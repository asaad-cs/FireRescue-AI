"""Dataset engineering tools for the object detection module.

Everything needed to turn raw downloaded datasets into one clean,
validated, reproducible YOLO dataset under datasets/processed/:

    download.py     Fetch raw datasets (or print manual instructions)
    image_utils.py  Stdlib image probing (format, dimensions) + hashing
    labels.py       YOLO label parsing, validation, and class remapping
    coco.py         COCO JSON -> YOLO label conversion (person class)
    sources.py      Declarative source registry (configs/sources.yaml)
    validator.py    Full dataset validation + JSON/Markdown reports
    merge.py        Hash-deduplicating merge with provenance tracking
    split.py        Deterministic stratified train/val/test splitting
    build.py        Final YOLO dataset assembly + data.yaml generation
    quality.py      Dataset statistics and the quality report
    pipeline.py     End-to-end orchestrator (merge -> split -> build)

None of these modules import ultralytics or torch; the heaviest
optional dependency (cv2 for deep image decoding) is imported lazily.
"""
