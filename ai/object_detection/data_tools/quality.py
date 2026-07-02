"""Dataset statistics and the final quality report.

Computes per-split, per-class statistics of the processed dataset and
renders quality_report.md, folding in the validation findings and the
deduplication results from the merge step when available.
"""
import json
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from ai.object_detection.config import load_dataset_config
from ai.object_detection.data_tools.labels import read_label_file
from ai.object_detection.data_tools.validator import ValidationReport
from ai.object_detection.paths import (
    MERGED_DATA_DIR,
    PROCESSED_DATA_DIR,
    REPORTS_DIR,
)
from ai.shared.utils.logger import get_logger

log = get_logger("data_tools.quality")

# Class-imbalance ratios above this trigger a recommendation.
_BALANCE_THRESHOLD = 3.0
# Validation/test splits smaller than this are statistically shaky.
_MIN_EVAL_SPLIT = 100


@dataclass
class SplitStats:
    """Statistics for one split of the processed dataset."""

    images: int = 0
    negatives: int = 0
    boxes_per_class: dict[str, int] = field(default_factory=dict)
    images_per_class: dict[str, int] = field(default_factory=dict)

    @property
    def boxes_total(self) -> int:
        """All annotations in the split."""
        return sum(self.boxes_per_class.values())


@dataclass
class DatasetStats:
    """Statistics for the whole processed dataset."""

    root: str
    names: list[str]
    computed_at: str
    splits: dict[str, SplitStats] = field(default_factory=dict)

    @property
    def images_total(self) -> int:
        """All images across splits."""
        return sum(s.images for s in self.splits.values())

    @property
    def boxes_total(self) -> int:
        """All annotations across splits."""
        return sum(s.boxes_total for s in self.splits.values())

    def totals_per_class(self, of: str = "boxes") -> dict[str, int]:
        """Aggregate per-class counts across splits.

        Args:
            of: 'boxes' for annotation counts, 'images' for the number
                of images containing the class.

        Returns:
            Class name -> count.
        """
        totals = {n: 0 for n in self.names}
        for split in self.splits.values():
            source = (
                split.boxes_per_class if of == "boxes"
                else split.images_per_class
            )
            for name, count in source.items():
                totals[name] += count
        return totals

    @property
    def negatives_total(self) -> int:
        """All negative (empty-label) images across splits."""
        return sum(s.negatives for s in self.splits.values())

    def balance_ratio(self) -> float:
        """Largest/smallest images-per-class ratio (inf if a class is absent)."""
        counts = [c for c in self.totals_per_class("images").values()]
        if not counts or min(counts) == 0:
            return float("inf")
        return max(counts) / min(counts)


def compute_stats(
    processed_dir: Path = PROCESSED_DATA_DIR,
    names: list[str] | None = None,
) -> DatasetStats:
    """Scan the processed dataset's labels and count everything.

    Args:
        processed_dir: Root of the built YOLO dataset.
        names: Unified class names; loaded from config when omitted.

    Returns:
        Per-split and per-class statistics.

    Raises:
        FileNotFoundError: If no images/ tree exists under the root.
    """
    names = names if names is not None else load_dataset_config().names
    images_root = processed_dir / "images"
    if not images_root.is_dir():
        raise FileNotFoundError(
            f"processed dataset not found at {processed_dir} — run "
            "'python -m ai.object_detection.data_tools.pipeline' first"
        )
    stats = DatasetStats(
        root=str(processed_dir),
        names=list(names),
        computed_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
    )
    for split_dir in sorted(d for d in images_root.iterdir() if d.is_dir()):
        split = SplitStats(
            boxes_per_class={n: 0 for n in names},
            images_per_class={n: 0 for n in names},
        )
        labels_dir = processed_dir / "labels" / split_dir.name
        for image in sorted(split_dir.iterdir()):
            if not image.is_file():
                continue
            split.images += 1
            label = labels_dir / f"{image.stem}.txt"
            annotations = read_label_file(label) if label.is_file() else []
            if not annotations:
                split.negatives += 1
                continue
            present = set()
            for ann in annotations:
                if 0 <= ann.class_id < len(names):
                    split.boxes_per_class[names[ann.class_id]] += 1
                    present.add(ann.class_id)
            for class_id in present:
                split.images_per_class[names[class_id]] += 1
        stats.splits[split_dir.name] = split
    return stats


def write_quality_report(
    stats: DatasetStats,
    path: Path,
    validation: ValidationReport | None = None,
    merge_summary: dict | None = None,
) -> Path:
    """Render the dataset quality report as Markdown.

    Args:
        stats: Processed dataset statistics.
        path: Destination file; parent directories are created.
        validation: Validation findings to fold in, when available.
        merge_summary: Parsed merged/provenance.json-adjacent summary
            (duplicate counts etc.) from the merge step, when available.

    Returns:
        The written path.
    """
    boxes = stats.totals_per_class("boxes")
    images = stats.totals_per_class("images")
    lines = [
        "# Dataset Quality Report",
        "",
        f"- **Dataset:** `{stats.root}`",
        f"- **Generated:** {stats.computed_at}",
        f"- **Total images:** {stats.images_total}",
        f"- **Total annotations:** {stats.boxes_total}",
        f"- **Negative samples:** {stats.negatives_total}",
        "",
        "## Images and annotations per class",
        "",
        "| Class | Images containing it | Annotations |",
        "|---|---|---|",
    ]
    lines += [
        f"| {name} | {images[name]} | {boxes[name]} |" for name in stats.names
    ]
    lines += ["", "## Per split", "", "| Split | Images | Negatives | "
              + " | ".join(stats.names) + " (boxes) |",
              "|---|---|---|" + "---|" * len(stats.names)]
    for split_name, split in stats.splits.items():
        per_class = " | ".join(
            str(split.boxes_per_class[n]) for n in stats.names
        )
        lines.append(
            f"| {split_name} | {split.images} | {split.negatives} "
            f"| {per_class} |"
        )

    ratio = stats.balance_ratio()
    ratio_text = "n/a (a class has no images)" if ratio == float("inf") \
        else f"{ratio:.2f}x"
    lines += ["", "## Dataset balance", "",
              f"- Largest/smallest images-per-class ratio: **{ratio_text}**"]

    if merge_summary:
        lines += [
            "",
            "## Deduplication and cleaning (from merge)",
            "",
            f"- Duplicate images skipped: {merge_summary.get('duplicates', 0)}",
            f"- Corrupted images excluded: {merge_summary.get('corrupted', 0)}",
            f"- Malformed label files excluded: {merge_summary.get('malformed', 0)}",
            f"- Boxes dropped (unmapped classes): "
            f"{merge_summary.get('unmapped', 0)}",
            f"- Boxes dropped (invalid geometry): "
            f"{merge_summary.get('invalid', 0)}",
        ]
    if validation:
        lines += [
            "",
            "## Validation findings",
            "",
            f"- Errors: **{validation.errors_total}** · Warnings: "
            f"**{validation.warnings_total}** (details in "
            "`dataset_report.md`)",
            f"- Broken images: "
            f"{len(validation.issues.get('corrupted_images', []))}",
            f"- Missing labels: "
            f"{len(validation.issues.get('missing_labels', []))}",
        ]

    lines += ["", "## Potential issues", ""]
    issues = _detect_issues(stats, validation)
    lines += [f"- {issue}" for issue in issues] or ["- none detected"]
    lines += ["", "## Recommendations", ""]
    lines += [f"- {rec}" for rec in _recommendations(stats, issues)]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def _detect_issues(
    stats: DatasetStats, validation: ValidationReport | None
) -> list[str]:
    issues = []
    images = stats.totals_per_class("images")
    for name, count in images.items():
        if count == 0:
            issues.append(f"class '{name}' has no images at all")
    ratio = stats.balance_ratio()
    if ratio != float("inf") and ratio > _BALANCE_THRESHOLD:
        smallest = min(images, key=images.get)
        largest = max(images, key=images.get)
        issues.append(
            f"class imbalance: '{largest}' has {ratio:.1f}x more images "
            f"than '{smallest}'"
        )
    for split_name in ("val", "test"):
        split = stats.splits.get(split_name)
        if split and 0 < split.images < _MIN_EVAL_SPLIT:
            issues.append(
                f"'{split_name}' split has only {split.images} images — "
                "metrics will be noisy"
            )
    if stats.images_total and stats.negatives_total / stats.images_total > 0.5:
        issues.append("more than half of all images are negatives")
    if validation and not validation.is_clean:
        issues.append(
            f"validation found {validation.errors_total} error(s) — "
            "see dataset_report.md"
        )
    return issues


def _recommendations(stats: DatasetStats, issues: list[str]) -> list[str]:
    recs = []
    images = stats.totals_per_class("images")
    smallest = min(images, key=images.get) if images else None
    if any("imbalance" in i or "no images" in i for i in issues):
        recs.append(
            f"add more '{smallest}' images (additional sources in "
            "docs/download_instructions.md) or enable class-weighted "
            "sampling during training"
        )
    if any("split has only" in i for i in issues):
        recs.append("re-split with a larger val/test share or add data "
                    "before trusting evaluation metrics")
    if not any("error" in i for i in issues):
        recs.append("dataset is structurally clean — proceed to Phase 8D "
                    "(first training run)")
    recs.append("review per-class sample images before training to catch "
                "annotation quality problems automation cannot see")
    return recs


def main(argv: list[str] | None = None) -> int:
    """CLI entry point: compute stats and write quality_report.md."""
    stats = compute_stats()
    merge_summary = load_merge_summary()
    report = write_quality_report(
        stats, REPORTS_DIR / "quality_report.md", merge_summary=merge_summary
    )
    log.info("quality report written: %s", report)
    return 0


def load_merge_summary(merged_dir: Path = MERGED_DATA_DIR) -> dict | None:
    """Summarize dedup counters from the last merge, if one has run.

    Args:
        merged_dir: Merged dataset directory holding merge_stats.json.

    Returns:
        Counter dict for write_quality_report, or None when no merge
        statistics exist.
    """
    path = merged_dir / "merge_stats.json"
    if not path.is_file():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    sources = data.get("sources", [])

    def total(key: str) -> int:
        return sum(s.get(key, 0) for s in sources)

    return {
        "duplicates": total("duplicates_skipped"),
        "corrupted": total("corrupted_skipped"),
        "malformed": total("malformed_skipped"),
        "unmapped": total("boxes_dropped_unmapped"),
        "invalid": total("boxes_dropped_invalid"),
    }


if __name__ == "__main__":
    sys.exit(main())
