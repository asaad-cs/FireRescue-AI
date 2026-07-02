"""Tests: ai.object_detection.training.evaluate — weight resolution and metrics extraction."""
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from ai.object_detection.training.evaluate import extract_metrics, parse_args, resolve_weights
from ai.object_detection.config import ConfigError


class TestResolveWeights(unittest.TestCase):

    def test_explicit_existing_path_is_used(self):
        with tempfile.TemporaryDirectory() as tmp:
            weights = Path(tmp) / "best.pt"
            weights.write_bytes(b"")
            self.assertEqual(resolve_weights(str(weights)), weights)

    def test_explicit_missing_path_raises(self):
        with self.assertRaises(ConfigError):
            resolve_weights("no/such/weights.pt")

    def test_default_uses_newest_best_checkpoint(self):
        found = Path("run") / "weights" / "best.pt"
        with patch("ai.object_detection.training.evaluate.find_weights", return_value=found):
            self.assertEqual(resolve_weights(None), found)

    def test_default_with_no_runs_raises(self):
        with patch("ai.object_detection.training.evaluate.find_weights", return_value=None):
            with self.assertRaises(ConfigError):
                resolve_weights(None)


class TestExtractMetrics(unittest.TestCase):

    def test_headline_metrics_are_extracted(self):
        results = SimpleNamespace(
            box=SimpleNamespace(map50=0.81, map=0.55, mp=0.9, mr=0.7)
        )
        self.assertEqual(
            extract_metrics(results),
            {"mAP50": 0.81, "mAP50-95": 0.55, "precision": 0.9, "recall": 0.7},
        )


class TestParseArgs(unittest.TestCase):

    def test_defaults(self):
        args = parse_args([])
        self.assertIsNone(args.weights)
        self.assertEqual(args.split, "val")

    def test_invalid_split_rejected(self):
        with self.assertRaises(SystemExit):
            parse_args(["--split", "train"])


if __name__ == "__main__":
    unittest.main()
