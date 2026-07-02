"""COCO instance annotations -> YOLO label files.

Used to extract the 'person' class from COCO 2017. Pure json + math:
reads a COCO instances JSON, selects the wanted categories, converts
pixel [x, y, w, h] boxes to normalized YOLO format, and writes one
label file per image that contains at least one wanted annotation.
"""
import json
from dataclasses import dataclass, field
from pathlib import Path

from ai.object_detection.data_tools.labels import BoxAnnotation, write_label_file


@dataclass
class CocoConversionStats:
    """Outcome of one COCO -> YOLO conversion."""

    images_total: int = 0
    images_with_targets: int = 0
    boxes_written: int = 0
    boxes_skipped_crowd: int = 0
    boxes_skipped_degenerate: int = 0
    boxes_per_class: dict[int, int] = field(default_factory=dict)


def convert_coco(
    json_path: Path,
    out_labels_dir: Path,
    category_to_class: dict[str, int],
) -> CocoConversionStats:
    """Convert selected categories of a COCO instances file to YOLO labels.

    Args:
        json_path: A COCO instances JSON (e.g. instances_val2017.json).
        out_labels_dir: Directory that receives one <image-stem>.txt per
            image containing at least one wanted annotation; created if
            missing. Images without wanted annotations get no file.
        category_to_class: COCO category name -> unified class id
            (e.g. {"person": 2}).

    Returns:
        Conversion statistics.

    Raises:
        ValueError: If a requested category name is not in the file.
    """
    with json_path.open("r", encoding="utf-8") as fh:
        coco = json.load(fh)

    cat_id_to_class = {}
    names_found = set()
    for cat in coco.get("categories", []):
        if cat["name"] in category_to_class:
            cat_id_to_class[cat["id"]] = category_to_class[cat["name"]]
            names_found.add(cat["name"])
    missing = set(category_to_class) - names_found
    if missing:
        raise ValueError(
            f"{json_path.name}: categories not found: {sorted(missing)}"
        )

    images = {img["id"]: img for img in coco.get("images", [])}
    stats = CocoConversionStats(images_total=len(images))
    per_image: dict[int, list[BoxAnnotation]] = {}

    for ann in coco.get("annotations", []):
        class_id = cat_id_to_class.get(ann["category_id"])
        if class_id is None:
            continue
        if ann.get("iscrowd"):
            stats.boxes_skipped_crowd += 1
            continue
        image = images[ann["image_id"]]
        box = _to_yolo_box(ann["bbox"], image["width"], image["height"], class_id)
        if box is None:
            stats.boxes_skipped_degenerate += 1
            continue
        per_image.setdefault(ann["image_id"], []).append(box)
        stats.boxes_written += 1
        stats.boxes_per_class[class_id] = stats.boxes_per_class.get(class_id, 0) + 1

    out_labels_dir.mkdir(parents=True, exist_ok=True)
    for image_id, boxes in per_image.items():
        stem = Path(images[image_id]["file_name"]).stem
        write_label_file(out_labels_dir / f"{stem}.txt", boxes)
    stats.images_with_targets = len(per_image)
    return stats


def _to_yolo_box(
    bbox: list[float], img_w: int, img_h: int, class_id: int
) -> BoxAnnotation | None:
    """Convert a COCO pixel [x, y, w, h] box to a normalized YOLO box.

    Returns None for degenerate boxes (zero width/height after clamping).
    """
    x, y, w, h = bbox
    # Clamp to the image; COCO boxes occasionally overflow by a pixel.
    x1 = min(max(x, 0.0), img_w)
    y1 = min(max(y, 0.0), img_h)
    x2 = min(max(x + w, 0.0), img_w)
    y2 = min(max(y + h, 0.0), img_h)
    if x2 - x1 <= 0 or y2 - y1 <= 0:
        return None
    return BoxAnnotation(
        class_id=class_id,
        center_x=(x1 + x2) / 2 / img_w,
        center_y=(y1 + y2) / 2 / img_h,
        width=(x2 - x1) / img_w,
        height=(y2 - y1) / img_h,
    )
