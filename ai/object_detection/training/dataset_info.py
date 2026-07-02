"""Inspect and summarize the datasets under ai/object_detection/datasets/.

Entry point:
    python -m ai.object_detection.training.dataset_info

Prints which raw sources are present, the merged dataset size, and the
per-split / per-class breakdown of the processed dataset, so dataset
problems are caught before training starts. Exits with status 1 when
the processed dataset has not been built yet.
"""
import sys

from ai.object_detection.config import load_dataset_config
from ai.object_detection.data_tools.quality import compute_stats
from ai.object_detection.data_tools.sources import load_sources
from ai.object_detection.paths import (
    MERGED_DATA_DIR,
    PROCESSED_DATA_DIR,
    RAW_DATA_DIR,
)
from ai.shared.utils.logger import get_logger

logger = get_logger("training.dataset_info")


def main() -> int:
    """Print a summary of the available datasets.

    Returns:
        0 when the processed dataset exists, 1 when it must be built
        first (raw/merged status is still printed either way).
    """
    cfg = load_dataset_config()
    logger.info("unified classes (nc=%d): %s", cfg.nc, ", ".join(
        f"{i}={n}" for i, n in enumerate(cfg.names)))

    for spec in load_sources():
        root = RAW_DATA_DIR / spec.root
        if not spec.enabled:
            state = "disabled"
        elif root.is_dir() and any(root.iterdir()):
            state = "present"
        else:
            state = "MISSING (see docs/download_instructions.md)"
        logger.info("raw source %-22s %s", spec.name, state)

    merged_images = MERGED_DATA_DIR / "images"
    if merged_images.is_dir():
        count = sum(1 for p in merged_images.iterdir() if p.is_file())
        logger.info("merged dataset: %d images at %s", count, MERGED_DATA_DIR)
    else:
        logger.info("merged dataset: not created yet")

    try:
        stats = compute_stats(PROCESSED_DATA_DIR, cfg.names)
    except FileNotFoundError:
        logger.warning(
            "processed dataset not built — run "
            "'python -m ai.object_detection.data_tools.pipeline'"
        )
        return 1

    logger.info("processed dataset: %d images, %d annotations, %d negatives",
                stats.images_total, stats.boxes_total, stats.negatives_total)
    for split_name, split in stats.splits.items():
        per_class = ", ".join(
            f"{name}={split.boxes_per_class[name]}" for name in stats.names
        )
        logger.info("  %-5s %5d images  (%s)", split_name, split.images,
                    per_class)
    ratio = stats.balance_ratio()
    logger.info("images-per-class balance ratio: %s",
                "n/a" if ratio == float("inf") else f"{ratio:.2f}x")
    return 0


if __name__ == "__main__":
    sys.exit(main())
