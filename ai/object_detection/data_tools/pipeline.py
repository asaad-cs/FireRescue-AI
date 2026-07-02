"""End-to-end dataset pipeline: merge -> split -> build -> validate.

One command turns whatever raw sources have been downloaded into the
final validated YOLO dataset and regenerates every report:

    python -m ai.object_detection.data_tools.pipeline [--seed N]
        [--ratios TRAIN VAL TEST] [--deep]

Outputs:
    datasets/merged/                 unified deduplicated dataset
    datasets/processed/              final YOLO dataset + data.yaml
    datasets/reports/merge_report.md
    datasets/reports/split_report.md
    datasets/reports/dataset_report.json + dataset_report.md
    datasets/reports/quality_report.md

The pipeline never writes into datasets/raw/.
"""
import argparse
import sys

from ai.object_detection.data_tools.build import build_processed
from ai.object_detection.data_tools.merge import merge_sources, write_merge_report
from ai.object_detection.data_tools.quality import (
    compute_stats,
    load_merge_summary,
    write_quality_report,
)
from ai.object_detection.data_tools.split import (
    DEFAULT_RATIOS,
    DEFAULT_SEED,
    assign_splits,
    write_split_report,
)
from ai.object_detection.data_tools.validator import (
    validate_dataset,
    write_report_json,
    write_report_md,
)
from ai.object_detection.paths import PROCESSED_DATA_DIR, REPORTS_DIR
from ai.shared.utils.logger import get_logger

log = get_logger("data_tools.pipeline")


def run_pipeline(
    seed: int = DEFAULT_SEED,
    ratios: tuple[float, float, float] = DEFAULT_RATIOS,
    deep: bool = False,
) -> bool:
    """Run merge, split, build, validation, and all reports.

    Args:
        seed: Split RNG seed (deterministic splits).
        ratios: train/val/test fractions.
        deep: Fully decode every image during validation (needs cv2).

    Returns:
        True when the final dataset validated clean.
    """
    log.info("step 1/5: merging raw sources")
    merge_result = merge_sources()
    write_merge_report(merge_result, REPORTS_DIR / "merge_report.md")

    log.info("step 2/5: assigning train/val/test splits "
             "(seed=%d, ratios=%s)", seed, ratios)
    split_result = assign_splits(ratios=ratios, seed=seed)
    write_split_report(split_result, REPORTS_DIR / "split_report.md")

    log.info("step 3/5: building datasets/processed/")
    build_result = build_processed()

    log.info("step 4/5: validating the processed dataset")
    report = validate_dataset(PROCESSED_DATA_DIR, deep=deep)
    write_report_json(report, REPORTS_DIR / "dataset_report.json")
    write_report_md(report, REPORTS_DIR / "dataset_report.md")

    log.info("step 5/5: writing the quality report")
    stats = compute_stats()
    write_quality_report(
        stats,
        REPORTS_DIR / "quality_report.md",
        validation=report,
        merge_summary=load_merge_summary(),
    )

    log.info(
        "pipeline complete: %d images (%s), %d annotations, "
        "%d validation error(s), %d warning(s)",
        build_result.images_total, build_result.images_per_split,
        report.annotations_total, report.errors_total,
        report.warnings_total,
    )
    return report.is_clean


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument(
        "--ratios", type=float, nargs=3, default=list(DEFAULT_RATIOS),
        metavar=("TRAIN", "VAL", "TEST"),
    )
    parser.add_argument(
        "--deep", action="store_true",
        help="fully decode every image during validation (slower)",
    )
    args = parser.parse_args(argv)
    clean = run_pipeline(
        seed=args.seed, ratios=tuple(args.ratios), deep=args.deep
    )
    return 0 if clean else 1


if __name__ == "__main__":
    sys.exit(main())
