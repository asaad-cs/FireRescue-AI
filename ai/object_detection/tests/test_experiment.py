"""Tests: ai.shared.utils.experiment — run naming and checkpoint discovery."""
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from ai.shared.utils.experiment import find_weights, list_runs, make_run_name


class TestMakeRunName(unittest.TestCase):

    def test_name_includes_experiment_and_timestamp(self):
        stamp = datetime(2026, 7, 2, 13, 45, 9)
        self.assertEqual(
            make_run_name("detector", now=stamp), "detector-20260702-134509"
        )

    def test_current_time_used_by_default(self):
        self.assertTrue(make_run_name("exp").startswith("exp-"))


class TestListRuns(unittest.TestCase):

    def test_missing_dir_gives_empty_list(self):
        self.assertEqual(list_runs(Path("does/not/exist")), [])

    def test_runs_sorted_newest_first(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "exp-20260101-000000").mkdir()
            (root / "exp-20260201-000000").mkdir()
            (root / "stray.txt").write_text("", encoding="utf-8")
            runs = list_runs(root)
            self.assertEqual(
                [r.name for r in runs],
                ["exp-20260201-000000", "exp-20260101-000000"],
            )


class TestFindWeights(unittest.TestCase):

    def _make_run(self, root: Path, name: str, with_best: bool) -> Path:
        weights = root / name / "weights"
        weights.mkdir(parents=True)
        if with_best:
            (weights / "best.pt").write_bytes(b"")
        return weights

    def test_none_when_no_runs(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertIsNone(find_weights("best", Path(tmp)))

    def test_newest_run_with_weights_wins(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            old = self._make_run(root, "exp-20260101-000000", with_best=True)
            self._make_run(root, "exp-20260201-000000", with_best=False)
            self.assertEqual(find_weights("best", root), old / "best.pt")

    def test_invalid_kind_raises(self):
        with self.assertRaises(ValueError):
            find_weights("newest", Path("unused"))


if __name__ == "__main__":
    unittest.main()
