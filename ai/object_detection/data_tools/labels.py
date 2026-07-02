"""YOLO label file parsing, validation, and class remapping.

A YOLO label file holds one annotation per line:

    <class_id> <center_x> <center_y> <width> <height>

with all four coordinates normalized to [0, 1]. An empty file is a
valid negative sample (an image with no objects).
"""
from dataclasses import dataclass
from pathlib import Path

# Real-world datasets routinely carry boxes that overflow the image
# edge by a rounding error; anything within this tolerance is fine.
BBOX_TOLERANCE = 1e-3


class LabelError(ValueError):
    """A label line is malformed and cannot be parsed."""


@dataclass(frozen=True)
class BoxAnnotation:
    """One normalized YOLO bounding box annotation."""

    class_id: int
    center_x: float
    center_y: float
    width: float
    height: float

    def as_line(self) -> str:
        """Render the annotation back to a YOLO label line."""
        return (
            f"{self.class_id} {self.center_x:.6f} {self.center_y:.6f} "
            f"{self.width:.6f} {self.height:.6f}"
        )


def parse_label_line(line: str) -> BoxAnnotation:
    """Parse one YOLO label line.

    Args:
        line: A non-empty label file line.

    Returns:
        The parsed annotation.

    Raises:
        LabelError: If the line does not have exactly five numeric
            tokens with an integer class id.
    """
    tokens = line.split()
    if len(tokens) != 5:
        raise LabelError(f"expected 5 tokens, got {len(tokens)}: '{line.strip()}'")
    try:
        class_id = int(tokens[0])
        values = [float(t) for t in tokens[1:]]
    except ValueError as exc:
        raise LabelError(f"non-numeric token in line: '{line.strip()}'") from exc
    return BoxAnnotation(class_id, *values)


def read_label_file(path: Path) -> list[BoxAnnotation]:
    """Read and parse a YOLO label file.

    Args:
        path: Label file; may be empty (a valid negative sample).

    Returns:
        All parsed annotations, in file order.

    Raises:
        LabelError: On the first malformed line, naming the line number.
    """
    annotations = []
    with path.open("r", encoding="utf-8") as fh:
        for lineno, line in enumerate(fh, start=1):
            if not line.strip():
                continue
            try:
                annotations.append(parse_label_line(line))
            except LabelError as exc:
                raise LabelError(f"{path.name}:{lineno}: {exc}") from exc
    return annotations


def annotation_issues(ann: BoxAnnotation, nc: int) -> list[str]:
    """Validate one annotation against the class count and image bounds.

    Args:
        ann: The annotation to check.
        nc: Number of classes; valid ids are 0..nc-1.

    Returns:
        Human-readable issue strings; empty when the annotation is valid.
    """
    issues = []
    if not 0 <= ann.class_id < nc:
        issues.append(f"invalid class id {ann.class_id} (nc={nc})")
    if ann.width <= 0 or ann.height <= 0:
        issues.append(f"non-positive box size {ann.width}x{ann.height}")
    low, high = -BBOX_TOLERANCE, 1.0 + BBOX_TOLERANCE
    for edge in (
        ann.center_x - ann.width / 2,
        ann.center_x + ann.width / 2,
        ann.center_y - ann.height / 2,
        ann.center_y + ann.height / 2,
    ):
        if not low <= edge <= high:
            issues.append("bounding box outside image bounds")
            break
    return issues


def count_duplicate_annotations(annotations: list[BoxAnnotation]) -> int:
    """Count annotations that repeat an earlier identical annotation.

    Args:
        annotations: Annotations from one label file.

    Returns:
        How many entries are exact duplicates of a previous one.
    """
    return len(annotations) - len(set(annotations))


def remap_class_ids(
    annotations: list[BoxAnnotation],
    class_map: dict[int, int | None],
) -> list[BoxAnnotation]:
    """Translate source class ids to the unified class ids.

    Args:
        annotations: Source annotations.
        class_map: Source id -> unified id; a None value (or a missing
            source id) drops the annotation.

    Returns:
        Remapped annotations; annotations of unmapped classes are gone.
    """
    remapped = []
    for ann in annotations:
        target = class_map.get(ann.class_id)
        if target is None:
            continue
        remapped.append(
            BoxAnnotation(
                class_id=target,
                center_x=ann.center_x,
                center_y=ann.center_y,
                width=ann.width,
                height=ann.height,
            )
        )
    return remapped


def write_label_file(path: Path, annotations: list[BoxAnnotation]) -> None:
    """Write annotations as a YOLO label file (empty file for none).

    Args:
        path: Destination .txt file.
        annotations: Annotations to write, in order.
    """
    content = "\n".join(ann.as_line() for ann in annotations)
    path.write_text(content + "\n" if content else "", encoding="utf-8")
