"""Tests: source registry loading and YOLO pair discovery."""
import tempfile
import unittest
from pathlib import Path

from ai.object_detection.data_tools.sources import (
    SourceSpec,
    discover_yolo_pairs,
    load_sources,
)
from ai.object_detection.tests._helpers import write_image, write_label
from ai.shared.utils.config import ConfigError


class TestLoadRealSourcesConfig(unittest.TestCase):
    """The committed configs/sources.yaml must always be loadable."""

    def test_loads_and_validates(self):
        specs = load_sources()
        names = [s.name for s in specs]
        self.assertIn("figshare_fire_smoke", names)
        self.assertIn("dfire", names)
        self.assertIn("coco_person", names)

    def test_unified_ids_within_range(self):
        for spec in load_sources():
            targets = (
                [v for v in spec.class_map.values() if v is not None]
                + list(spec.categories.values())
            )
            for target in targets:
                self.assertIn(target, (0, 1, 2), spec.name)

    def test_coco_source_shape(self):
        coco = next(s for s in load_sources() if s.kind == "coco")
        self.assertTrue(coco.images)
        self.assertTrue(coco.annotations)
        self.assertEqual(coco.categories, {"person": 2})


class TestSpecValidation(unittest.TestCase):

    def _yaml(self, tmp: Path, body: str) -> Path:
        path = tmp / "sources.yaml"
        path.write_text(body, encoding="utf-8")
        return path

    def test_unknown_kind_rejected(self):
        spec = SourceSpec(name="x", kind="voc", root="x", enabled=True,
                          class_map={0: 0})
        with self.assertRaises(ConfigError):
            spec.validate(nc=3)

    def test_absolute_root_rejected(self):
        spec = SourceSpec(name="x", kind="yolo", root="C:/data", enabled=True,
                          class_map={0: 0})
        with self.assertRaises(ConfigError):
            spec.validate(nc=3)

    def test_target_class_out_of_range_rejected(self):
        spec = SourceSpec(name="x", kind="yolo", root="x", enabled=True,
                          class_map={0: 3})
        with self.assertRaises(ConfigError):
            spec.validate(nc=3)

    def test_yolo_without_class_map_rejected(self):
        spec = SourceSpec(name="x", kind="yolo", root="x", enabled=True)
        with self.assertRaises(ConfigError):
            spec.validate(nc=3)

    def test_coco_without_categories_rejected(self):
        spec = SourceSpec(name="x", kind="coco", root="x", enabled=True,
                          images="img", annotations="a.json")
        with self.assertRaises(ConfigError):
            spec.validate(nc=3)

    def test_duplicate_source_names_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self._yaml(Path(tmp), (
                "sources:\n"
                "  - {name: a, kind: yolo, root: a, class_map: {0: 0}}\n"
                "  - {name: a, kind: yolo, root: b, class_map: {0: 1}}\n"
            ))
            with self.assertRaises(ConfigError):
                load_sources(path)

    def test_empty_sources_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self._yaml(Path(tmp), "sources: []\n")
            with self.assertRaises(ConfigError):
                load_sources(path)


class TestDiscoverYoloPairs(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)

    def test_split_images_labels_layout(self):
        write_image(self.tmp / "train" / "images" / "a.png")
        write_label(self.tmp / "train" / "labels" / "a.txt", [])
        pairs = discover_yolo_pairs(self.tmp)
        self.assertEqual(len(pairs), 1)
        self.assertIsNotNone(pairs[0][1])
        self.assertEqual(pairs[0][1].name, "a.txt")

    def test_images_split_layout(self):
        write_image(self.tmp / "images" / "val" / "b.png")
        write_label(self.tmp / "labels" / "val" / "b.txt", [])
        pairs = discover_yolo_pairs(self.tmp)
        self.assertEqual(len(pairs), 1)
        self.assertIsNotNone(pairs[0][1])

    def test_sibling_label_layout(self):
        write_image(self.tmp / "flat" / "c.png")
        write_label(self.tmp / "flat" / "c.txt", [])
        pairs = discover_yolo_pairs(self.tmp)
        self.assertEqual(len(pairs), 1)
        self.assertIsNotNone(pairs[0][1])

    def test_missing_label_reported_as_none(self):
        write_image(self.tmp / "train" / "images" / "d.png")
        pairs = discover_yolo_pairs(self.tmp)
        self.assertEqual(len(pairs), 1)
        self.assertIsNone(pairs[0][1])

    def test_non_image_files_ignored(self):
        write_image(self.tmp / "images" / "e.png")
        (self.tmp / "images" / "notes.txt").write_text("x", encoding="utf-8")
        (self.tmp / "README.md").write_text("x", encoding="utf-8")
        pairs = discover_yolo_pairs(self.tmp)
        self.assertEqual(len(pairs), 1)

    def test_deterministic_order(self):
        for stem in ("z", "a", "m"):
            write_image(self.tmp / "images" / f"{stem}.png")
        names = [img.name for img, _ in discover_yolo_pairs(self.tmp)]
        self.assertEqual(names, sorted(names))


if __name__ == "__main__":
    unittest.main()
