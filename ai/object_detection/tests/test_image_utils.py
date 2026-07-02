"""Tests: stdlib image probing and content hashing."""
import tempfile
import unittest
from pathlib import Path

from ai.object_detection.data_tools.image_utils import (
    SUPPORTED_EXTENSIONS,
    ImageError,
    decode_check,
    file_hash,
    probe_image,
)
from ai.object_detection.tests._helpers import (
    make_bmp,
    make_jpeg_header,
    make_png,
)


class TestProbeImage(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)

    def _write(self, name: str, data: bytes) -> Path:
        path = self.tmp / name
        path.write_bytes(data)
        return path

    def test_png_dimensions(self):
        info = probe_image(self._write("a.png", make_png(12, 7)))
        self.assertEqual((info.width, info.height, info.format), (12, 7, "png"))

    def test_bmp_dimensions(self):
        info = probe_image(self._write("a.bmp", make_bmp(9, 5)))
        self.assertEqual((info.width, info.height, info.format), (9, 5, "bmp"))

    def test_jpeg_dimensions(self):
        info = probe_image(self._write("a.jpg", make_jpeg_header(640, 480)))
        self.assertEqual((info.width, info.height), (640, 480))
        self.assertEqual(info.format, "jpeg")

    def test_jpeg_alias_extension(self):
        info = probe_image(self._write("a.jpeg", make_jpeg_header(3, 2)))
        self.assertEqual((info.width, info.height), (3, 2))

    def test_unsupported_extension_rejected(self):
        path = self._write("a.gif", make_png())
        with self.assertRaises(ImageError):
            probe_image(path)

    def test_truncated_png_is_corrupt(self):
        with self.assertRaises(ImageError):
            probe_image(self._write("a.png", make_png()[:10]))

    def test_wrong_signature_is_corrupt(self):
        with self.assertRaises(ImageError):
            probe_image(self._write("a.png", b"\x00" * 64))

    def test_jpeg_without_sof_is_corrupt(self):
        with self.assertRaises(ImageError):
            probe_image(self._write("a.jpg", b"\xff\xd8\xff\xd9"))

    def test_empty_file_is_corrupt(self):
        with self.assertRaises(ImageError):
            probe_image(self._write("a.jpg", b""))

    def test_zero_dimension_rejected(self):
        with self.assertRaises(ImageError):
            probe_image(self._write("a.png", make_png(0, 4)))

    def test_supported_extensions_match_predict_contract(self):
        self.assertEqual(
            set(SUPPORTED_EXTENSIONS), {".jpg", ".jpeg", ".png", ".bmp"}
        )


class TestDecodeCheck(unittest.TestCase):

    def test_valid_png_passes_deep_check(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "a.png"
            path.write_bytes(make_png(8, 8))
            self.assertTrue(decode_check(path))

    def test_garbage_fails_deep_check_when_cv2_present(self):
        try:
            import cv2  # noqa: F401
        except ImportError:
            self.skipTest("cv2 not installed")
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "a.png"
            path.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 64)
            self.assertFalse(decode_check(path))


class TestFileHash(unittest.TestCase):

    def test_identical_content_same_hash(self):
        with tempfile.TemporaryDirectory() as tmp:
            a, b = Path(tmp) / "a.bin", Path(tmp) / "b.bin"
            a.write_bytes(b"payload")
            b.write_bytes(b"payload")
            self.assertEqual(file_hash(a), file_hash(b))

    def test_different_content_different_hash(self):
        with tempfile.TemporaryDirectory() as tmp:
            a, b = Path(tmp) / "a.bin", Path(tmp) / "b.bin"
            a.write_bytes(b"payload-1")
            b.write_bytes(b"payload-2")
            self.assertNotEqual(file_hash(a), file_hash(b))

    def test_md5_hex_format(self):
        with tempfile.TemporaryDirectory() as tmp:
            a = Path(tmp) / "a.bin"
            a.write_bytes(b"x")
            digest = file_hash(a)
            self.assertEqual(len(digest), 32)
            int(digest, 16)  # must be valid hex


if __name__ == "__main__":
    unittest.main()
