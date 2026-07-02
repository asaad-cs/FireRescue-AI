"""Tests: ai.object_detection.training.predict — source validation and argument parsing."""
import tempfile
import unittest
from pathlib import Path

from ai.object_detection.training.predict import parse_args, validate_source
from ai.object_detection.config import ConfigError


class TestValidateSource(unittest.TestCase):

    def test_missing_path_raises(self):
        with self.assertRaises(ConfigError):
            validate_source("no/such/image.jpg")

    def test_unsupported_file_type_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "notes.txt"
            path.write_text("", encoding="utf-8")
            with self.assertRaises(ConfigError):
                validate_source(str(path))

    def test_single_image_accepted(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "frame.PNG"
            path.write_bytes(b"")
            self.assertEqual(validate_source(str(path)), path)

    def test_folder_with_images_accepted(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "a.jpg").write_bytes(b"")
            self.assertEqual(validate_source(tmp), Path(tmp))

    def test_folder_without_images_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "readme.md").write_text("", encoding="utf-8")
            with self.assertRaises(ConfigError):
                validate_source(tmp)


class TestParseArgs(unittest.TestCase):

    def test_source_is_required(self):
        with self.assertRaises(SystemExit):
            parse_args([])

    def test_defaults(self):
        args = parse_args(["--source", "img.jpg"])
        self.assertEqual(args.source, "img.jpg")
        self.assertIsNone(args.weights)
        self.assertIsNone(args.conf)
        self.assertIsNone(args.save_dir)

    def test_conf_is_parsed_as_float(self):
        args = parse_args(["--source", "img.jpg", "--conf", "0.6"])
        self.assertEqual(args.conf, 0.6)


if __name__ == "__main__":
    unittest.main()
