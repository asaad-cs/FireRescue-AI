"""Tests: deterministic stratified train/val/test splitting."""
import json
import tempfile
import unittest
from pathlib import Path

from ai.object_detection.data_tools.split import (
    SPLIT_NAMES,
    assign_splits,
    class_signature,
    load_splits,
    write_split_report,
)
from ai.object_detection.tests._helpers import write_image, write_label


class SplitTestBase(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.merged = Path(self._tmp.name) / "merged"
        self.addCleanup(self._tmp.cleanup)

    def populate(self, count: int, label_lines=("0 0.5 0.5 0.2 0.2",)):
        for i in range(count):
            write_image(self.merged / "images" / f"img{i:04d}.png",
                        color=(i % 256, i // 256, 7))
            write_label(self.merged / "labels" / f"img{i:04d}.txt",
                        list(label_lines))


class TestClassSignature(unittest.TestCase):

    def test_signatures(self):
        names = ["fire", "smoke", "person"]
        self.assertEqual(class_signature(set(), names), "negative")
        self.assertEqual(class_signature({0}, names), "fire")
        self.assertEqual(class_signature({1, 0}, names), "fire+smoke")
        self.assertEqual(class_signature({2, 0, 1}, names),
                         "fire+smoke+person")


class TestAssignSplits(SplitTestBase):

    def test_every_image_assigned_exactly_once(self):
        self.populate(100)
        result = assign_splits(self.merged, seed=42)
        self.assertEqual(len(result.assignments), 100)
        self.assertTrue(
            all(s in SPLIT_NAMES for s in result.assignments.values()))

    def test_ratios_are_respected(self):
        self.populate(200)
        result = assign_splits(self.merged, ratios=(0.7, 0.2, 0.1), seed=42)
        counts = result.split_counts()
        self.assertAlmostEqual(counts["train"] / 200, 0.7, delta=0.03)
        self.assertAlmostEqual(counts["val"] / 200, 0.2, delta=0.03)
        self.assertAlmostEqual(counts["test"] / 200, 0.1, delta=0.03)

    def test_same_seed_is_deterministic(self):
        self.populate(50)
        first = assign_splits(self.merged, seed=42).assignments
        second = assign_splits(self.merged, seed=42).assignments
        self.assertEqual(first, second)

    def test_different_seed_changes_assignment(self):
        self.populate(50)
        a = assign_splits(self.merged, seed=42).assignments
        b = assign_splits(self.merged, seed=1337).assignments
        self.assertNotEqual(a, b)

    def test_stratification_keeps_signatures_in_every_split(self):
        for i in range(60):
            write_image(self.merged / "images" / f"fire{i}.png",
                        color=(i, 0, 0))
            write_label(self.merged / "labels" / f"fire{i}.txt",
                        ["0 0.5 0.5 0.2 0.2"])
        for i in range(60):
            write_image(self.merged / "images" / f"person{i}.png",
                        color=(0, i, 0))
            write_label(self.merged / "labels" / f"person{i}.txt",
                        ["2 0.5 0.5 0.2 0.2"])
        result = assign_splits(self.merged, seed=42)
        for signature in ("fire", "person"):
            for split in SPLIT_NAMES:
                self.assertGreater(
                    result.signature_counts[signature][split], 0,
                    f"{signature} missing from {split}")

    def test_tiny_group_goes_to_train(self):
        self.populate(1)
        result = assign_splits(self.merged, seed=42)
        self.assertEqual(list(result.assignments.values()), ["train"])

    def test_splits_json_written_and_loadable(self):
        self.populate(10)
        result = assign_splits(self.merged, seed=7)
        loaded = load_splits(self.merged)
        self.assertEqual(loaded, result.assignments)
        raw = json.loads(
            (self.merged / "splits.json").read_text(encoding="utf-8"))
        self.assertEqual(raw["seed"], 7)

    def test_invalid_ratios_rejected(self):
        self.populate(5)
        with self.assertRaises(ValueError):
            assign_splits(self.merged, ratios=(0.5, 0.5, 0.5))
        with self.assertRaises(ValueError):
            assign_splits(self.merged, ratios=(1.1, -0.2, 0.1))

    def test_missing_merged_dataset_raises(self):
        with self.assertRaises(ValueError):
            assign_splits(self.merged)

    def test_load_splits_missing_raises(self):
        self.merged.mkdir(parents=True)
        with self.assertRaises(FileNotFoundError):
            load_splits(self.merged)


class TestSplitReport(SplitTestBase):

    def test_report_content(self):
        self.populate(30)
        result = assign_splits(self.merged, seed=42)
        path = write_split_report(result,
                                  Path(self._tmp.name) / "split_report.md")
        text = path.read_text(encoding="utf-8")
        self.assertIn("# Dataset Split Report", text)
        self.assertIn("Seed:** 42", text)
        self.assertIn("| train |", text)
        self.assertIn("Stratification", text)


if __name__ == "__main__":
    unittest.main()
