"""Tests: master-library → runtime-folder export tool (Phase 8H)."""
import tempfile
import unittest
from pathlib import Path

from ai.object_detection.data_tools.export_simulation_library import (
    ExportRules,
    export_library,
)
from ai.object_detection.tests._helpers import write_image


class ExportTestBase(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)
        self.source = self.tmp / "master"
        self.dest = self.tmp / "runtime"

    def add(self, category: str, name: str, subcategory: str | None = None):
        folder = self.source / category
        if subcategory:
            folder = folder / subcategory
        write_image(folder / name)

    def export(self, **rule_kwargs):
        return export_library(
            source=self.source, dest=self.dest,
            rules=ExportRules(**rule_kwargs),
        )

    def names(self, category: str) -> list[str]:
        folder = self.dest / category
        if not folder.is_dir():
            return []
        return sorted(p.name for p in folder.iterdir() if p.is_file())


class TestDiscoveryAndFlattening(ExportTestBase):

    def test_root_files_keep_names_subfolders_get_prefix(self):
        self.add("fire", "root.jpg")
        self.add("fire", "blaze.jpg", subcategory="office")
        result = self.export()
        self.assertEqual(result.exported["fire"], 2)
        self.assertEqual(self.names("fire"),
                         ["office__blaze.jpg", "root.jpg"])

    def test_all_categories_exported_by_default(self):
        self.add("fire", "a.jpg")
        self.add("smoke", "b.jpg", subcategory="corridor")
        result = self.export()
        self.assertEqual(sorted(result.exported), ["fire", "smoke"])

    def test_extension_filter(self):
        self.add("fire", "a.jpg")
        (self.source / "fire" / "notes.txt").write_text("x", encoding="utf-8")
        (self.source / "fire" / ".gitkeep").write_text("", encoding="utf-8")
        result = self.export()
        self.assertEqual(result.exported["fire"], 1)

    def test_empty_category_exports_zero_gracefully(self):
        (self.source / "fire_person").mkdir(parents=True)
        result = self.export()
        self.assertEqual(result.exported["fire_person"], 0)
        self.assertTrue((self.dest / "fire_person").is_dir())

    def test_missing_source_raises(self):
        with self.assertRaises(FileNotFoundError):
            export_library(source=self.tmp / "nope", dest=self.dest)

    def test_unknown_category_raises(self):
        self.add("fire", "a.jpg")
        with self.assertRaises(ValueError) as ctx:
            self.export(categories=("unicorn",))
        self.assertIn("unicorn", str(ctx.exception))


class TestSelectionRules(ExportTestBase):

    def setUp(self):
        super().setUp()
        for i in range(6):
            self.add("fire", f"f{i}.jpg", subcategory="office")
            self.add("fire", f"w{i}.jpg", subcategory="warehouse")
        self.add("smoke", "s0.jpg", subcategory="office")

    def test_category_selection(self):
        result = self.export(categories=("smoke",))
        self.assertEqual(list(result.exported), ["smoke"])
        self.assertEqual(self.names("fire"), [])

    def test_subcategory_selection(self):
        self.export(subcategories=("warehouse",))
        self.assertEqual(len(self.names("fire")), 6)
        self.assertTrue(all(n.startswith("warehouse__")
                            for n in self.names("fire")))
        self.assertEqual(self.names("smoke"), [])
        # smoke has no warehouse sub-folder -> zero, gracefully

    def test_limit_without_random_takes_first_sorted(self):
        self.export(limit=3)
        self.assertEqual(
            self.names("fire"),
            ["office__f0.jpg", "office__f1.jpg", "office__f2.jpg"],
        )

    def test_random_sample_respects_limit_and_seed(self):
        result = self.export(limit=4, randomize=True, seed=7)
        first = self.names("fire")
        self.assertEqual(len(first), 4)
        self.assertEqual(result.exported["fire"], 4)
        # Same seed reproduces the same sample.
        self.export(limit=4, randomize=True, seed=7, clean=True)
        self.assertEqual(self.names("fire"), first)

    def test_different_seed_changes_sample(self):
        self.export(limit=4, randomize=True, seed=7)
        first = self.names("fire")
        self.export(limit=4, randomize=True, seed=1234, clean=True)
        self.assertNotEqual(self.names("fire"), first)

    def test_limit_larger_than_pool_takes_everything(self):
        self.export(categories=("smoke",), limit=99)
        self.assertEqual(len(self.names("smoke")), 1)


class TestOverwriteAndClean(ExportTestBase):

    def setUp(self):
        super().setUp()
        self.add("fire", "a.jpg", subcategory="office")

    def test_existing_files_skipped_without_overwrite(self):
        self.export()
        target = self.dest / "fire" / "office__a.jpg"
        target.write_bytes(b"sentinel")
        result = self.export()
        self.assertEqual(target.read_bytes(), b"sentinel")
        self.assertEqual(result.skipped_existing, 1)
        self.assertEqual(result.exported["fire"], 0)

    def test_overwrite_replaces_existing(self):
        self.export()
        target = self.dest / "fire" / "office__a.jpg"
        target.write_bytes(b"sentinel")
        result = self.export(overwrite=True)
        self.assertNotEqual(target.read_bytes(), b"sentinel")
        self.assertEqual(result.exported["fire"], 1)

    def test_clean_removes_stale_runtime_files(self):
        stale = self.dest / "fire" / "stale.jpg"
        stale.parent.mkdir(parents=True)
        stale.write_bytes(b"old")
        result = self.export(clean=True)
        self.assertFalse(stale.exists())
        self.assertEqual(self.names("fire"), ["office__a.jpg"])
        self.assertEqual(result.cleaned_categories, ["fire"])

    def test_clean_never_touches_unselected_categories(self):
        other = self.dest / "smoke" / "keep.jpg"
        other.parent.mkdir(parents=True)
        other.write_bytes(b"keep")
        self.export(categories=("fire",), clean=True)
        self.assertTrue(other.exists())

    def test_master_library_is_never_modified(self):
        before = sorted(p.name for p in
                        (self.source / "fire" / "office").iterdir())
        self.export(clean=True, overwrite=True)
        after = sorted(p.name for p in
                       (self.source / "fire" / "office").iterdir())
        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
