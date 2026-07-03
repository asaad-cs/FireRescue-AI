# FireRescue AI — AI Workspace (Version 2)

The Version 2 workspace for all AI capabilities. It is fully
independent of the MVP: nothing in `ai/` is imported by the backend,
the simulation, or the frontend, and the frozen v1.0.0 code is never
modified from here.

## Architecture — Multiple AI Modules

The workspace is organized as independent AI modules that share common
infrastructure:

| Module | Status | Purpose |
|---|---|---|
| `object_detection/` | **Implemented** | Ultralytics YOLO transfer learning — detects `fire`, `smoke`, `person` |
| `fire_detection/` | Planned | Dedicated fire & smoke analysis |
| `mapping/` | Planned | SLAM / building mapping |
| `sensor_fusion/` | Planned | Fusing vision with environmental sensor channels |

Each module is self-contained (its own configs, datasets, models,
training code, and tests). Generic utilities live in `ai/shared/` and
must stay model-agnostic.

## Installation

The AI stack is separate from the backend dependencies:

```bash
pip install -r ai/requirements.txt
```

## Directory Structure

```
ai/
├── requirements.txt            AI-only dependencies (ultralytics, torch, ...)
├── shared/
│   └── utils/
│       ├── config.py           Generic YAML loading + ConfigError
│       ├── device.py           'auto'/'cpu'/'cuda' resolution, lazy torch import
│       ├── experiment.py       Run naming + checkpoint discovery (dir passed in)
│       ├── logger.py           Standalone logging under 'firerescue.ai'
│       ├── paths.py            AI_ROOT / PROJECT_ROOT / ensure_dir
│       └── seed.py             Deterministic seeding for reproducibility
├── object_detection/           ── IMPLEMENTED ──
│   ├── paths.py                Module paths (configs, datasets, models)
│   ├── config.py               Typed config schemas + loaders (YOLO-specific)
│   ├── configs/
│   │   ├── training.yaml       Session: seed, workers, AMP, early stopping, resume
│   │   ├── dataset.yaml        Splits, class names, nc, dataset root (relative)
│   │   ├── model.yaml          YOLO size, epochs, batch, device, thresholds, export
│   │   └── sources.yaml        Raw source registry + per-source class id mappings
│   ├── docs/
│   │   ├── dataset-manifest.md         Selected datasets, licenses, rationale
│   │   └── download_instructions.md    Manual steps for login-gated sources
│   ├── datasets/
│   │   ├── raw/                Original downloads, never modified
│   │   ├── merged/             Unified deduplicated dataset + provenance.json
│   │   ├── processed/          Final YOLO dataset: images/<split>, labels/<split>, data.yaml
│   │   ├── external/           Third-party datasets (never edited in place)
│   │   └── reports/            dataset/merge/split/quality reports (generated)
│   ├── data_tools/
│   │   ├── download.py         Fetch + checksum-verify raw sources
│   │   ├── image_utils.py      Stdlib image probing + content hashing
│   │   ├── labels.py           YOLO label parse/validate/remap
│   │   ├── coco.py             COCO JSON -> YOLO conversion (person)
│   │   ├── sources.py          sources.yaml loader + pair discovery
│   │   ├── validator.py        Full dataset validation + reports
│   │   ├── merge.py            Standardizing, deduplicating merge
│   │   ├── split.py            Deterministic stratified splits
│   │   ├── build.py            Final YOLO assembly + data.yaml
│   │   ├── quality.py          Statistics + quality report
│   │   └── pipeline.py         merge -> split -> build -> validate
│   ├── models/
│   │   ├── checkpoints/        One directory per training run
│   │   ├── exports/            Final serialized models ready for integration
│   │   └── predictions/        Annotated images from predict.py (generated)
│   ├── training/
│   │   ├── train.py            python -m ai.object_detection.training.train
│   │   ├── evaluate.py         python -m ai.object_detection.training.evaluate
│   │   ├── predict.py          python -m ai.object_detection.training.predict
│   │   └── dataset_info.py     Dataset summary (sources, splits, class balance)
│   └── tests/                  Unit tests (config, device, dataset tools, pipeline)
├── fire_detection/             ── PLANNED ──
│   ├── configs/  training/  models/
├── mapping/                    ── PLANNED ──
├── sensor_fusion/              ── PLANNED ──
└── notebooks/                  Exploratory analysis (never production code)
```

## Object Detection — Training

```bash
python -m ai.object_detection.training.train
```

What happens:

1. All three configs are loaded and validated eagerly — a bad value
   fails with a `ConfigError` naming the file and field before any
   heavy library loads.
2. All RNGs are seeded (`training.yaml: seed`).
3. The device is resolved (`model.yaml: device`, `auto` → CUDA if
   available, else CPU).
4. A run directory
   `ai/object_detection/models/checkpoints/<experiment>-<timestamp>/`
   is created with a resolved `data.yaml` (absolute dataset root).
5. The pretrained checkpoint `yolov8<size>.pt` is downloaded by
   Ultralytics on first use and fine-tuned on the configured dataset
   (transfer learning — no custom networks).

Training never starts on import — only when the module is executed
directly. It fails fast with a clear message if the dataset split
directories do not exist yet.

## Object Detection — Evaluation

```bash
python -m ai.object_detection.training.evaluate                       # newest best.pt, val split
python -m ai.object_detection.training.evaluate --split test          # test split
python -m ai.object_detection.training.evaluate --weights path/to.pt  # explicit checkpoint
```

Runs Ultralytics validation with the thresholds from `model.yaml` and
logs the headline metrics: **mAP50, mAP50-95, precision, recall**.

## Object Detection — Prediction

```bash
python -m ai.object_detection.training.predict --source path/to/image.jpg
python -m ai.object_detection.training.predict --source path/to/folder --conf 0.5
python -m ai.object_detection.training.predict --source img.jpg --save-dir out/
```

Accepts a single image (`.jpg .jpeg .png .bmp`) or a folder of images.
Uses the newest `best.pt` unless `--weights` is given; the confidence
threshold defaults to `model.yaml`. Annotated images are saved under
`ai/object_detection/models/predictions/predict-<timestamp>/`.
No webcam or video input.

## Model Exports

`ai/object_detection/models/exports/` holds finalized models in the
format configured in `model.yaml` (`export.format`, default ONNX).
Only exported models are candidates for backend integration.
Checkpoints in `models/checkpoints/` are training artifacts and
disposable.

## Expected Outputs

| Command | Output |
|---|---|
| `train` | `checkpoints/<run>/weights/best.pt` and `last.pt`, training curves, resolved `data.yaml`, `tb/` reserved for TensorBoard logs |
| `evaluate` | Metrics logged to stdout (mAP50, mAP50-95, precision, recall) |
| `predict` | Annotated images in `models/predictions/predict-<timestamp>/` |

## Directory Structure After Training

```
ai/object_detection/models/checkpoints/
└── firerescue-detector-20260702-140000/
    ├── data.yaml            Resolved dataset yaml used for this run
    ├── tb/                  TensorBoard log directory
    ├── weights/
    │   ├── best.pt          Best checkpoint by validation fitness
    │   └── last.pt          Most recent checkpoint (resume point)
    ├── results.csv          Per-epoch metrics
    └── *.png / *.jpg        Loss curves, PR curves, sample batches
```

None of these artifacts are committed — `.gitignore` tracks only the
directory structure.

## Dataset Workflow

The dataset is fully reproducible from two commands:

```bash
python -m ai.object_detection.data_tools.download   # fetch raw sources
python -m ai.object_detection.data_tools.pipeline   # merge -> split -> build -> validate
```

Selected sources, licenses, and rationale are documented in
`object_detection/docs/dataset-manifest.md`. Sources that require a
login (D-Fire) have step-by-step instructions in
`object_detection/docs/download_instructions.md`; the pipeline simply
skips sources that are not downloaded yet and picks them up on the
next run.

### Stages

1. **Download** (`data_tools/download.py`) — every automatable archive
   is fetched with an md5 check and unpacked under `datasets/raw/`.
   Raw files are originals: nothing ever modifies them.
2. **Merge + standardize** (`data_tools/merge.py`) — every enabled
   source in `configs/sources.yaml` is walked, class ids are remapped
   to the unified scheme (`0 fire · 1 smoke · 2 person`), COCO JSON is
   converted to YOLO, byte-identical images are deduplicated by md5,
   corrupted images and malformed labels are excluded, and everything
   lands in `datasets/merged/` as `<source>__<name>` files with full
   provenance in `merged/provenance.json`.
3. **Split** (`data_tools/split.py`) — deterministic 70/20/10
   train/val/test assignment (seed 42), stratified by class signature
   so each split sees a similar class mixture. Same inputs + seed =
   byte-identical splits (`merged/splits.json`).
4. **Build** (`data_tools/build.py`) — copies the merged files into
   the layout `configs/dataset.yaml` declares
   (`processed/images/<split>/`, `processed/labels/<split>/`) and
   generates `processed/data.yaml` for Ultralytics.
5. **Validate + report** (`data_tools/validator.py`, `quality.py`) —
   see below.

### Validation

`python -m ai.object_detection.data_tools.validator --root processed`
checks corrupted images (header probe; `--deep` fully decodes with
cv2), unsupported formats, missing/empty/orphan/malformed labels,
duplicated images and annotations, invalid class ids, and boxes
outside image bounds. It writes `datasets/reports/dataset_report.json`
and `.md` and exits non-zero when error-severity findings exist.
Empty labels are warnings by design: they are valid negative samples.

`python -m ai.object_detection.training.dataset_info` prints a quick
summary (available sources, merged size, per-split class balance).

### Reports

Every pipeline run regenerates `datasets/reports/`:
`merge_report.md` (per-source stats, dedup counts, conversion rules),
`split_report.md` (seed, ratios, stratification table),
`dataset_report.{json,md}` (validation findings), and
`quality_report.md` (class balance, potential issues,
recommendations).

### Adding a new dataset

1. Place the raw files under `datasets/raw/<name>/` (or add a
   `DownloadSpec` in `data_tools/download.py` if it is directly
   downloadable).
2. Add an entry to `configs/sources.yaml`: `kind: yolo` with a
   `class_map` translating its ids to `0 fire · 1 smoke · 2 person`
   (map to `null` to drop a class), or `kind: coco` with `images`,
   `annotations`, and `categories`.
3. Document it in `docs/dataset-manifest.md` (license included).
4. Re-run the pipeline and review the regenerated reports.

## Adding a New AI Module

1. Create `ai/<module>/` with its own `paths.py` (derive everything
   from `Path(__file__).resolve().parent`), `configs/`, and code.
2. Reuse `ai/shared/utils/` — logging, seeding, device selection,
   YAML machinery, run naming. Do not duplicate utilities.
3. Keep the module self-contained; modules never import each other.

## Integration with FireRescue AI (Phase 8E — implemented)

The hand-off the MVP was designed for is now in place:

- `perception/detectors/yolo.py` implements `YOLODetector` on the
  existing `AbstractDetector` interface. It loads the newest ONNX
  export from `ai/object_detection/models/exports/` with ONNX Runtime
  and runs the full inference pipeline (letterbox preprocessing,
  decoding, confidence filtering, class-aware NMS, class mapping to
  `DetectionResult`).
- `backend/main.py` registers it in `DetectorRegistry` alongside
  `ground_truth` at startup. Registration always succeeds: with no
  exported model (or no onnxruntime installed) the detector degrades
  gracefully and reports zones as UNOBSERVED.
- The active detector is chosen by `perception_detector` in
  `backend/config/settings.py` (`"ground_truth"` — still the default —
  or `"yolo"`); thresholds and the model location are the
  `yolo_*` settings. No REST, WebSocket, or frontend contract changed.
- The detector reads images from `frame.channels["rgb"]` (numpy BGR
  array or image path) — the channel the Frame model reserved for
  this. The simulation does not emit that channel yet, so with `yolo`
  active the system runs and reports UNOBSERVED until a future phase
  supplies imagery.
