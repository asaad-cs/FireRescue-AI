"""Merge raw source datasets into one unified, standardized dataset.

Reads every enabled source from configs/sources.yaml, standardizes the
class ids to the unified scheme (0 fire · 1 smoke · 2 person), and
writes a flat deduplicated dataset:

    datasets/merged/images/<source>__<name>.<ext>
    datasets/merged/labels/<source>__<name>.txt
    datasets/merged/provenance.json

Guarantees:
    - raw/ is never written to; every image is copied, never moved
    - byte-identical images are merged once (md5 content hashing),
      including duplicates across different sources
    - every merged label uses unified class ids; boxes of unmapped
      classes are dropped and counted
    - corrupted images and malformed labels are excluded and counted
    - provenance.json records source, original path, and md5 for
      every merged file
"""
import json
import shutil
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from ai.object_detection.config import load_dataset_config
from ai.object_detection.data_tools.coco import convert_coco
from ai.object_detection.data_tools.image_utils import (
    ImageError,
    file_hash,
    probe_image,
)
from ai.object_detection.data_tools.labels import (
    LabelError,
    annotation_issues,
    read_label_file,
    remap_class_ids,
    write_label_file,
)
from ai.object_detection.data_tools.sources import (
    SourceSpec,
    discover_yolo_pairs,
    load_sources,
)
from ai.object_detection.paths import (
    MERGED_DATA_DIR,
    RAW_DATA_DIR,
    REPORTS_DIR,
)
from ai.shared.utils.logger import get_logger

log = get_logger("data_tools.merge")


@dataclass
class SourceMergeStats:
    """What happened to one source during the merge."""

    name: str
    images_found: int = 0
    images_merged: int = 0
    duplicates_skipped: int = 0
    corrupted_skipped: int = 0
    malformed_skipped: int = 0
    missing_label_skipped: int = 0
    negatives_merged: int = 0
    boxes_in: int = 0
    boxes_merged: int = 0
    boxes_dropped_unmapped: int = 0
    boxes_dropped_invalid: int = 0


@dataclass
class MergeResult:
    """Outcome of a full merge run."""

    merged_dir: str
    merged_at: str
    sources: list[SourceMergeStats] = field(default_factory=list)
    skipped_sources: list[str] = field(default_factory=list)
    class_counts: dict[str, int] = field(default_factory=dict)

    @property
    def images_total(self) -> int:
        """Number of images in the merged dataset."""
        return sum(s.images_merged for s in self.sources)

    @property
    def boxes_total(self) -> int:
        """Number of annotations in the merged dataset."""
        return sum(s.boxes_merged for s in self.sources)


def merge_sources(
    specs: list[SourceSpec] | None = None,
    raw_root: Path = RAW_DATA_DIR,
    merged_dir: Path = MERGED_DATA_DIR,
    keep_negatives: bool = True,
) -> MergeResult:
    """Standardize and merge every available enabled source.

    Args:
        specs: Sources to merge; defaults to configs/sources.yaml.
        raw_root: Directory holding the raw source datasets.
        merged_dir: Output directory; its images/ and labels/ subtrees
            are rebuilt from scratch on every run.
        keep_negatives: Keep images whose labels end up empty (useful
            background samples for detector training).

    Returns:
        Per-source statistics and totals.

    Raises:
        RuntimeError: If no enabled source directory exists at all.
    """
    cfg = load_dataset_config()
    specs = load_sources() if specs is None else specs

    images_out = merged_dir / "images"
    labels_out = merged_dir / "labels"
    for out in (images_out, labels_out):
        if out.exists():
            shutil.rmtree(out)
        out.mkdir(parents=True)

    result = MergeResult(
        merged_dir=str(merged_dir),
        merged_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        class_counts={n: 0 for n in cfg.names},
    )
    provenance: list[dict] = []
    hashes: dict[str, str] = {}
    used_names: set[str] = set()

    for spec in specs:
        if not spec.enabled:
            continue
        root = raw_root / spec.root
        if not root.is_dir():
            log.warning("source '%s' not found at %s — skipped (see "
                        "docs/download_instructions.md)", spec.name, root)
            result.skipped_sources.append(spec.name)
            continue
        log.info("merging source '%s' from %s", spec.name, root)
        pairs = _source_pairs(spec, root, merged_dir)
        if not pairs:
            log.warning("source '%s' has no images under %s — skipped",
                        spec.name, root)
            result.skipped_sources.append(spec.name)
            continue
        stats = SourceMergeStats(name=spec.name)
        for image, label in pairs:
            _merge_one(
                spec, image, label, cfg.nc, cfg.names, keep_negatives,
                images_out, labels_out, hashes, used_names, stats,
                provenance, result.class_counts,
            )
        result.sources.append(stats)
        log.info("source '%s': %d/%d images merged, %d boxes",
                 spec.name, stats.images_merged, stats.images_found,
                 stats.boxes_merged)

    tmp = merged_dir / "_coco_labels"
    if tmp.exists():
        shutil.rmtree(tmp)
    if not result.sources:
        raise RuntimeError(
            f"no enabled source found under {raw_root} — run "
            "'python -m ai.object_detection.data_tools.download' first"
        )

    (merged_dir / "provenance.json").write_text(
        json.dumps(
            {"merged_at": result.merged_at, "entries": provenance}, indent=2
        )
        + "\n",
        encoding="utf-8",
    )
    # Machine-readable counters for the quality report.
    (merged_dir / "merge_stats.json").write_text(
        json.dumps(
            {
                "merged_at": result.merged_at,
                "skipped_sources": result.skipped_sources,
                "class_counts": result.class_counts,
                "sources": [asdict(s) for s in result.sources],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return result


def _source_pairs(
    spec: SourceSpec, root: Path, merged_dir: Path
) -> list[tuple[Path, Path | None]]:
    """Return (image, label) pairs for a source, converting COCO first."""
    if spec.kind == "yolo":
        return discover_yolo_pairs(root)
    labels_dir = merged_dir / "_coco_labels" / spec.name
    stats = convert_coco(root / spec.annotations, labels_dir, spec.categories)
    log.info("source '%s': %d/%d COCO images have target annotations "
             "(%d crowd boxes skipped)", spec.name,
             stats.images_with_targets, stats.images_total,
             stats.boxes_skipped_crowd)
    images_dir = root / spec.images
    by_stem = {
        p.stem: p
        for p in sorted(images_dir.glob("*"))
        if p.is_file()
    }
    pairs = []
    for label in sorted(labels_dir.glob("*.txt")):
        image = by_stem.get(label.stem)
        if image is not None:
            pairs.append((image, label))
    return pairs


def _merge_one(
    spec: SourceSpec,
    image: Path,
    label: Path | None,
    nc: int,
    names: list[str],
    keep_negatives: bool,
    images_out: Path,
    labels_out: Path,
    hashes: dict[str, str],
    used_names: set[str],
    stats: SourceMergeStats,
    provenance: list[dict],
    class_counts: dict[str, int],
) -> None:
    stats.images_found += 1
    if label is None:
        stats.missing_label_skipped += 1
        return
    try:
        probe_image(image)
    except ImageError:
        stats.corrupted_skipped += 1
        return
    try:
        annotations = read_label_file(label)
    except LabelError:
        stats.malformed_skipped += 1
        return

    stats.boxes_in += len(annotations)
    # COCO labels are already unified; YOLO sources get remapped here.
    if spec.kind == "yolo":
        remapped = remap_class_ids(annotations, spec.class_map)
        stats.boxes_dropped_unmapped += len(annotations) - len(remapped)
    else:
        remapped = annotations
    kept = [a for a in remapped if not annotation_issues(a, nc)]
    stats.boxes_dropped_invalid += len(remapped) - len(kept)
    # Deduplicate identical annotations while preserving order.
    kept = list(dict.fromkeys(kept))
    if not kept and not keep_negatives:
        return

    digest = file_hash(image)
    if digest in hashes:
        stats.duplicates_skipped += 1
        return
    merged_name = f"{spec.name}__{image.stem}{image.suffix.lower()}"
    if merged_name in used_names:
        merged_name = (
            f"{spec.name}__{image.stem}-{digest[:8]}{image.suffix.lower()}"
        )
    used_names.add(merged_name)
    hashes[digest] = merged_name

    shutil.copy2(image, images_out / merged_name)
    write_label_file(labels_out / f"{Path(merged_name).stem}.txt", kept)
    provenance.append(
        {
            "file": merged_name,
            "source": spec.name,
            "original": str(image),
            "md5": digest,
        }
    )
    stats.images_merged += 1
    stats.boxes_merged += len(kept)
    if not kept:
        stats.negatives_merged += 1
    for ann in kept:
        class_counts[names[ann.class_id]] += 1


def write_merge_report(result: MergeResult, path: Path) -> Path:
    """Render the merge outcome as Markdown.

    Args:
        result: Merge statistics to render.
        path: Destination file; parent directories are created.

    Returns:
        The written path.
    """
    lines = [
        "# Dataset Merge Report",
        "",
        f"- **Merged:** {result.merged_at}",
        f"- **Output:** `{result.merged_dir}`",
        f"- **Images:** {result.images_total}",
        f"- **Annotations:** {result.boxes_total}",
        "",
        "## Class distribution (unified ids)",
        "",
        "| Class | Boxes |",
        "|---|---|",
    ]
    lines += [f"| {n} | {c} |" for n, c in result.class_counts.items()]
    lines += [
        "",
        "## Per-source results",
        "",
        "| Source | Found | Merged | Dup skipped | Corrupt | Malformed |"
        " No label | Negatives | Boxes in | Boxes kept | Unmapped dropped |"
        " Invalid dropped |",
        "|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for s in result.sources:
        lines.append(
            f"| {s.name} | {s.images_found} | {s.images_merged} "
            f"| {s.duplicates_skipped} | {s.corrupted_skipped} "
            f"| {s.malformed_skipped} | {s.missing_label_skipped} "
            f"| {s.negatives_merged} | {s.boxes_in} | {s.boxes_merged} "
            f"| {s.boxes_dropped_unmapped} | {s.boxes_dropped_invalid} |"
        )
    if result.skipped_sources:
        lines += [
            "",
            "## Skipped sources (not downloaded)",
            "",
        ]
        lines += [
            f"- `{name}` — see `docs/download_instructions.md`"
            for name in result.skipped_sources
        ]
    lines += [
        "",
        "## Standardization rules applied",
        "",
        "- Unified class ids: 0 fire · 1 smoke · 2 person"
        " (configs/dataset.yaml)",
        "- Per-source class id mappings come from configs/sources.yaml;"
        " boxes of unmapped classes are dropped and counted above",
        "- COCO pixel boxes were converted to normalized YOLO format;"
        " crowd regions (iscrowd=1) were excluded",
        "- Byte-identical images (md5) are merged once; later copies are"
        " recorded as duplicates",
        "- Exact duplicate annotation lines within a label file are"
        " collapsed to one",
        "- Merged files are renamed `<source>__<original-stem>.<ext>`;"
        " full provenance is in `merged/provenance.json`",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def main(argv: list[str] | None = None) -> int:
    """CLI entry point: merge all sources and write the merge report."""
    result = merge_sources()
    report = write_merge_report(result, REPORTS_DIR / "merge_report.md")
    log.info("merged %d images / %d boxes from %d source(s); report: %s",
             result.images_total, result.boxes_total, len(result.sources),
             report)
    return 0


if __name__ == "__main__":
    sys.exit(main())
