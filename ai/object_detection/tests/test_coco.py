"""Tests: COCO instances JSON -> YOLO label conversion."""
import json
import tempfile
import unittest
from pathlib import Path

from ai.object_detection.data_tools.coco import convert_coco
from ai.object_detection.data_tools.labels import (
    BBOX_TOLERANCE,
    annotation_issues,
    read_label_file,
)

COCO_FIXTURE = {
    "categories": [
        {"id": 1, "name": "person"},
        {"id": 18, "name": "dog"},
    ],
    "images": [
        {"id": 10, "file_name": "000010.jpg", "width": 100, "height": 200},
        {"id": 20, "file_name": "000020.jpg", "width": 640, "height": 480},
        {"id": 30, "file_name": "000030.jpg", "width": 640, "height": 480},
    ],
    "annotations": [
        # image 10: one person at pixel box (10, 20, 30, 40)
        {"id": 1, "image_id": 10, "category_id": 1,
         "bbox": [10, 20, 30, 40], "iscrowd": 0},
        # image 10: a dog — must be ignored
        {"id": 2, "image_id": 10, "category_id": 18,
         "bbox": [0, 0, 50, 50], "iscrowd": 0},
        # image 20: crowd person — must be skipped
        {"id": 3, "image_id": 20, "category_id": 1,
         "bbox": [0, 0, 640, 480], "iscrowd": 1},
        # image 20: person box overflowing the image edge — clamped
        {"id": 4, "image_id": 20, "category_id": 1,
         "bbox": [600, 400, 100, 100], "iscrowd": 0},
        # image 30: degenerate zero-width box — dropped
        {"id": 5, "image_id": 30, "category_id": 1,
         "bbox": [10, 10, 0, 20], "iscrowd": 0},
    ],
}


class TestConvertCoco(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)
        self.json_path = self.tmp / "instances.json"
        self.json_path.write_text(json.dumps(COCO_FIXTURE), encoding="utf-8")
        self.out = self.tmp / "labels"

    def _convert(self):
        return convert_coco(self.json_path, self.out, {"person": 2})

    def test_only_wanted_category_is_converted(self):
        self._convert()
        anns = read_label_file(self.out / "000010.txt")
        self.assertEqual(len(anns), 1)
        self.assertEqual(anns[0].class_id, 2)

    def test_bbox_math(self):
        self._convert()
        ann = read_label_file(self.out / "000010.txt")[0]
        # (10, 20, 30, 40) in a 100x200 image.
        self.assertAlmostEqual(ann.center_x, 0.25, places=5)
        self.assertAlmostEqual(ann.center_y, 0.20, places=5)
        self.assertAlmostEqual(ann.width, 0.30, places=5)
        self.assertAlmostEqual(ann.height, 0.20, places=5)

    def test_crowd_annotations_skipped(self):
        stats = self._convert()
        self.assertEqual(stats.boxes_skipped_crowd, 1)
        anns = read_label_file(self.out / "000020.txt")
        self.assertEqual(len(anns), 1)  # only the non-crowd box

    def test_overflowing_box_is_clamped_into_bounds(self):
        self._convert()
        ann = read_label_file(self.out / "000020.txt")[0]
        # Serialization rounds to 6 decimals, so compare against the
        # same tolerance the validator enforces.
        self.assertEqual(annotation_issues(ann, nc=3), [])
        self.assertLessEqual(ann.center_x + ann.width / 2,
                             1.0 + BBOX_TOLERANCE)
        self.assertLessEqual(ann.center_y + ann.height / 2,
                             1.0 + BBOX_TOLERANCE)

    def test_degenerate_box_dropped_and_no_empty_file(self):
        stats = self._convert()
        self.assertEqual(stats.boxes_skipped_degenerate, 1)
        # Image 30 lost its only box -> no label file, not an empty one.
        self.assertFalse((self.out / "000030.txt").exists())

    def test_stats(self):
        stats = self._convert()
        self.assertEqual(stats.images_total, 3)
        self.assertEqual(stats.images_with_targets, 2)
        self.assertEqual(stats.boxes_written, 2)
        self.assertEqual(stats.boxes_per_class, {2: 2})

    def test_missing_category_raises(self):
        with self.assertRaises(ValueError) as ctx:
            convert_coco(self.json_path, self.out, {"unicorn": 0})
        self.assertIn("unicorn", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
