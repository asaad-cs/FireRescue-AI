"""Tests: the dataset_info training entry point."""
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from ai.object_detection.training import dataset_info
from ai.object_detection.tests._helpers import write_image, write_label


class TestDatasetInfo(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)

    def _patch_paths(self):
        return mock.patch.multiple(
            dataset_info,
            RAW_DATA_DIR=self.tmp / "raw",
            MERGED_DATA_DIR=self.tmp / "merged",
            PROCESSED_DATA_DIR=self.tmp / "processed",
        )

    def test_returns_1_when_processed_missing(self):
        with self._patch_paths():
            self.assertEqual(dataset_info.main(), 1)

    def test_returns_0_and_logs_summary_when_processed_exists(self):
        processed = self.tmp / "processed"
        write_image(processed / "images" / "train" / "a.png")
        write_label(processed / "labels" / "train" / "a.txt",
                    ["0 0.5 0.5 0.2 0.2"])
        write_image(processed / "images" / "val" / "b.png")
        write_label(processed / "labels" / "val" / "b.txt", [])
        with self._patch_paths():
            with self.assertLogs("firerescue.ai", level="INFO") as logs:
                self.assertEqual(dataset_info.main(), 0)
        text = "\n".join(logs.output)
        self.assertIn("processed dataset: 2 images", text)
        self.assertIn("train", text)
        self.assertIn("fire=1", text)

    def test_reports_missing_raw_sources(self):
        with self._patch_paths():
            with self.assertLogs("firerescue.ai", level="INFO") as logs:
                dataset_info.main()
        text = "\n".join(logs.output)
        self.assertIn("dfire", text)
        self.assertIn("MISSING", text)

    def test_never_raises_notimplementederror(self):
        # The Phase 8B scaffold used to raise; the implementation and
        # its callers must never see that again.
        with self._patch_paths():
            try:
                dataset_info.main()
            except NotImplementedError:  # pragma: no cover
                self.fail("dataset_info.main() is still a scaffold")


if __name__ == "__main__":
    unittest.main()
