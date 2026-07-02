"""Tests: shared and object-detection path constants, plus ensure_dir."""
import tempfile
import unittest
from pathlib import Path

from ai.object_detection import paths as od_paths
from ai.shared.utils import paths as shared_paths


class TestSharedPaths(unittest.TestCase):

    def test_ai_root_is_the_ai_package_dir(self):
        self.assertEqual(shared_paths.AI_ROOT.name, "ai")
        self.assertTrue((shared_paths.AI_ROOT / "__init__.py").is_file())

    def test_project_root_is_parent_of_ai_root(self):
        self.assertEqual(shared_paths.PROJECT_ROOT, shared_paths.AI_ROOT.parent)

    def test_paths_are_absolute(self):
        self.assertTrue(shared_paths.AI_ROOT.is_absolute())
        self.assertTrue(shared_paths.PROJECT_ROOT.is_absolute())

    def test_notebooks_dir_is_under_ai_root(self):
        self.assertTrue(
            shared_paths.NOTEBOOKS_DIR.is_relative_to(shared_paths.AI_ROOT)
        )


class TestObjectDetectionPaths(unittest.TestCase):

    def test_module_root_is_the_object_detection_dir(self):
        self.assertEqual(od_paths.MODULE_ROOT.name, "object_detection")
        self.assertTrue((od_paths.MODULE_ROOT / "__init__.py").is_file())

    def test_module_root_lives_under_ai_root(self):
        self.assertEqual(od_paths.MODULE_ROOT.parent, shared_paths.AI_ROOT)

    def test_all_dirs_are_under_module_root(self):
        for p in (
            od_paths.CONFIGS_DIR,
            od_paths.DATASETS_DIR,
            od_paths.RAW_DATA_DIR,
            od_paths.PROCESSED_DATA_DIR,
            od_paths.EXTERNAL_DATA_DIR,
            od_paths.MODELS_DIR,
            od_paths.CHECKPOINTS_DIR,
            od_paths.EXPORTS_DIR,
        ):
            self.assertTrue(p.is_relative_to(od_paths.MODULE_ROOT), p)

    def test_workspace_dirs_exist_on_disk(self):
        for p in (od_paths.CONFIGS_DIR, od_paths.DATASETS_DIR, od_paths.MODELS_DIR):
            self.assertTrue(p.is_dir(), p)


class TestEnsureDir(unittest.TestCase):

    def test_creates_missing_nested_dir(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "a" / "b" / "c"
            result = shared_paths.ensure_dir(target)
            self.assertTrue(target.is_dir())
            self.assertEqual(result, target)

    def test_existing_dir_is_a_no_op(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp)
            self.assertEqual(shared_paths.ensure_dir(target), target)
            self.assertTrue(target.is_dir())


if __name__ == "__main__":
    unittest.main()
