"""Reproducible, leakage-free train/val/test splitting.

Assignments are deterministic and scene-aware. The raw sources
contain multiple export variants of the same original photograph —
Roboflow-style pipelines emit every augmented/recompressed copy as
`<original-stem>_jpg.rf.<32-hex-digest>.jpg`, so the variants have
different bytes (md5 deduplication in the merge step cannot see them)
but show the exact same scene. Splitting per image scattered such
twins across train, val, and test and inflated every evaluation
metric.

The fix: images are first grouped by scene — the merged file name
with the Roboflow export suffix stripped — and every scene is
assigned to exactly one split. Scenes are stratified by class
signature (which classes their images contain, or 'negative'),
shuffled with a fixed seed, and dealt whole to train, then val, then
test until each split's image quota is filled. The same merged
dataset, seed, and ratios always produce byte-identical splits, and
the class balance stays similar across splits.

The result is written to merged/splits.json; the build step consumes
it to assemble datasets/processed/.
"""
import json
import random
import re
import sys
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from ai.object_detection.config import load_dataset_config
from ai.object_detection.data_tools.labels import read_label_file
from ai.object_detection.paths import MERGED_DATA_DIR, REPORTS_DIR
from ai.shared.utils.logger import get_logger

log = get_logger("data_tools.split")

SPLIT_NAMES = ("train", "val", "test")
DEFAULT_RATIOS = (0.7, 0.2, 0.1)
DEFAULT_SEED = 42

# Roboflow export suffix: every augmented/recompressed variant of one
# original is named <original-stem>.rf.<md5-of-the-variant>.<ext>.
_ROBOFLOW_SUFFIX = re.compile(r"\.rf\.[0-9a-f]{32}$")


@dataclass
class SplitResult:
    """Outcome of one split assignment."""

    seed: int
    ratios: tuple[float, float, float]
    created_at: str
    assignments: dict[str, str] = field(default_factory=dict)
    signature_counts: dict[str, dict[str, int]] = field(default_factory=dict)
    scenes_total: int = 0
    multi_image_scenes: int = 0
    images_in_multi_image_scenes: int = 0
    largest_scene: int = 0

    def split_counts(self) -> dict[str, int]:
        """Images per split."""
        counts = {name: 0 for name in SPLIT_NAMES}
        for split in self.assignments.values():
            counts[split] += 1
        return counts


def scene_key(file_name: str) -> str:
    """Identify the scene a merged image belongs to.

    Export variants of the same original photograph share their file
    name up to the Roboflow `.rf.<hex>` suffix; stripping it (plus the
    extension) collapses them into one scene. Names without the suffix
    are their own scene, so unaugmented sources keep per-image
    behavior.

    Args:
        file_name: Merged image file name, e.g.
            'figshare_fire_smoke__fire-42-_jpg.rf.<32 hex chars>.jpg'.

    Returns:
        The scene identifier, e.g. 'figshare_fire_smoke__fire-42-_jpg'.
    """
    return _ROBOFLOW_SUFFIX.sub("", Path(file_name).stem)


def class_signature(class_ids: set[int], names: list[str]) -> str:
    """Describe which classes an image contains, e.g. 'fire+smoke'.

    Args:
        class_ids: Unified class ids present in the image's label file.
        names: Unified class names, index-aligned.

    Returns:
        '+'-joined sorted class names, or 'negative' for no classes.
    """
    if not class_ids:
        return "negative"
    return "+".join(names[i] for i in sorted(class_ids))


def assign_splits(
    merged_dir: Path = MERGED_DATA_DIR,
    ratios: tuple[float, float, float] = DEFAULT_RATIOS,
    seed: int = DEFAULT_SEED,
) -> SplitResult:
    """Deterministically assign every merged image to a split.

    Assignment operates on whole scenes, never on single images, so
    export variants of one photograph can never straddle two splits.

    Args:
        merged_dir: Merged dataset (images/ + labels/).
        ratios: train/val/test fractions; must sum to 1.
        seed: RNG seed; identical inputs and seed give identical splits.

    Returns:
        The assignment, also written to merged/splits.json.

    Raises:
        ValueError: If ratios are invalid or the merged dataset is empty.
    """
    if len(ratios) != 3 or abs(sum(ratios) - 1.0) > 1e-9 or min(ratios) < 0:
        raise ValueError(f"ratios must be 3 non-negative values summing to 1, "
                         f"got {ratios}")
    images_dir = merged_dir / "images"
    labels_dir = merged_dir / "labels"
    if not images_dir.is_dir():
        raise ValueError(f"merged dataset not found at {merged_dir} — run "
                         "the merge step first")
    names = load_dataset_config().names

    signatures: dict[str, str] = {}
    scenes: dict[str, list[str]] = {}
    for image in sorted(images_dir.iterdir()):
        if not image.is_file():
            continue
        label = labels_dir / f"{image.stem}.txt"
        ids = (
            {a.class_id for a in read_label_file(label)}
            if label.is_file()
            else set()
        )
        signatures[image.name] = class_signature(ids, names)
        scenes.setdefault(scene_key(image.name), []).append(image.name)
    if not scenes:
        raise ValueError(f"no images found under {images_dir}")

    result = SplitResult(
        seed=seed,
        ratios=tuple(ratios),
        created_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        scenes_total=len(scenes),
        multi_image_scenes=sum(1 for m in scenes.values() if len(m) > 1),
        images_in_multi_image_scenes=sum(
            len(m) for m in scenes.values() if len(m) > 1
        ),
        largest_scene=max(len(m) for m in scenes.values()),
    )

    # Stratify whole scenes by their dominant class signature.
    groups: dict[str, list[list[str]]] = {}
    for key in sorted(scenes):
        members = scenes[key]
        counts = Counter(signatures[name] for name in members)
        top = max(counts.values())
        signature = min(s for s, c in counts.items() if c == top)
        groups.setdefault(signature, []).append(members)

    rng = random.Random(seed)
    for signature in sorted(groups):
        scene_list = groups[signature]
        rng.shuffle(scene_list)
        n = sum(len(members) for members in scene_list)
        n_train = round(n * ratios[0])
        n_val = round(n * ratios[1])
        # Tiny groups go entirely to train rather than starving it.
        if n_train == 0:
            n_train, n_val = n, 0
        counts = {split: 0 for split in SPLIT_NAMES}
        for members in scene_list:
            if counts["train"] < n_train:
                split = "train"
            elif counts["val"] < n_val:
                split = "val"
            else:
                split = "test"
            counts[split] += len(members)
            for name in members:
                result.assignments[name] = split
        result.signature_counts[signature] = counts

    (merged_dir / "splits.json").write_text(
        json.dumps(
            {
                "seed": result.seed,
                "ratios": list(result.ratios),
                "created_at": result.created_at,
                "method": "scene",
                "scenes": {
                    "total": result.scenes_total,
                    "multi_image": result.multi_image_scenes,
                    "images_in_multi_image": (
                        result.images_in_multi_image_scenes
                    ),
                    "largest": result.largest_scene,
                },
                "assignments": result.assignments,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    return result


def load_splits(merged_dir: Path = MERGED_DATA_DIR) -> dict[str, str]:
    """Read a previously written splits.json.

    Args:
        merged_dir: Merged dataset directory.

    Returns:
        Image file name -> split name.

    Raises:
        FileNotFoundError: If splits.json does not exist yet.
    """
    path = merged_dir / "splits.json"
    if not path.is_file():
        raise FileNotFoundError(f"{path} not found — run the split step first")
    return json.loads(path.read_text(encoding="utf-8"))["assignments"]


def write_split_report(result: SplitResult, path: Path) -> Path:
    """Render the split assignment as Markdown.

    Args:
        result: Split statistics to render.
        path: Destination file; parent directories are created.

    Returns:
        The written path.
    """
    counts = result.split_counts()
    total = sum(counts.values())
    lines = [
        "# Dataset Split Report",
        "",
        f"- **Created:** {result.created_at}",
        f"- **Seed:** {result.seed} (deterministic — identical inputs"
        " always reproduce this split)",
        f"- **Ratios:** train {result.ratios[0]:.0%} / val"
        f" {result.ratios[1]:.0%} / test {result.ratios[2]:.0%}",
        f"- **Total images:** {total}",
        "",
        "## Images per split",
        "",
        "| Split | Images | Share |",
        "|---|---|---|",
    ]
    for split in SPLIT_NAMES:
        share = counts[split] / total if total else 0.0
        lines.append(f"| {split} | {counts[split]} | {share:.1%} |")
    lines += [
        "",
        "## Leakage prevention (scene-aware assignment)",
        "",
        "Export variants of the same original photograph (Roboflow",
        "`.rf.<hex>` copies — augmented or recompressed) are grouped",
        "into one scene, and every scene is assigned to exactly one",
        "split, so no photograph can appear in both train and val/test.",
        "",
        f"- Scenes: {result.scenes_total} "
        f"({result.multi_image_scenes} with more than one image,"
        f" covering {result.images_in_multi_image_scenes} images)",
        f"- Largest scene: {result.largest_scene} images",
        "",
        "## Stratification by class signature",
        "",
        "Scenes are grouped by the dominant set of classes their",
        "images contain and each group is split independently, so every",
        "split sees a similar class mixture.",
        "",
        "| Signature | Train | Val | Test |",
        "|---|---|---|---|",
    ]
    for signature in sorted(result.signature_counts):
        c = result.signature_counts[signature]
        lines.append(
            f"| {signature} | {c['train']} | {c['val']} | {c['test']} |"
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def main(argv: list[str] | None = None) -> int:
    """CLI entry point: assign splits and write the split report."""
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument(
        "--ratios", type=float, nargs=3, default=list(DEFAULT_RATIOS),
        metavar=("TRAIN", "VAL", "TEST"),
    )
    args = parser.parse_args(argv)

    result = assign_splits(ratios=tuple(args.ratios), seed=args.seed)
    report = write_split_report(result, REPORTS_DIR / "split_report.md")
    log.info("split %d images: %s; report: %s",
             len(result.assignments), result.split_counts(), report)
    return 0


if __name__ == "__main__":
    sys.exit(main())
