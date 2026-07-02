"""Declarative registry of raw source datasets (configs/sources.yaml).

Each source describes where its files live under datasets/raw/ and how
its class ids translate to the unified scheme. Adding a dataset means
adding one YAML entry — no pipeline code changes.
"""
from dataclasses import dataclass, field
from pathlib import Path

from ai.object_detection.config import load_dataset_config
from ai.object_detection.data_tools.image_utils import SUPPORTED_EXTENSIONS
from ai.object_detection.paths import CONFIGS_DIR
from ai.shared.utils.config import ConfigError, load_yaml, require as _require

VALID_KINDS = ("yolo", "coco")


@dataclass(frozen=True)
class SourceSpec:
    """One entry of configs/sources.yaml."""

    name: str
    kind: str
    root: str
    enabled: bool
    class_map: dict[int, int | None] = field(default_factory=dict)
    images: str | None = None
    annotations: str | None = None
    categories: dict[str, int] = field(default_factory=dict)
    license: str = ""
    url: str = ""

    def validate(self, nc: int) -> None:
        """Check internal consistency against the unified class count.

        Args:
            nc: Number of unified classes; valid target ids are 0..nc-1.

        Raises:
            ConfigError: If any field is invalid.
        """
        src = f"sources.yaml:{self.name}"
        if self.kind not in VALID_KINDS:
            raise ConfigError(
                f"{src}: 'kind' must be one of {VALID_KINDS}, got '{self.kind}'"
            )
        p = Path(self.root)
        if p.is_absolute() or p.drive or p.root in ("/", "\\"):
            raise ConfigError(
                f"{src}: 'root' must be relative to datasets/raw/, got '{self.root}'"
            )
        if self.kind == "yolo":
            if not self.class_map:
                raise ConfigError(f"{src}: yolo sources need a 'class_map'")
            targets = [t for t in self.class_map.values() if t is not None]
        else:
            if not self.images or not self.annotations:
                raise ConfigError(
                    f"{src}: coco sources need 'images' and 'annotations'"
                )
            if not self.categories:
                raise ConfigError(f"{src}: coco sources need 'categories'")
            targets = list(self.categories.values())
        for target in targets:
            if not 0 <= target < nc:
                raise ConfigError(
                    f"{src}: mapped class id {target} outside 0..{nc - 1}"
                )


def load_sources(path: Path = CONFIGS_DIR / "sources.yaml") -> list[SourceSpec]:
    """Load and validate all source specs.

    Args:
        path: YAML file to read; defaults to configs/sources.yaml.

    Returns:
        All specs, including disabled ones (callers filter on .enabled).

    Raises:
        ConfigError: If the file is missing, malformed, or inconsistent.
    """
    data = load_yaml(path)
    entries = _require(data, "sources", path.name)
    if not isinstance(entries, list) or not entries:
        raise ConfigError(f"{path.name}: 'sources' must be a non-empty list")
    nc = load_dataset_config().nc

    specs = []
    seen = set()
    for entry in entries:
        name = str(_require(entry, "name", path.name))
        if name in seen:
            raise ConfigError(f"{path.name}: duplicate source name '{name}'")
        seen.add(name)
        raw_map = entry.get("class_map") or {}
        spec = SourceSpec(
            name=name,
            kind=str(_require(entry, "kind", f"{path.name}:{name}")),
            root=str(_require(entry, "root", f"{path.name}:{name}")),
            enabled=bool(entry.get("enabled", True)),
            class_map={
                int(k): (None if v is None else int(v))
                for k, v in raw_map.items()
            },
            images=entry.get("images"),
            annotations=entry.get("annotations"),
            categories={
                str(k): int(v) for k, v in (entry.get("categories") or {}).items()
            },
            license=str(entry.get("license", "")),
            url=str(entry.get("url", "")),
        )
        spec.validate(nc)
        specs.append(spec)
    return specs


def discover_yolo_pairs(root: Path) -> list[tuple[Path, Path | None]]:
    """Find every image under a YOLO-style tree with its label file.

    Handles the common layouts:
        <root>/<split>/images/x.jpg + <root>/<split>/labels/x.txt
        <root>/images/<split>/x.jpg + <root>/labels/<split>/x.txt
        image and label side by side in the same directory

    Args:
        root: Source dataset root to walk.

    Returns:
        (image_path, label_path) pairs sorted by image path; label_path
        is None when no label file exists for the image.
    """
    pairs = []
    for image in sorted(root.rglob("*")):
        if not image.is_file() or image.suffix.lower() not in SUPPORTED_EXTENSIONS:
            continue
        label = None
        if "images" in image.parts:
            # Mirror .../images/... -> .../labels/... (rightmost match).
            parts = list(image.parts)
            idx = len(parts) - 1 - parts[::-1].index("images")
            parts[idx] = "labels"
            candidate = Path(*parts).with_suffix(".txt")
            if candidate.is_file():
                label = candidate
        if label is None:
            candidate = image.with_suffix(".txt")
            if candidate.is_file():
                label = candidate
        pairs.append((image, label))
    return pairs
