"""Tests: final YOLO dataset assembly and data.yaml generation."""
import tempfile
import unittest
from pathlib import Path

import yaml

from ai.object_detection.config import load_dataset_config
from ai.object_detection.data_tools.build import build_processed
from ai.object_detection.data_tools.split import assign_splits
from ai.object_detection.tests._helpers import write_image, write_label


class TestBuildProcessed(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)
        self.merged = self.tmp / "merged"
        self.processed = self.tmp / "processed"
        for i in range(20):
            write_image(self.merged / "images" / f"img{i:03d}.png",
                        color=(i, 50, 100))
            write_label(self.merged / "labels" / f"img{i:03d}.txt",
                        [f"{i % 3} 0.5 0.5 0.2 0.2"])
        assign_splits(self.merged, seed=42)

    def build(self):
        return build_processed(self.merged, self.processed)

    def test_layout_and_counts(self):
        result = self.build()
        self.assertEqual(result.images_total, 20)
        for split in ("train", "val", "test"):
            images = list((self.processed / "images" / split).glob("*.png"))
            labels = list((self.processed / "labels" / split).glob("*.txt"))
            self.assertEqual(len(images), result.images_per_split[split])
            self.assertEqual(len(images), len(labels))
            for image in images:
                self.assertTrue(
                    (self.processed / "labels" / split /
                     f"{image.stem}.txt").is_file())

    def test_data_yaml_matches_dataset_config(self):
        result = self.build()
        data = yaml.safe_load(Path(result.data_yaml).read_text(
            encoding="utf-8"))
        cfg = load_dataset_config()
        self.assertEqual(data["nc"], cfg.nc)
        self.assertEqual(list(data["names"].values()), cfg.names)
        self.assertEqual(data["train"], cfg.train)
        self.assertEqual(data["val"], cfg.val)
        self.assertEqual(data["test"], cfg.test)
        self.assertEqual(Path(data["path"]), self.processed.resolve())

    def test_rebuild_replaces_previous_output(self):
        self.build()
        stray = self.processed / "images" / "train" / "stale.png"
        write_image(stray)
        self.build()
        self.assertFalse(stray.exists())

    def test_missing_referenced_file_raises(self):
        assign_splits(self.merged, seed=42)
        (self.merged / "images" / "img000.png").unlink()
        with self.assertRaises(FileNotFoundError):
            self.build()

    def test_missing_splits_json_raises(self):
        (self.merged / "splits.json").unlink()
        with self.assertRaises(FileNotFoundError):
            self.build()


if __name__ == "__main__":
    unittest.main()
