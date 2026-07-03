"""Populate the simulated drone camera with real dataset images.

Reads the merged dataset (datasets/merged/), groups images by their
class signature (fire, smoke, fire+smoke, person, negative, ...), and
copies a deterministic sample of each group into the camera image
library used by simulation/camera/:

    simulation/camera/images/
    ├── safe/          (negatives)
    ├── fire/
    ├── smoke/
    ├── fire_smoke/
    ├── person/
    └── ...            (person-combination folders when available)

Run after the dataset pipeline:

    python -m ai.object_detection.data_tools.export_sim_images
        [--per-category N] [--seed N] [--dest DIR]
"""
import argparse
import random
import shutil
import sys
from pathlib import Path

from ai.object_detection.config import load_dataset_config
from ai.object_detection.data_tools.labels import read_label_file
from ai.object_detection.data_tools.split import class_signature
from ai.object_detection.paths import MERGED_DATA_DIR
from ai.shared.utils.logger import get_logger
from ai.shared.utils.paths import PROJECT_ROOT

log = get_logger("data_tools.export_sim_images")

# Dataset class signature → camera image category.
SIGNATURE_CATEGORIES = {
    "negative": "safe",
    "fire": "fire",
    "smoke": "smoke",
    "fire+smoke": "fire_smoke",
    "person": "person",
    "fire+person": "fire_person",
    "smoke+person": "smoke_person",
    "fire+smoke+person": "fire_smoke_person",
}

DEFAULT_DEST = PROJECT_ROOT / "simulation" / "camera" / "images"
DEFAULT_PER_CATEGORY = 12
DEFAULT_SEED = 42


def export_sim_images(
    merged_dir: Path = MERGED_DATA_DIR,
    dest: Path = DEFAULT_DEST,
    per_category: int = DEFAULT_PER_CATEGORY,
    seed: int = DEFAULT_SEED,
) -> dict[str, int]:
    """Copy a deterministic per-category sample into the camera library.

    Args:
        merged_dir: Merged dataset (images/ + labels/).
        dest: Camera image root; one sub-folder per category.
        per_category: Maximum images copied per category.
        seed: RNG seed for the deterministic sample.

    Returns:
        Category name -> number of images copied.

    Raises:
        FileNotFoundError: If the merged dataset does not exist yet.
    """
    images_dir = merged_dir / "images"
    labels_dir = merged_dir / "labels"
    if not images_dir.is_dir():
        raise FileNotFoundError(
            f"merged dataset not found at {merged_dir} — run "
            "'python -m ai.object_detection.data_tools.pipeline' first"
        )
    names = load_dataset_config().names

    groups: dict[str, list[Path]] = {}
    for image in sorted(images_dir.iterdir()):
        if not image.is_file():
            continue
        label = labels_dir / f"{image.stem}.txt"
        ids = (
            {a.class_id for a in read_label_file(label)}
            if label.is_file()
            else set()
        )
        signature = class_signature(ids, names)
        category = SIGNATURE_CATEGORIES.get(signature)
        if category:
            groups.setdefault(category, []).append(image)

    rng = random.Random(seed)
    copied: dict[str, int] = {}
    for category in sorted(groups):
        files = sorted(groups[category])
        sample = (
            files if len(files) <= per_category
            else rng.sample(files, per_category)
        )
        folder = dest / category
        folder.mkdir(parents=True, exist_ok=True)
        for source in sample:
            shutil.copy2(source, folder / source.name)
        copied[category] = len(sample)
        log.info("category %-18s %d image(s)", category, len(sample))
    return copied


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--per-category", type=int, default=DEFAULT_PER_CATEGORY)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--dest", type=Path, default=DEFAULT_DEST)
    args = parser.parse_args(argv)
    copied = export_sim_images(
        dest=args.dest, per_category=args.per_category, seed=args.seed
    )
    log.info("camera library ready at %s (%d categories, %d images)",
             args.dest, len(copied), sum(copied.values()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
