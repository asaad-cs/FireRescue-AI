"""Tests: simulated camera — config, category resolution, image provider."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import numpy as np

from simulation.camera.provider import (
    CameraConfig,
    CameraConfigError,
    ZoneCategoryResolver,
    ZoneImageProvider,
    load_camera_config,
)

CONFIG_YAML = """\
image_root: images
extensions: [".jpg", ".png"]
randomize: true
seed: 7
cache_size: 8
default_category: safe
hazard_categories:
  CLEAR: safe
  MODERATE: smoke
  CRITICAL: fire
victim_suffix: _person
victim_only_category: person
zone_overrides:
  "9_9_1": fire_smoke
video:
  enabled: false
"""


def write_png(path: Path, value: int = 128) -> Path:
    import cv2

    path.parent.mkdir(parents=True, exist_ok=True)
    image = np.full((8, 8, 3), value, dtype=np.uint8)
    ok, buffer = cv2.imencode(".png", image)
    assert ok
    path.write_bytes(buffer.tobytes())
    return path


def make_config(**overrides) -> CameraConfig:
    defaults = dict(
        image_root="images",
        extensions=(".jpg", ".jpeg", ".png"),
        randomize=True,
        seed=7,
        cache_size=8,
        default_category="safe",
        hazard_categories={"CLEAR": "safe", "MODERATE": "smoke",
                           "CRITICAL": "fire"},
        victim_suffix="_person",
        victim_only_category="person",
        zone_overrides={},
    )
    defaults.update(overrides)
    return CameraConfig(**defaults)


def make_provider(root: Path, config: CameraConfig | None = None,
                  hazard_levels=None, victim_zones=()) -> ZoneImageProvider:
    config = config or make_config()
    resolver = ZoneCategoryResolver(
        config=config,
        hazard_levels=hazard_levels or {},
        victim_zones=victim_zones,
    )
    return ZoneImageProvider(config=config, resolver=resolver, image_root=root)


class TestLoadCameraConfig(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)

    def _write(self, content: str) -> Path:
        path = self.tmp / "simulation_camera.yaml"
        path.write_text(content, encoding="utf-8")
        return path

    def test_valid_config(self):
        config = load_camera_config(self._write(CONFIG_YAML))
        self.assertEqual(config.image_root, "images")
        self.assertEqual(config.seed, 7)
        self.assertEqual(config.hazard_categories["CRITICAL"], "fire")
        self.assertEqual(config.zone_overrides["9_9_1"], "fire_smoke")
        self.assertFalse(config.video_enabled)

    def test_defaults_applied(self):
        config = load_camera_config(self._write("image_root: x\n"))
        self.assertTrue(config.randomize)
        self.assertEqual(config.default_category, "safe")
        self.assertIn(".jpg", config.extensions)
        self.assertIn(".png", config.extensions)

    def test_missing_file_raises(self):
        with self.assertRaises(CameraConfigError):
            load_camera_config(self.tmp / "nope.yaml")

    def test_missing_image_root_raises(self):
        with self.assertRaises(CameraConfigError):
            load_camera_config(self._write("randomize: true\n"))

    def test_non_mapping_raises(self):
        with self.assertRaises(CameraConfigError):
            load_camera_config(self._write("- just\n- a list\n"))

    def test_video_enabled_is_rejected(self):
        content = "image_root: x\nvideo:\n  enabled: true\n"
        with self.assertRaises(CameraConfigError) as ctx:
            load_camera_config(self._write(content))
        self.assertIn("video", str(ctx.exception))

    def test_invalid_cache_size_raises(self):
        with self.assertRaises(CameraConfigError):
            load_camera_config(self._write("image_root: x\ncache_size: 0\n"))

    def test_real_committed_config_loads(self):
        path = (Path(__file__).resolve().parents[1] / "camera"
                / "simulation_camera.yaml")
        config = load_camera_config(path)
        self.assertFalse(config.video_enabled)
        self.assertEqual(config.default_category, "safe")


class TestZoneCategoryResolver(unittest.TestCase):

    def _resolver(self, **kwargs):
        return ZoneCategoryResolver(
            config=make_config(zone_overrides={"9_9_1": "fire_smoke"}),
            hazard_levels=kwargs.get(
                "hazard_levels", {"1_0_1": "CRITICAL", "2_0_1": "MODERATE"}
            ),
            victim_zones=kwargs.get("victim_zones", {"3_0_1", "1_0_1"}),
        )

    def test_override_has_highest_priority(self):
        self.assertEqual(self._resolver().category_for("9_9_1"), "fire_smoke")

    def test_hazard_level_maps_to_category(self):
        resolver = self._resolver(victim_zones=set())
        self.assertEqual(resolver.category_for("1_0_1"), "fire")
        self.assertEqual(resolver.category_for("2_0_1"), "smoke")

    def test_unknown_zone_gets_default(self):
        self.assertEqual(self._resolver().category_for("8_8_8"), "safe")

    def test_victim_appends_suffix(self):
        self.assertEqual(self._resolver().category_for("1_0_1"), "fire_person")

    def test_victim_in_safe_zone_becomes_person(self):
        self.assertEqual(self._resolver().category_for("3_0_1"), "person")


class TestZoneImageProvider(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)

    def test_image_loading_returns_bgr_array(self):
        write_png(self.root / "safe" / "a.png")
        provider = make_provider(self.root)
        image = provider.image_for_zone("0_0_1")
        self.assertEqual(image.shape, (8, 8, 3))
        self.assertEqual(image.dtype, np.uint8)

    def test_extension_filter(self):
        write_png(self.root / "safe" / "a.png")
        (self.root / "safe" / "notes.txt").write_text("x", encoding="utf-8")
        (self.root / "safe" / "b.gif").write_bytes(b"GIF89a")
        provider = make_provider(self.root)
        self.assertEqual(provider.select_path("safe").name, "a.png")

    def test_missing_root_returns_none(self):
        provider = make_provider(self.root / "does-not-exist")
        self.assertIsNone(provider.image_for_zone("0_0_1"))

    def test_missing_category_falls_back_along_chain(self):
        write_png(self.root / "fire" / "f.png")
        provider = make_provider(
            self.root,
            hazard_levels={"1_0_1": "CRITICAL"},
            victim_zones={"1_0_1"},
        )
        # fire_person has no folder → falls back to fire.
        path = provider.select_path("fire_person")
        self.assertEqual(path.name, "f.png")
        self.assertIsNotNone(provider.image_for_zone("1_0_1"))

    def test_empty_everywhere_returns_none(self):
        (self.root / "fire").mkdir(parents=True)  # exists but empty
        provider = make_provider(self.root,
                                 hazard_levels={"1_0_1": "CRITICAL"})
        self.assertIsNone(provider.image_for_zone("1_0_1"))

    def test_random_selection_uses_all_images(self):
        for name in ("a.png", "b.png", "c.png"):
            write_png(self.root / "safe" / name)
        provider = make_provider(self.root)
        chosen = {provider.select_path("safe").name for _ in range(60)}
        self.assertEqual(chosen, {"a.png", "b.png", "c.png"})

    def test_seed_reproducibility(self):
        for name in ("a.png", "b.png", "c.png", "d.png"):
            write_png(self.root / "safe" / name)

        def sequence(seed: int):
            provider = make_provider(self.root, make_config(seed=seed))
            return [provider.select_path("safe").name for _ in range(12)]

        self.assertEqual(sequence(7), sequence(7))
        self.assertNotEqual(sequence(7), sequence(1234))

    def test_randomize_disabled_always_first_sorted(self):
        for name in ("b.png", "a.png", "c.png"):
            write_png(self.root / "safe" / name)
        provider = make_provider(self.root, make_config(randomize=False))
        names = {provider.select_path("safe").name for _ in range(10)}
        self.assertEqual(names, {"a.png"})

    def test_cache_decodes_each_image_once(self):
        write_png(self.root / "safe" / "a.png")
        provider = make_provider(self.root)
        calls = []
        original = ZoneImageProvider._decode

        def counting(path):
            calls.append(path)
            return original(path)

        provider._decode = counting
        for _ in range(5):
            self.assertIsNotNone(provider.image_for_zone("0_0_1"))
        self.assertEqual(len(calls), 1)

    def test_cache_evicts_beyond_capacity(self):
        write_png(self.root / "safe" / "a.png", value=10)
        write_png(self.root / "safe" / "b.png", value=20)
        provider = make_provider(
            self.root, make_config(cache_size=1, randomize=False)
        )
        calls = []
        original = ZoneImageProvider._decode

        def counting(path):
            calls.append(path.name)
            return original(path)

        provider._decode = counting
        provider._load(self.root / "safe" / "a.png")
        provider._load(self.root / "safe" / "b.png")  # evicts a
        provider._load(self.root / "safe" / "a.png")  # decoded again
        self.assertEqual(calls, ["a.png", "b.png", "a.png"])

    def test_undecodable_image_returns_none(self):
        bad = self.root / "safe" / "bad.png"
        bad.parent.mkdir(parents=True)
        bad.write_bytes(b"not an image at all")
        provider = make_provider(self.root)
        self.assertIsNone(provider.image_for_zone("0_0_1"))


if __name__ == "__main__":
    unittest.main()
