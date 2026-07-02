"""Dataset validation: every integrity check plus JSON/Markdown reports.

Validates a YOLO-layout dataset root (<root>/images[/<split>] and
<root>/labels[/<split>]) and reports:

    errors    corrupted images · unsupported formats · malformed labels
              missing labels (orphan images) · orphan labels
              invalid class ids · out-of-bounds boxes
              duplicated annotations
    warnings  empty labels (valid negatives) · duplicated images

Run directly to validate the merged or processed dataset:

    python -m ai.object_detection.data_tools.validator --root processed
"""
import argparse
import json
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from ai.object_detection.config import load_dataset_config
from ai.object_detection.data_tools.image_utils import (
    SUPPORTED_EXTENSIONS,
    ImageError,
    decode_check,
    file_hash,
    probe_image,
)
from ai.object_detection.data_tools.labels import (
    LabelError,
    annotation_issues,
    count_duplicate_annotations,
    read_label_file,
)
from ai.object_detection.paths import (
    MERGED_DATA_DIR,
    PROCESSED_DATA_DIR,
    REPORTS_DIR,
)
from ai.shared.utils.logger import get_logger

log = get_logger("data_tools.validator")

ERROR_CATEGORIES = (
    "corrupted_images",
    "unsupported_formats",
    "malformed_labels",
    "missing_labels",
    "orphan_labels",
    "invalid_class_ids",
    "out_of_bounds_boxes",
    "duplicated_annotations",
)
WARNING_CATEGORIES = ("empty_labels", "duplicated_images")

# Cap per-category examples in the Markdown report (JSON keeps all).
_MD_EXAMPLE_CAP = 25


@dataclass
class ValidationReport:
    """Outcome of validating one dataset root."""

    name: str
    root: str
    nc: int
    names: list[str]
    deep_checked: bool = False
    checked_at: str = ""
    images_total: int = 0
    labels_total: int = 0
    annotations_total: int = 0
    negatives_total: int = 0
    split_image_counts: dict[str, int] = field(default_factory=dict)
    class_counts: dict[str, int] = field(default_factory=dict)
    issues: dict[str, list[str]] = field(default_factory=dict)

    def issue_count(self, categories: tuple[str, ...]) -> int:
        """Total number of recorded issues across the given categories."""
        return sum(len(self.issues.get(c, [])) for c in categories)

    @property
    def errors_total(self) -> int:
        """Number of error-severity findings."""
        return self.issue_count(ERROR_CATEGORIES)

    @property
    def warnings_total(self) -> int:
        """Number of warning-severity findings."""
        return self.issue_count(WARNING_CATEGORIES)

    @property
    def is_clean(self) -> bool:
        """True when the dataset has no error-severity findings."""
        return self.errors_total == 0

    def to_dict(self) -> dict:
        """JSON-serializable representation."""
        return {
            "name": self.name,
            "root": self.root,
            "checked_at": self.checked_at,
            "deep_checked": self.deep_checked,
            "nc": self.nc,
            "names": self.names,
            "totals": {
                "images": self.images_total,
                "labels": self.labels_total,
                "annotations": self.annotations_total,
                "negatives": self.negatives_total,
                "errors": self.errors_total,
                "warnings": self.warnings_total,
            },
            "split_image_counts": self.split_image_counts,
            "class_counts": self.class_counts,
            "issues": {k: sorted(v) for k, v in self.issues.items()},
            "is_clean": self.is_clean,
        }


def validate_dataset(
    root: Path,
    name: str | None = None,
    deep: bool = False,
) -> ValidationReport:
    """Run every integrity check against a YOLO-layout dataset root.

    Args:
        root: Directory containing images/ and labels/, either flat or
            with per-split subdirectories.
        name: Report label; defaults to the root directory name.
        deep: Also fully decode every image with cv2 when available
            (slower, catches corruption past the header).

    Returns:
        The populated report.

    Raises:
        FileNotFoundError: If root/images does not exist.
    """
    images_root = root / "images"
    labels_root = root / "labels"
    if not images_root.is_dir():
        raise FileNotFoundError(
            f"not a YOLO dataset root (no images/ directory): {root}"
        )
    cfg = load_dataset_config()
    report = ValidationReport(
        name=name or root.name,
        root=str(root),
        nc=cfg.nc,
        names=list(cfg.names),
        deep_checked=deep,
        checked_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        issues={c: [] for c in ERROR_CATEGORIES + WARNING_CATEGORIES},
        class_counts={n: 0 for n in cfg.names},
    )

    split_dirs = sorted(d for d in images_root.iterdir() if d.is_dir())
    splits = [(d.name, d, labels_root / d.name) for d in split_dirs]
    if not splits:
        splits = [("", images_root, labels_root)]

    hashes: dict[str, str] = {}
    for split_name, images_dir, labels_dir in splits:
        expected_labels = set()
        image_count = 0
        for item in sorted(images_dir.iterdir()):
            if not item.is_file():
                continue
            rel = f"{split_name}/{item.name}" if split_name else item.name
            if item.suffix.lower() not in SUPPORTED_EXTENSIONS:
                report.issues["unsupported_formats"].append(rel)
                continue
            image_count += 1
            _check_image(item, rel, deep, hashes, report)
            expected_labels.add(item.stem)
            _check_label(labels_dir / f"{item.stem}.txt", rel, report)
        report.split_image_counts[split_name or "(flat)"] = image_count
        report.images_total += image_count
        if labels_dir.is_dir():
            for label in sorted(labels_dir.glob("*.txt")):
                if label.stem not in expected_labels:
                    rel = (
                        f"{split_name}/{label.name}" if split_name else label.name
                    )
                    report.issues["orphan_labels"].append(rel)
    return report


def _check_image(
    path: Path,
    rel: str,
    deep: bool,
    hashes: dict[str, str],
    report: ValidationReport,
) -> None:
    try:
        probe_image(path)
    except ImageError as exc:
        report.issues["corrupted_images"].append(f"{rel}: {exc}")
        return
    if deep and not decode_check(path):
        report.issues["corrupted_images"].append(f"{rel}: failed full decode")
        return
    digest = file_hash(path)
    if digest in hashes:
        report.issues["duplicated_images"].append(
            f"{rel}: identical to {hashes[digest]}"
        )
    else:
        hashes[digest] = rel


def _check_label(label: Path, image_rel: str, report: ValidationReport) -> None:
    if not label.is_file():
        report.issues["missing_labels"].append(image_rel)
        return
    report.labels_total += 1
    try:
        annotations = read_label_file(label)
    except LabelError as exc:
        report.issues["malformed_labels"].append(str(exc))
        return
    if not annotations:
        report.negatives_total += 1
        report.issues["empty_labels"].append(image_rel)
        return
    duplicates = count_duplicate_annotations(annotations)
    if duplicates:
        report.issues["duplicated_annotations"].append(
            f"{label.name}: {duplicates} duplicated line(s)"
        )
    for ann in annotations:
        report.annotations_total += 1
        if 0 <= ann.class_id < report.nc:
            report.class_counts[report.names[ann.class_id]] += 1
        for issue in annotation_issues(ann, report.nc):
            category = (
                "invalid_class_ids"
                if "class id" in issue
                else "out_of_bounds_boxes"
            )
            report.issues[category].append(f"{label.name}: {issue}")


def write_report_json(report: ValidationReport, path: Path) -> Path:
    """Write the full report as JSON.

    Args:
        report: Report to serialize.
        path: Destination file; parent directories are created.

    Returns:
        The written path.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(report.to_dict(), indent=2) + "\n", encoding="utf-8"
    )
    return path


def write_report_md(report: ValidationReport, path: Path) -> Path:
    """Write the report as human-readable Markdown.

    Args:
        report: Report to render.
        path: Destination file; parent directories are created.

    Returns:
        The written path.
    """
    verdict = "CLEAN" if report.is_clean else "ISSUES FOUND"
    lines = [
        f"# Dataset Validation Report — {report.name}",
        "",
        f"- **Root:** `{report.root}`",
        f"- **Checked:** {report.checked_at}",
        f"- **Deep decode check:** {'yes' if report.deep_checked else 'no (header probe only)'}",
        f"- **Verdict:** **{verdict}** — {report.errors_total} error(s), "
        f"{report.warnings_total} warning(s)",
        "",
        "## Totals",
        "",
        "| Metric | Value |",
        "|---|---|",
        f"| Images | {report.images_total} |",
        f"| Label files | {report.labels_total} |",
        f"| Annotations | {report.annotations_total} |",
        f"| Negative samples (empty labels) | {report.negatives_total} |",
    ]
    for split, count in report.split_image_counts.items():
        lines.append(f"| Images in `{split}` | {count} |")
    lines += ["", "## Annotations per class", "", "| Class | Boxes |", "|---|---|"]
    lines += [f"| {n} | {c} |" for n, c in report.class_counts.items()]
    lines += ["", "## Findings", ""]
    for category in ERROR_CATEGORIES + WARNING_CATEGORIES:
        found = report.issues.get(category, [])
        severity = "error" if category in ERROR_CATEGORIES else "warning"
        lines.append(f"### {category} ({severity}) — {len(found)}")
        lines.append("")
        for example in found[:_MD_EXAMPLE_CAP]:
            lines.append(f"- `{example}`")
        if len(found) > _MD_EXAMPLE_CAP:
            lines.append(f"- … and {len(found) - _MD_EXAMPLE_CAP} more (see JSON)")
        if not found:
            lines.append("- none")
        lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


_KNOWN_ROOTS = {"processed": PROCESSED_DATA_DIR, "merged": MERGED_DATA_DIR}


def main(argv: list[str] | None = None) -> int:
    """CLI entry point; validates a dataset and writes both reports."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        default="processed",
        help="'processed', 'merged', or a path to a YOLO dataset root",
    )
    parser.add_argument(
        "--deep",
        action="store_true",
        help="fully decode every image (requires cv2; slower)",
    )
    args = parser.parse_args(argv)
    root = _KNOWN_ROOTS.get(args.root, Path(args.root))

    report = validate_dataset(root, deep=args.deep)
    json_path = write_report_json(report, REPORTS_DIR / "dataset_report.json")
    md_path = write_report_md(report, REPORTS_DIR / "dataset_report.md")
    log.info("validated %s: %d images, %d errors, %d warnings",
             report.root, report.images_total, report.errors_total,
             report.warnings_total)
    log.info("reports written: %s, %s", json_path, md_path)
    return 0 if report.is_clean else 1


if __name__ == "__main__":
    sys.exit(main())
