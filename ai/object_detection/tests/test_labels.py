"""Tests: YOLO label parsing, validation, and class remapping."""
import tempfile
import unittest
from pathlib import Path

from ai.object_detection.data_tools.labels import (
    BoxAnnotation,
    LabelError,
    annotation_issues,
    count_duplicate_annotations,
    parse_label_line,
    read_label_file,
    remap_class_ids,
    write_label_file,
)

BOX = BoxAnnotation(0, 0.5, 0.5, 0.2, 0.2)


class TestParseLabelLine(unittest.TestCase):

    def test_valid_line(self):
        ann = parse_label_line("1 0.5 0.25 0.1 0.2")
        self.assertEqual(ann.class_id, 1)
        self.assertAlmostEqual(ann.center_y, 0.25)

    def test_wrong_token_count_raises(self):
        with self.assertRaises(LabelError):
            parse_label_line("1 0.5 0.5 0.1")
        with self.assertRaises(LabelError):
            parse_label_line("1 0.5 0.5 0.1 0.1 0.9")

    def test_non_numeric_token_raises(self):
        with self.assertRaises(LabelError):
            parse_label_line("fire 0.5 0.5 0.1 0.1")

    def test_float_class_id_raises(self):
        with self.assertRaises(LabelError):
            parse_label_line("1.5 0.5 0.5 0.1 0.1")


class TestReadWriteLabelFile(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)

    def test_roundtrip(self):
        path = self.tmp / "a.txt"
        original = [BOX, BoxAnnotation(2, 0.1, 0.9, 0.05, 0.1)]
        write_label_file(path, original)
        self.assertEqual(read_label_file(path), original)

    def test_empty_file_is_valid_negative(self):
        path = self.tmp / "a.txt"
        write_label_file(path, [])
        self.assertEqual(path.read_text(encoding="utf-8"), "")
        self.assertEqual(read_label_file(path), [])

    def test_blank_lines_are_skipped(self):
        path = self.tmp / "a.txt"
        path.write_text("0 0.5 0.5 0.1 0.1\n\n\n1 0.5 0.5 0.1 0.1\n",
                        encoding="utf-8")
        self.assertEqual(len(read_label_file(path)), 2)

    def test_malformed_line_names_file_and_line(self):
        path = self.tmp / "bad.txt"
        path.write_text("0 0.5 0.5 0.1 0.1\nnot a label\n", encoding="utf-8")
        with self.assertRaises(LabelError) as ctx:
            read_label_file(path)
        self.assertIn("bad.txt:2", str(ctx.exception))


class TestAnnotationIssues(unittest.TestCase):

    def test_valid_annotation_has_no_issues(self):
        self.assertEqual(annotation_issues(BOX, nc=3), [])

    def test_invalid_class_id(self):
        issues = annotation_issues(BoxAnnotation(3, 0.5, 0.5, 0.1, 0.1), nc=3)
        self.assertTrue(any("class id" in i for i in issues))
        issues = annotation_issues(BoxAnnotation(-1, 0.5, 0.5, 0.1, 0.1), nc=3)
        self.assertTrue(any("class id" in i for i in issues))

    def test_box_outside_image(self):
        issues = annotation_issues(BoxAnnotation(0, 0.95, 0.5, 0.2, 0.1), nc=3)
        self.assertTrue(any("outside image" in i for i in issues))

    def test_tiny_overflow_within_tolerance_is_ok(self):
        ann = BoxAnnotation(0, 0.5, 0.5, 1.0 + 1e-4, 0.5)
        self.assertEqual(annotation_issues(ann, nc=3), [])

    def test_non_positive_size(self):
        issues = annotation_issues(BoxAnnotation(0, 0.5, 0.5, 0.0, 0.1), nc=3)
        self.assertTrue(any("non-positive" in i for i in issues))


class TestDuplicatesAndRemap(unittest.TestCase):

    def test_duplicate_annotations_counted(self):
        self.assertEqual(count_duplicate_annotations([BOX, BOX, BOX]), 2)
        self.assertEqual(count_duplicate_annotations([BOX]), 0)

    def test_remap_translates_ids(self):
        anns = [BoxAnnotation(0, 0.5, 0.5, 0.1, 0.1),
                BoxAnnotation(1, 0.4, 0.4, 0.1, 0.1)]
        out = remap_class_ids(anns, {0: 1, 1: 0})
        self.assertEqual([a.class_id for a in out], [1, 0])
        # Geometry must be untouched.
        self.assertEqual(out[0].center_x, 0.5)

    def test_remap_drops_unmapped_and_null_classes(self):
        anns = [BoxAnnotation(0, 0.5, 0.5, 0.1, 0.1),
                BoxAnnotation(7, 0.4, 0.4, 0.1, 0.1),
                BoxAnnotation(1, 0.3, 0.3, 0.1, 0.1)]
        out = remap_class_ids(anns, {0: 2, 1: None})
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0].class_id, 2)

    def test_as_line_format(self):
        line = BoxAnnotation(2, 0.5, 0.25, 0.125, 0.0625).as_line()
        self.assertEqual(line, "2 0.500000 0.250000 0.125000 0.062500")


if __name__ == "__main__":
    unittest.main()
