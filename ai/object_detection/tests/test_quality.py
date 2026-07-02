"""Tests: dataset statistics and the quality report."""
import json
import tempfile
import unittest
from pathlib import Path

from ai.object_detection.data_tools.quality import (
    compute_stats,
    load_merge_summary,
    write_quality_report,
)
from ai.object_detection.tests._helpers import write_image, write_label

NAMES = ["fire", "smoke", "person"]


class QualityTestBase(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)
        self.processed = self.tmp / "processed"

    def add(self, split: str, stem: str, lines):
        write_image(self.processed / "images" / split / f"{stem}.png")
        write_label(self.processed / "labels" / split / f"{stem}.txt", lines)


class TestComputeStats(QualityTestBase):

    def test_counts_per_split_and_class(self):
        self.add("train", "a", ["0 0.5 0.5 0.1 0.1", "0 0.3 0.3 0.1 0.1"])
        self.add("train", "b", ["1 0.5 0.5 0.1 0.1"])
        self.add("val", "c", ["2 0.5 0.5 0.1 0.1"])
        self.add("val", "neg", [])
        stats = compute_stats(self.processed, NAMES)
        self.assertEqual(stats.images_total, 4)
        self.assertEqual(stats.boxes_total, 4)
        self.assertEqual(stats.negatives_total, 1)
        self.assertEqual(stats.splits["train"].boxes_per_class["fire"], 2)
        self.assertEqual(stats.splits["train"].images_per_class["fire"], 1)
        self.assertEqual(stats.splits["val"].boxes_per_class["person"], 1)

    def test_totals_per_class(self):
        self.add("train", "a", ["0 0.5 0.5 0.1 0.1"])
        self.add("val", "b", ["0 0.5 0.5 0.1 0.1", "1 0.4 0.4 0.1 0.1"])
        stats = compute_stats(self.processed, NAMES)
        self.assertEqual(stats.totals_per_class("boxes"),
                         {"fire": 2, "smoke": 1, "person": 0})
        self.assertEqual(stats.totals_per_class("images"),
                         {"fire": 2, "smoke": 1, "person": 0})

    def test_balance_ratio(self):
        for i in range(6):
            self.add("train", f"fire{i}", ["0 0.5 0.5 0.1 0.1"])
        self.add("train", "smoke0", ["1 0.5 0.5 0.1 0.1"])
        self.add("train", "person0", ["2 0.5 0.5 0.1 0.1"])
        stats = compute_stats(self.processed, NAMES)
        self.assertAlmostEqual(stats.balance_ratio(), 6.0)

    def test_balance_ratio_inf_when_class_absent(self):
        self.add("train", "a", ["0 0.5 0.5 0.1 0.1"])
        stats = compute_stats(self.processed, NAMES)
        self.assertEqual(stats.balance_ratio(), float("inf"))

    def test_missing_processed_dataset_raises(self):
        with self.assertRaises(FileNotFoundError):
            compute_stats(self.tmp / "nope", NAMES)


class TestQualityReport(QualityTestBase):

    def test_report_sections(self):
        self.add("train", "a", ["0 0.5 0.5 0.1 0.1"])
        self.add("val", "b", ["1 0.5 0.5 0.1 0.1"])
        self.add("test", "c", ["2 0.5 0.5 0.1 0.1"])
        stats = compute_stats(self.processed, NAMES)
        path = write_quality_report(stats, self.tmp / "quality_report.md")
        text = path.read_text(encoding="utf-8")
        for section in ("# Dataset Quality Report",
                        "## Images and annotations per class",
                        "## Per split", "## Dataset balance",
                        "## Potential issues", "## Recommendations"):
            self.assertIn(section, text)

    def test_imbalance_triggers_issue_and_recommendation(self):
        for i in range(10):
            self.add("train", f"fire{i}", ["0 0.5 0.5 0.1 0.1"])
        self.add("train", "person0", ["2 0.5 0.5 0.1 0.1"])
        self.add("train", "smoke0", ["1 0.5 0.5 0.1 0.1"])
        stats = compute_stats(self.processed, NAMES)
        text = write_quality_report(
            stats, self.tmp / "q.md").read_text(encoding="utf-8")
        self.assertIn("class imbalance", text)
        self.assertIn("add more", text)

    def test_merge_summary_folded_in(self):
        self.add("train", "a", ["0 0.5 0.5 0.1 0.1"])
        stats = compute_stats(self.processed, NAMES)
        summary = {"duplicates": 5, "corrupted": 2, "malformed": 1,
                   "unmapped": 7, "invalid": 3}
        text = write_quality_report(
            stats, self.tmp / "q.md",
            merge_summary=summary).read_text(encoding="utf-8")
        self.assertIn("Duplicate images skipped: 5", text)
        self.assertIn("Corrupted images excluded: 2", text)


class TestLoadMergeSummary(unittest.TestCase):

    def test_none_when_no_merge_ran(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertIsNone(load_merge_summary(Path(tmp)))

    def test_aggregates_source_counters(self):
        with tempfile.TemporaryDirectory() as tmp:
            stats = {
                "sources": [
                    {"duplicates_skipped": 2, "corrupted_skipped": 1,
                     "malformed_skipped": 0, "boxes_dropped_unmapped": 4,
                     "boxes_dropped_invalid": 1},
                    {"duplicates_skipped": 3, "corrupted_skipped": 0,
                     "malformed_skipped": 2, "boxes_dropped_unmapped": 0,
                     "boxes_dropped_invalid": 0},
                ]
            }
            path = Path(tmp) / "merge_stats.json"
            path.write_text(json.dumps(stats), encoding="utf-8")
            summary = load_merge_summary(Path(tmp))
            self.assertEqual(summary["duplicates"], 5)
            self.assertEqual(summary["corrupted"], 1)
            self.assertEqual(summary["malformed"], 2)
            self.assertEqual(summary["unmapped"], 4)
            self.assertEqual(summary["invalid"], 1)


if __name__ == "__main__":
    unittest.main()
