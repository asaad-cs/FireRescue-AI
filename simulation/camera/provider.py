"""
Zone image provider — the simulated camera's picture library.

Three collaborating pieces, all configured by simulation_camera.yaml:

  CameraConfig          parsed, validated configuration
  ZoneCategoryResolver  zone_id → image category ("fire", "safe", ...)
                        derived from the active scenario's hazard levels
                        and victim positions, with per-zone overrides
  ZoneImageProvider     category → concrete image (discovery, seeded
                        random selection, LRU decode cache, graceful
                        fallback when folders are missing or empty)

Design rules:
  - No hardcoded paths: the image root comes from configuration and is
    resolved by the caller (dependency injection).
  - Never raises during a mission: a missing folder, empty category,
    or unreadable file degrades to a less specific category and
    finally to "no image" (None).
  - Lazy imports: yaml only in load_camera_config, cv2/numpy only when
    an image is actually decoded.
"""
from __future__ import annotations

import logging
import random
from collections import OrderedDict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Collection, Dict, List, Mapping, Optional, Tuple

logger = logging.getLogger(__name__)

_DEFAULT_EXTENSIONS = (".jpg", ".jpeg", ".png")


class CameraConfigError(ValueError):
    """simulation_camera.yaml is missing, malformed, or inconsistent."""


@dataclass(frozen=True)
class CameraConfig:
    """Parsed simulation_camera.yaml.

    Selection modes (Phase 8K):
      randomize=False        → fixed: always the first image (sorted by
                               name) of a category. Strict test mode.
      randomize=True, seed=N → deterministic mission: seeded random
                               selection, reproducible across runs.
      randomize=True, seed=None ("seed: null" in YAML)
                             → normal random mode: a fresh entropy seed
                               is drawn per provider (i.e. per mission)
                               and logged, so consecutive missions see
                               different imagery yet any single mission
                               can be reproduced from its logged seed.
    """

    image_root: str
    extensions: Tuple[str, ...] = _DEFAULT_EXTENSIONS
    randomize: bool = True
    seed: Optional[int] = 42
    cache_size: int = 64
    default_category: str = "safe"
    hazard_categories: Dict[str, str] = field(default_factory=dict)
    victim_suffix: str = "_person"
    victim_only_category: str = "person"
    zone_overrides: Dict[str, str] = field(default_factory=dict)
    # Placeholder for a future video source. Must stay False — video,
    # streaming, webcams, and RTSP are explicitly out of scope.
    video_enabled: bool = False


def load_camera_config(path: Path) -> CameraConfig:
    """Load and validate simulation_camera.yaml.

    Args:
        path: The YAML file to read.

    Returns:
        A validated CameraConfig.

    Raises:
        CameraConfigError: If the file is missing, malformed, or asks
            for unsupported features (e.g. video).
    """
    import yaml

    if not path.is_file():
        raise CameraConfigError(f"camera config not found: {path}")
    with path.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    if not isinstance(data, dict):
        raise CameraConfigError(f"camera config is not a YAML mapping: {path}")

    video = data.get("video") or {}
    raw_seed = data.get("seed", 42)
    config = CameraConfig(
        image_root=str(_require(data, "image_root", path)),
        extensions=tuple(
            str(e).lower() for e in data.get("extensions", _DEFAULT_EXTENSIONS)
        ),
        randomize=bool(data.get("randomize", True)),
        # "seed: null" selects normal random mode (fresh entropy per mission).
        seed=None if raw_seed is None else int(raw_seed),
        cache_size=int(data.get("cache_size", 64)),
        default_category=str(data.get("default_category", "safe")),
        hazard_categories={
            str(k): str(v)
            for k, v in (data.get("hazard_categories") or {}).items()
        },
        victim_suffix=str(data.get("victim_suffix", "_person")),
        victim_only_category=str(data.get("victim_only_category", "person")),
        zone_overrides={
            str(k): str(v) for k, v in (data.get("zone_overrides") or {}).items()
        },
        video_enabled=bool(video.get("enabled", False)),
    )
    if config.video_enabled:
        raise CameraConfigError(
            f"{path.name}: video is a placeholder and not implemented; "
            "set video.enabled to false"
        )
    if config.cache_size < 1:
        raise CameraConfigError(f"{path.name}: cache_size must be >= 1")
    if not config.extensions:
        raise CameraConfigError(f"{path.name}: extensions must not be empty")
    return config


def _require(data: Mapping[str, Any], key: str, path: Path) -> Any:
    if key not in data:
        raise CameraConfigError(f"{path.name}: missing required key '{key}'")
    return data[key]


class ZoneCategoryResolver:
    """Derives the image category for a zone from scenario ground truth.

    Resolution order:
      1. explicit zone_overrides from the config
      2. the zone's hazard level via hazard_categories
      3. victim presence appends victim_suffix (or, in an otherwise
         safe zone, switches to victim_only_category)
    """

    def __init__(
        self,
        config: CameraConfig,
        hazard_levels: Mapping[str, str],
        victim_zones: Collection[str],
    ) -> None:
        """
        Args:
            config: Parsed camera configuration.
            hazard_levels: zone_id → hazard level name (plain strings,
                e.g. "CRITICAL"), as defined by the active scenario.
            victim_zones: zone_ids that contain a victim.
        """
        self._config = config
        self._hazard_levels = dict(hazard_levels)
        self._victim_zones = set(victim_zones)

    def category_for(self, zone_id: str) -> str:
        """Return the image category for a zone."""
        override = self._config.zone_overrides.get(zone_id)
        if override:
            return override
        level = self._hazard_levels.get(zone_id, "")
        base = self._config.hazard_categories.get(
            level, self._config.default_category
        )
        if zone_id in self._victim_zones:
            if base == self._config.default_category:
                return self._config.victim_only_category
            return f"{base}{self._config.victim_suffix}"
        return base


class ZoneImageProvider:
    """Serves one RGB image (BGR uint8 numpy array) per zone visit.

    One provider lives exactly one mission (make_data_source builds a
    fresh one per mission), so all per-instance state below is
    mission-scoped by construction.

    Mission-scoped no-repeat pool (Phase 8K): with randomize enabled,
    an image already served this mission is not chosen again until
    every image of that category folder has been used; only then does
    the pool recycle. Zones are also sticky — a zone keeps the image
    it was first assigned, so revisits show the same room. Recycling
    (Phase Demo.4) also excludes the image that just closed the
    previous cycle, so it cannot immediately reopen the next one too.

    Reproducibility: with an integer seed the whole mission's imagery
    is deterministic (one seeded RNG + deterministic BFS visit order).
    With seed None (normal random mode) a fresh entropy seed is drawn
    and exposed as effective_seed so the mission can still be
    reproduced from the logs. With randomize disabled, the first image
    (sorted by name) of a category is always served.
    """

    def __init__(
        self,
        config: CameraConfig,
        resolver: ZoneCategoryResolver,
        image_root: Path,
    ) -> None:
        """
        Args:
            config: Parsed camera configuration.
            resolver: Zone → category resolver.
            image_root: Absolute directory holding one sub-folder per
                category (resolved by the caller — never hardcoded here).
        """
        self._config = config
        self._resolver = resolver
        self._image_root = image_root
        self._effective_seed = (
            config.seed
            if config.seed is not None
            else random.SystemRandom().randrange(2**63)
        )
        self._rng = random.Random(self._effective_seed)
        self._listings: Dict[str, List[Path]] = {}
        self._used: Dict[str, set] = {}
        self._last_shown: Dict[str, Path] = {}
        self._zone_assignments: Dict[str, Optional[Path]] = {}
        self._cache: "OrderedDict[str, Any]" = OrderedDict()
        self._warned: set = set()

    @property
    def effective_seed(self) -> int:
        """The seed actually driving selection this mission.

        Equals config.seed when one was given; otherwise the entropy
        seed drawn for normal random mode (log it to reproduce a run).
        """
        return self._effective_seed

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def image_for_zone(self, zone_id: str) -> Optional[Any]:
        """Pick and decode an image for a zone.

        A zone keeps the image it was assigned on first visit for the
        rest of the mission (rooms do not change appearance between
        visits, and repeat frames do not drain the no-repeat pool).

        Args:
            zone_id: Zone identifier ("<x>_<y>_<floor>").

        Returns:
            HxWx3 uint8 BGR numpy array, or None when no usable image
            exists for the zone's category or any of its fallbacks.
        """
        if zone_id in self._zone_assignments:
            path = self._zone_assignments[zone_id]
        else:
            category = self._resolver.category_for(zone_id)
            path = self.select_path(category)
            self._zone_assignments[zone_id] = path
        if path is None:
            return None
        return self._load(path)

    def select_path(self, category: str) -> Optional[Path]:
        """Choose an image path for a category, walking the fallback chain.

        Fallback chain for e.g. "fire_smoke_person":
        the category itself → without the victim suffix ("fire_smoke")
        → its first component ("fire") → the default category.

        With randomize enabled, selection draws from the mission's
        no-repeat pool: images already served are excluded until the
        candidate folder is exhausted, at which point the pool recycles.

        Args:
            category: Requested image category.

        Returns:
            A chosen path, or None when every candidate is empty.
        """
        for candidate in self._candidates(category):
            files = self._list_category(candidate)
            if files:
                if candidate != category:
                    self._warn_once(
                        f"category '{category}' has no images — using "
                        f"'{candidate}' instead"
                    )
                if not self._config.randomize:
                    return files[0]
                return self._pick_unused(candidate, files)
        self._warn_once(
            f"no images available for category '{category}' "
            f"(searched {list(self._candidates(category))} under "
            f"{self._image_root})"
        )
        return None

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _pick_unused(self, folder: str, files: List[Path]) -> Path:
        """Random choice honoring the mission-scoped no-repeat pool.

        Pools are keyed by the folder actually served, so a category
        reached via fallback (fire_person → fire) shares its pool with
        direct requests for that folder.

        Recycle-boundary guard: when a pool exhausts and recycles, the
        image that just closed the previous cycle is excluded from the
        reopened pool (when more than one image exists), so it cannot
        become the first pick of the new cycle too. With exactly one
        image, there is nothing to exclude — that image is always
        returned, unchanged from before.
        """
        used = self._used.setdefault(folder, set())
        unused = [f for f in files if f not in used]
        if not unused:
            logger.info(
                "ZoneImageProvider | category '%s' exhausted its %d "
                "image(s) this mission — recycling pool",
                folder,
                len(files),
            )
            used.clear()
            unused = files
            last = self._last_shown.get(folder)
            if last is not None and len(files) > 1:
                unused = [f for f in files if f != last]
        choice = self._rng.choice(unused)
        used.add(choice)
        self._last_shown[folder] = choice
        return choice

    def _candidates(self, category: str) -> List[str]:
        candidates = [category]
        suffix = self._config.victim_suffix
        if suffix and category.endswith(suffix):
            candidates.append(category[: -len(suffix)])
        head = category.split("_")[0]
        if head not in candidates:
            candidates.append(head)
        if self._config.default_category not in candidates:
            candidates.append(self._config.default_category)
        return candidates

    def _list_category(self, category: str) -> List[Path]:
        """Sorted image files of one category folder (cached, lazy)."""
        if category not in self._listings:
            folder = self._image_root / category
            if not folder.is_dir():
                self._listings[category] = []
            else:
                self._listings[category] = sorted(
                    p
                    for p in folder.iterdir()
                    if p.is_file()
                    and p.suffix.lower() in self._config.extensions
                )
        return self._listings[category]

    def _load(self, path: Path) -> Optional[Any]:
        """Decode an image with an LRU cache of config.cache_size entries."""
        key = str(path)
        if key in self._cache:
            self._cache.move_to_end(key)
            return self._cache[key]
        image = self._decode(path)
        if image is None:
            self._warn_once(f"could not decode image: {path}")
            return None
        self._cache[key] = image
        if len(self._cache) > self._config.cache_size:
            self._cache.popitem(last=False)
        return image

    @staticmethod
    def _decode(path: Path) -> Optional[Any]:
        """Read an image file into a BGR uint8 array (lazy cv2/numpy)."""
        import cv2
        import numpy as np

        try:
            # imdecode instead of imread: robust to non-ASCII Windows paths.
            data = np.fromfile(str(path), dtype=np.uint8)
            return cv2.imdecode(data, cv2.IMREAD_COLOR)
        except Exception:
            return None

    def _warn_once(self, message: str) -> None:
        if message not in self._warned:
            self._warned.add(message)
            logger.warning("ZoneImageProvider | %s", message)
