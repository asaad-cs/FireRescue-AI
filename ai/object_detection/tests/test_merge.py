"""Tests: standardizing merge with deduplication and provenance."""
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from ai.object_detection.data_tools.labels import read_label_file
from ai.object_detection.data_tools.merge import (
    merge_sources,
    write_merge_report,
)
from ai.object_detection.data_tools.sources import SourceSpec
from ai.object_detection.tests._helpers import (
    build_yolo_source,
    write_image,
    write_label,
)

# Source class order intentionally differs from the unified one
# (0 smoke, 1 fire — the D-Fire convention).
SWAPPED = {0: 1, 1: 0}


def spec(name: str, **kwargs) -> SourceSpec:
    defaults = dict(kind="yolo", root=name, enabled=True, class_map=SWAPPED)
    defaults.update(kwargs)
    return SourceSpec(name=name, **defaults)


class MergeTestBase(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)
        self.raw = self.tmp / "raw"
        self.merged = self.tmp / "merged"

    def merge(self, specs):
        return merge_sources(specs, raw_root=self.raw,
                             merged_dir=self.merged)


class TestMergeSources(MergeTestBase):

    def test_basic_merge_with_remapping(self):
        build_yolo_source(self.raw / "src_a", "train", {
            "img1": ["0 0.5 0.5 0.2 0.2"],   # smoke in source ids
            "img2": ["1 0.5 0.5 0.2 0.2"],   # fire in source ids
        })
        result = self.merge([spec("src_a")])
        self.assertEqual(result.images_total, 2)
        self.assertEqual(result.class_counts, {"fire": 1, "smoke": 1,
                                               "person": 0})
        anns = read_label_file(self.merged / "labels" / "src_a__img1.txt")
        self.assertEqual(anns[0].class_id, 1)  # smoke remapped 0 -> 1

    def test_provenance_written(self):
        build_yolo_source(self.raw / "src_a", "train",
                          {"img1": ["0 0.5 0.5 0.2 0.2"]})
        self.merge([spec("src_a")])
        data = json.loads(
            (self.merged / "provenance.json").read_text(encoding="utf-8"))
        entry = data["entries"][0]
        self.assertEqual(entry["file"], "src_a__img1.png")
        self.assertEqual(entry["source"], "src_a")
        self.assertIn("img1.png", entry["original"])
        self.assertEqual(len(entry["md5"]), 32)

    def test_identical_images_across_sources_merged_once(self):
        build_yolo_source(self.raw / "src_a", "train",
                          {"img1": ["0 0.5 0.5 0.2 0.2"]})
        (self.raw / "src_b" / "train" / "images").mkdir(parents=True)
        shutil.copy2(self.raw / "src_a" / "train" / "images" / "img1.png",
                     self.raw / "src_b" / "train" / "images" / "copy.png")
        write_label(self.raw / "src_b" / "train" / "labels" / "copy.txt",
                    ["0 0.5 0.5 0.2 0.2"])
        result = self.merge([spec("src_a"), spec("src_b")])
        self.assertEqual(result.images_total, 1)
        stats_b = result.sources[1]
        self.assertEqual(stats_b.duplicates_skipped, 1)

    def test_unmapped_class_boxes_dropped(self):
        build_yolo_source(self.raw / "src_a", "train", {
            "img1": ["0 0.5 0.5 0.2 0.2", "5 0.4 0.4 0.1 0.1"],
        })
        result = self.merge([spec("src_a")])
        stats = result.sources[0]
        self.assertEqual(stats.boxes_dropped_unmapped, 1)
        self.assertEqual(stats.boxes_merged, 1)

    def test_corrupted_image_excluded(self):
        build_yolo_source(self.raw / "src_a", "train",
                          {"good": ["0 0.5 0.5 0.2 0.2"]})
        bad = self.raw / "src_a" / "train" / "images" / "bad.png"
        bad.write_bytes(b"not-a-png")
        write_label(self.raw / "src_a" / "train" / "labels" / "bad.txt",
                    ["0 0.5 0.5 0.2 0.2"])
        result = self.merge([spec("src_a")])
        self.assertEqual(result.images_total, 1)
        self.assertEqual(result.sources[0].corrupted_skipped, 1)

    def test_malformed_label_excluded(self):
        build_yolo_source(self.raw / "src_a", "train", {
            "good": ["0 0.5 0.5 0.2 0.2"],
            "bad": ["garbage line"],
        })
        result = self.merge([spec("src_a")])
        self.assertEqual(result.images_total, 1)
        self.assertEqual(result.sources[0].malformed_skipped, 1)

    def test_image_without_label_skipped(self):
        build_yolo_source(self.raw / "src_a", "train", {
            "good": ["0 0.5 0.5 0.2 0.2"],
            "unlabeled": None,
        })
        result = self.merge([spec("src_a")])
        self.assertEqual(result.images_total, 1)
        self.assertEqual(result.sources[0].missing_label_skipped, 1)

    def test_negatives_kept_with_empty_labels(self):
        build_yolo_source(self.raw / "src_a", "train", {"neg": []})
        result = self.merge([spec("src_a")])
        self.assertEqual(result.images_total, 1)
        self.assertEqual(result.sources[0].negatives_merged, 1)
        label = self.merged / "labels" / "src_a__neg.txt"
        self.assertEqual(label.read_text(encoding="utf-8"), "")

    def test_duplicate_annotation_lines_collapsed(self):
        build_yolo_source(self.raw / "src_a", "train", {
            "img1": ["0 0.5 0.5 0.2 0.2", "0 0.5 0.5 0.2 0.2"],
        })
        self.merge([spec("src_a")])
        anns = read_label_file(self.merged / "labels" / "src_a__img1.txt")
        self.assertEqual(len(anns), 1)

    def test_same_stem_in_two_splits_gets_unique_names(self):
        build_yolo_source(self.raw / "src_a", "train",
                          {"img": ["0 0.5 0.5 0.2 0.2"]})
        build_yolo_source(self.raw / "src_a", "val",
                          {"img": ["1 0.5 0.5 0.2 0.2"]})
        result = self.merge([spec("src_a")])
        self.assertEqual(result.images_total, 2)
        images = sorted(p.name for p in (self.merged / "images").iterdir())
        self.assertEqual(len(images), 2)
        self.assertEqual(len(set(images)), 2)

    def test_empty_source_directory_skipped_with_record(self):
        build_yolo_source(self.raw / "src_a", "train",
                          {"img1": ["0 0.5 0.5 0.2 0.2"]})
        (self.raw / "empty_src").mkdir(parents=True)
        result = self.merge([spec("src_a"), spec("empty_src")])
        self.assertEqual(result.skipped_sources, ["empty_src"])
        self.assertEqual(len(result.sources), 1)

    def test_missing_source_skipped_with_record(self):
        build_yolo_source(self.raw / "src_a", "train",
                          {"img1": ["0 0.5 0.5 0.2 0.2"]})
        result = self.merge([spec("src_a"), spec("ghost")])
        self.assertEqual(result.skipped_sources, ["ghost"])
        self.assertEqual(len(result.sources), 1)

    def test_all_sources_missing_raises(self):
        with self.assertRaises(RuntimeError):
            self.merge([spec("ghost")])

    def test_disabled_source_ignored(self):
        build_yolo_source(self.raw / "src_a", "train",
                          {"img1": ["0 0.5 0.5 0.2 0.2"]})
        result = self.merge([spec("src_a"),
                             spec("src_b", enabled=False)])
        self.assertEqual(len(result.sources), 1)
        self.assertEqual(result.skipped_sources, [])

    def test_rerun_rebuilds_cleanly(self):
        build_yolo_source(self.raw / "src_a", "train",
                          {"img1": ["0 0.5 0.5 0.2 0.2"]})
        self.merge([spec("src_a")])
        first = sorted(p.name for p in (self.merged / "images").iterdir())
        self.merge([spec("src_a")])
        second = sorted(p.name for p in (self.merged / "images").iterdir())
        self.assertEqual(first, second)

    def test_merge_stats_json_written(self):
        build_yolo_source(self.raw / "src_a", "train",
                          {"img1": ["0 0.5 0.5 0.2 0.2"]})
        self.merge([spec("src_a")])
        data = json.loads(
            (self.merged / "merge_stats.json").read_text(encoding="utf-8"))
        self.assertEqual(data["sources"][0]["images_merged"], 1)


class TestMergeCocoSource(MergeTestBase):

    def test_coco_source_end_to_end(self):
        root = self.raw / "cocosrc"
        write_image(root / "val" / "pic1.png")
        write_image(root / "val" / "pic2.png")
        coco = {
            "categories": [{"id": 1, "name": "person"}],
            "images": [
                {"id": 1, "file_name": "pic1.png", "width": 4, "height": 4},
                {"id": 2, "file_name": "pic2.png", "width": 4, "height": 4},
            ],
            "annotations": [
                {"id": 1, "image_id": 1, "category_id": 1,
                 "bbox": [1, 1, 2, 2], "iscrowd": 0},
            ],
        }
        ann_path = root / "instances.json"
        ann_path.write_text(json.dumps(coco), encoding="utf-8")
        result = self.merge([
            SourceSpec(name="cocosrc", kind="coco", root="cocosrc",
                       enabled=True, images="val",
                       annotations="instances.json",
                       categories={"person": 2}),
        ])
        # Only the image with a person annotation is merged.
        self.assertEqual(result.images_total, 1)
        self.assertEqual(result.class_counts["person"], 1)
        anns = read_label_file(self.merged / "labels" / "cocosrc__pic1.txt")
        self.assertEqual(anns[0].class_id, 2)
        # The temporary converted-label directory must be cleaned up.
        self.assertFalse((self.merged / "_coco_labels").exists())


class TestMergeReport(MergeTestBase):

    def test_report_content(self):
        build_yolo_source(self.raw / "src_a", "train",
                          {"img1": ["0 0.5 0.5 0.2 0.2"]})
        result = self.merge([spec("src_a"), spec("ghost")])
        path = write_merge_report(result, self.tmp / "merge_report.md")
        text = path.read_text(encoding="utf-8")
        self.assertIn("# Dataset Merge Report", text)
        self.assertIn("src_a", text)
        self.assertIn("Skipped sources", text)
        self.assertIn("ghost", text)
        self.assertIn("Standardization rules", text)


if __name__ == "__main__":
    unittest.main()
