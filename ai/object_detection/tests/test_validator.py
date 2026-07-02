"""Tests: dataset validator checks and report writers."""
import json
import tempfile
import unittest
from pathlib import Path

from ai.object_detection.data_tools.validator import (
    validate_dataset,
    write_report_json,
    write_report_md,
)
from ai.object_detection.tests._helpers import (
    make_png,
    write_image,
    write_label,
)

GOOD = "0 0.5 0.5 0.2 0.2"


class ValidatorTestBase(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)

    def add(self, split: str, stem: str, label_lines=None, data: bytes = None,
            ext: str = ".png"):
        image = self.root / "images" / split / f"{stem}{ext}"
        if data is None:
            write_image(image)
        else:
            image.parent.mkdir(parents=True, exist_ok=True)
            image.write_bytes(data)
        if label_lines is not None:
            write_label(self.root / "labels" / split / f"{stem}.txt",
                        label_lines)


class TestValidateDataset(ValidatorTestBase):

    def test_clean_dataset(self):
        self.add("train", "a", [GOOD], data=make_png(4, 4, (1, 2, 3)))
        self.add("val", "b", ["1 0.4 0.4 0.1 0.1"],
                 data=make_png(4, 4, (4, 5, 6)))
        report = validate_dataset(self.root)
        self.assertTrue(report.is_clean)
        self.assertEqual(report.images_total, 2)
        self.assertEqual(report.annotations_total, 2)
        self.assertEqual(report.class_counts["fire"], 1)
        self.assertEqual(report.class_counts["smoke"], 1)

    def test_missing_label_detected(self):
        self.add("train", "a")  # no label file
        report = validate_dataset(self.root)
        self.assertEqual(len(report.issues["missing_labels"]), 1)
        self.assertFalse(report.is_clean)

    def test_orphan_label_detected(self):
        self.add("train", "a", [GOOD])
        write_label(self.root / "labels" / "train" / "ghost.txt", [GOOD])
        report = validate_dataset(self.root)
        self.assertEqual(report.issues["orphan_labels"], ["train/ghost.txt"])

    def test_empty_label_is_warning_not_error(self):
        self.add("train", "a", [])
        report = validate_dataset(self.root)
        self.assertEqual(len(report.issues["empty_labels"]), 1)
        self.assertEqual(report.negatives_total, 1)
        self.assertTrue(report.is_clean)

    def test_corrupted_image_detected(self):
        self.add("train", "a", [GOOD], data=b"\x89PNG-corrupt")
        report = validate_dataset(self.root)
        self.assertEqual(len(report.issues["corrupted_images"]), 1)

    def test_unsupported_format_detected(self):
        self.add("train", "a", None, data=make_png(), ext=".tiff")
        report = validate_dataset(self.root)
        self.assertEqual(len(report.issues["unsupported_formats"]), 1)
        self.assertEqual(report.images_total, 0)

    def test_duplicated_images_detected(self):
        payload = make_png(6, 6, (9, 9, 9))
        self.add("train", "a", [GOOD], data=payload)
        self.add("val", "b", [GOOD], data=payload)
        report = validate_dataset(self.root)
        self.assertEqual(len(report.issues["duplicated_images"]), 1)
        self.assertIn("identical to", report.issues["duplicated_images"][0])

    def test_duplicated_annotations_detected(self):
        self.add("train", "a", [GOOD, GOOD])
        report = validate_dataset(self.root)
        self.assertEqual(len(report.issues["duplicated_annotations"]), 1)

    def test_invalid_class_id_detected(self):
        self.add("train", "a", ["9 0.5 0.5 0.1 0.1"])
        report = validate_dataset(self.root)
        self.assertEqual(len(report.issues["invalid_class_ids"]), 1)

    def test_out_of_bounds_box_detected(self):
        self.add("train", "a", ["0 0.95 0.5 0.3 0.1"])
        report = validate_dataset(self.root)
        self.assertEqual(len(report.issues["out_of_bounds_boxes"]), 1)

    def test_malformed_label_detected(self):
        self.add("train", "a", ["this is not yolo"])
        report = validate_dataset(self.root)
        self.assertEqual(len(report.issues["malformed_labels"]), 1)

    def test_flat_layout_supported(self):
        write_image(self.root / "images" / "a.png")
        write_label(self.root / "labels" / "a.txt", [GOOD])
        report = validate_dataset(self.root)
        self.assertTrue(report.is_clean)
        self.assertEqual(report.split_image_counts, {"(flat)": 1})

    def test_missing_images_dir_raises(self):
        with self.assertRaises(FileNotFoundError):
            validate_dataset(self.root / "nope")


class TestReportWriters(ValidatorTestBase):

    def _report(self):
        self.add("train", "a", [GOOD])
        self.add("train", "b")  # missing label -> one error
        return validate_dataset(self.root)

    def test_json_report(self):
        report = self._report()
        path = write_report_json(report, self.root / "out" / "r.json")
        data = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(data["totals"]["images"], 2)
        self.assertEqual(data["totals"]["errors"], 1)
        self.assertFalse(data["is_clean"])
        self.assertIn("missing_labels", data["issues"])

    def test_md_report(self):
        report = self._report()
        path = write_report_md(report, self.root / "out" / "r.md")
        text = path.read_text(encoding="utf-8")
        self.assertIn("# Dataset Validation Report", text)
        self.assertIn("ISSUES FOUND", text)
        self.assertIn("missing_labels", text)
        self.assertIn("| fire | 1 |", text)

    def test_md_clean_verdict(self):
        self.add("train", "a", [GOOD])
        report = validate_dataset(self.root)
        text = write_report_md(
            report, self.root / "r.md").read_text(encoding="utf-8")
        self.assertIn("CLEAN", text)


if __name__ == "__main__":
    unittest.main()
