"""Tests: download registry, checksum verification, and extraction.

No network access: transfers use file:// URLs against temp files.
"""
import hashlib
import tempfile
import unittest
import zipfile
from pathlib import Path

from ai.object_detection.data_tools.download import (
    DOWNLOADS,
    MANUAL_SOURCES,
    download_file,
    extract_zip,
)


class TestDownloadRegistry(unittest.TestCase):

    def test_specs_are_wellformed(self):
        for spec in DOWNLOADS:
            self.assertTrue(spec.url.startswith(("http://", "https://")),
                            spec.name)
            self.assertEqual(len(spec.md5), 32, spec.name)
            int(spec.md5, 16)
            self.assertFalse(Path(spec.dest).is_absolute(), spec.name)

    def test_names_and_destinations_unique(self):
        names = [d.name for d in DOWNLOADS]
        dests = [d.dest for d in DOWNLOADS]
        self.assertEqual(len(names), len(set(names)))
        self.assertEqual(len(dests), len(set(dests)))

    def test_manual_sources_documented(self):
        self.assertTrue(any("dfire" in m for m in MANUAL_SOURCES))


class TestDownloadFile(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)
        self.payload = b"dataset-bytes"
        self.md5 = hashlib.md5(self.payload).hexdigest()
        self.source = self.tmp / "remote.bin"
        self.source.write_bytes(self.payload)
        self.url = self.source.resolve().as_uri()

    def test_download_and_verify(self):
        dest = self.tmp / "out" / "file.bin"
        download_file(self.url, dest, self.md5)
        self.assertEqual(dest.read_bytes(), self.payload)
        self.assertFalse(dest.with_suffix(".bin.part").exists())

    def test_existing_verified_file_not_refetched(self):
        dest = self.tmp / "file.bin"
        dest.write_bytes(self.payload)
        # A bogus URL proves no fetch happens when the checksum matches.
        download_file("file:///nonexistent/nope.bin", dest, self.md5)
        self.assertEqual(dest.read_bytes(), self.payload)

    def test_checksum_mismatch_raises_and_removes_partial(self):
        dest = self.tmp / "file.bin"
        with self.assertRaises(RuntimeError):
            download_file(self.url, dest, "0" * 32)
        self.assertFalse(dest.exists())
        self.assertFalse(dest.with_suffix(".bin.part").exists())


class TestExtractZip(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)
        self.archive = self.tmp / "a.zip"
        with zipfile.ZipFile(self.archive, "w") as zf:
            zf.writestr("sub/one.txt", "1")
            zf.writestr("two.txt", "2")

    def test_extracts_all_members(self):
        out = self.tmp / "out"
        extract_zip(self.archive, out)
        self.assertEqual((out / "sub" / "one.txt").read_text(), "1")
        self.assertEqual((out / "two.txt").read_text(), "2")

    def test_second_extraction_is_a_noop(self):
        out = self.tmp / "out"
        extract_zip(self.archive, out)
        marker = out / "two.txt"
        before = marker.stat().st_mtime_ns
        extract_zip(self.archive, out)
        self.assertEqual(marker.stat().st_mtime_ns, before)


if __name__ == "__main__":
    unittest.main()
