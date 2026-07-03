"""Export the master simulation image library into the runtime folder.

The permanent, curated image library lives in assets/simulation_dataset/
(one folder per detection category, optional scene sub-folders). The
simulator itself only ever reads the flat runtime folder
simulation/camera/images/ — this tool builds that runtime folder from
the master library according to configurable rules:

    python -m ai.object_detection.data_tools.export_simulation_library
        [--categories fire smoke ...]      only these categories
        [--subcategories office dataset]   only these scene sub-folders
        [--limit N]                        at most N images per category
        [--random]                         seeded random sample instead of
                                           the first N (sorted)
        [--seed N]                         RNG seed for --random (default 42)
        [--overwrite]                      replace files that already exist
        [--clean]                          delete each selected category's
                                           runtime folder before exporting
        [--source DIR] [--dest DIR]        override the default locations

Images found in scene sub-folders are flattened into the category's
runtime folder with a '<subcategory>__' name prefix (the camera
provider reads flat category folders); images placed directly in a
category root keep their names. The tool never modifies the master
library and never touches runtime categories that were not selected.
"""
import argparse
import random
import shutil
import sys
from dataclasses import dataclass, field
from pathlib import Path

from ai.shared.utils.logger import get_logger
from ai.shared.utils.paths import PROJECT_ROOT

log = get_logger("data_tools.export_simulation_library")

DEFAULT_SOURCE = PROJECT_ROOT / "assets" / "simulation_dataset"
DEFAULT_DEST = PROJECT_ROOT / "simulation" / "camera" / "images"
DEFAULT_SEED = 42

# Must stay aligned with simulation_camera.yaml's extensions.
IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png")


@dataclass(frozen=True)
class ExportRules:
    """Configurable selection rules for one export run."""

    categories: tuple[str, ...] = ()      # empty = every category found
    subcategories: tuple[str, ...] = ()   # empty = every sub-folder
    limit: int | None = None              # per category; None = all
    randomize: bool = False
    seed: int = DEFAULT_SEED
    overwrite: bool = False
    clean: bool = False


@dataclass
class ExportResult:
    """Outcome of one export run."""

    exported: dict[str, int] = field(default_factory=dict)
    skipped_existing: int = 0
    cleaned_categories: list[str] = field(default_factory=list)

    @property
    def total(self) -> int:
        """Total images written."""
        return sum(self.exported.values())


def export_library(
    source: Path = DEFAULT_SOURCE,
    dest: Path = DEFAULT_DEST,
    rules: ExportRules = ExportRules(),
) -> ExportResult:
    """Build the runtime image folder from the master library.

    Args:
        source: Master library root (assets/simulation_dataset).
        dest: Runtime folder the simulator reads
            (simulation/camera/images).
        rules: Selection, ordering, and overwrite behaviour.

    Returns:
        Per-category export counts.

    Raises:
        FileNotFoundError: If the master library does not exist.
        ValueError: If a requested category is not in the library.
    """
    if not source.is_dir():
        raise FileNotFoundError(
            f"master image library not found: {source} — see "
            "assets/simulation_dataset/README.md"
        )
    available = sorted(
        d.name for d in source.iterdir()
        if d.is_dir() and not d.name.startswith((".", "_"))
    )
    selected = list(rules.categories) if rules.categories else available
    missing = sorted(set(selected) - set(available))
    if missing:
        raise ValueError(
            f"categories not in the master library: {missing} "
            f"(available: {available})"
        )

    rng = random.Random(rules.seed)
    result = ExportResult()
    for category in selected:
        candidates = _collect(source / category, rules.subcategories)
        if rules.limit is not None and len(candidates) > rules.limit:
            if rules.randomize:
                candidates = sorted(rng.sample(candidates, rules.limit))
            else:
                candidates = candidates[: rules.limit]

        target = dest / category
        if rules.clean and target.is_dir():
            shutil.rmtree(target)
            result.cleaned_categories.append(category)
        target.mkdir(parents=True, exist_ok=True)

        written = 0
        for runtime_name, path in candidates:
            out = target / runtime_name
            if out.exists() and not rules.overwrite:
                result.skipped_existing += 1
                continue
            shutil.copy2(path, out)
            written += 1
        result.exported[category] = written
        log.info("category %-18s %3d exported, %d candidate(s)",
                 category, written, len(candidates))
    return result


def _collect(
    category_dir: Path, subcategories: tuple[str, ...]
) -> list[tuple[str, Path]]:
    """List (runtime_name, source_path) pairs for one category, sorted.

    Files directly in the category root keep their names; files in a
    scene sub-folder are prefixed '<subcategory>__' so flattening can
    never collide silently.
    """
    pairs: list[tuple[str, Path]] = []
    for item in sorted(category_dir.iterdir()):
        if item.is_file() and item.suffix.lower() in IMAGE_EXTENSIONS:
            if not subcategories:
                pairs.append((item.name, item))
        elif item.is_dir():
            if subcategories and item.name not in subcategories:
                continue
            for image in sorted(item.iterdir()):
                if image.is_file() and image.suffix.lower() in IMAGE_EXTENSIONS:
                    pairs.append((f"{item.name}__{image.name}", image))
    return sorted(pairs)


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--dest", type=Path, default=DEFAULT_DEST)
    parser.add_argument("--categories", nargs="*", default=[])
    parser.add_argument("--subcategories", nargs="*", default=[])
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--random", action="store_true", dest="randomize")
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--clean", action="store_true")
    args = parser.parse_args(argv)

    result = export_library(
        source=args.source,
        dest=args.dest,
        rules=ExportRules(
            categories=tuple(args.categories),
            subcategories=tuple(args.subcategories),
            limit=args.limit,
            randomize=args.randomize,
            seed=args.seed,
            overwrite=args.overwrite,
            clean=args.clean,
        ),
    )
    log.info("export complete: %d image(s) across %d categor(ies); "
             "%d skipped as existing%s",
             result.total, len(result.exported), result.skipped_existing,
             f"; cleaned {result.cleaned_categories}"
             if result.cleaned_categories else "")
    return 0


if __name__ == "__main__":
    sys.exit(main())
