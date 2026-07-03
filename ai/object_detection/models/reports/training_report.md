# Training Report — First Object Detection Model (Phase 8D smoke test)

- **Run:** `firerescue-detector-20260703-003931`
- **Date:** 2026-07-03
- **Purpose:** first end-to-end training of the FireRescue AI object
  detector — a smoke test proving the Phase 8B training infrastructure
  and the Phase 8C dataset produce a working model. Not a production
  model.

## Training configuration

Committed configs were used unchanged, with a single in-memory
override (`epochs: 50 → 5`) applied via `prepare_session(model=...)`
for the smoke test.

| Setting | Value | Source |
|---|---|---|
| Base model | `yolov8n.pt` (transfer learning) | model.yaml `size: n` |
| Epochs | **5** (smoke-test override; committed value is 50) | override |
| Image size | 640 | model.yaml |
| Batch | 16 | model.yaml (batch=-1 auto-tune needs CUDA) |
| Optimizer | `auto` → AdamW(lr=0.001429, momentum=0.9) | model.yaml |
| Workers | 0 (Windows-safe) | training.yaml |
| Seed | 42 (deterministic) | training.yaml |
| Early-stopping patience | 10 | training.yaml |
| AMP | requested; disabled by Ultralytics on CPU | training.yaml |
| Dataset | `datasets/processed` — 12,545 imgs (8,781/2,509/1,255), nc=3 (fire, smoke, person) | dataset.yaml |

## Hardware

- CPU: Intel Core i7-12700F (20 logical cores) — training device
- GPU: **NVIDIA RTX 3060 Ti 8 GB present but unused** — installed
  torch is `2.12.1+cpu`; `device: auto` resolved to `cpu`
- ultralytics 8.4.84 · Python 3.12.10 · Windows 11 Pro

## Training duration

- In-training compute: **≈ 4 h 15 m** (epochs 1–2: 6,188 s; epochs
  3–5 + final val: 9,094 s), ≈ 51 min/epoch at ~5.5 s/batch
- Wall clock was longer (≈ 6 h): the session's background-task runner
  killed the process twice; the run resumed cleanly from `last.pt`
  both times (Ultralytics `resume=True`), which also exercised the
  checkpoint/resume path. Epochs are contiguous in `results.csv`.

## Final metrics (best.pt, val split, 2,509 images / 6,441 boxes)

**Standard protocol** (training-end validation, conf≈0.001):

| Class | Precision | Recall | mAP50 | mAP50-95 |
|---|---|---|---|---|
| **all** | 0.621 | 0.458 | **0.509** | **0.270** |
| fire | 0.643 | 0.467 | 0.552 | 0.283 |
| smoke | 0.679 | 0.346 | 0.431 | 0.207 |
| person | 0.540 | 0.562 | 0.545 | 0.319 |

**Deployment-threshold protocol** (`evaluate` with model.yaml
conf=0.25, iou=0.45 — the thresholds the backend would run with):

| Class | Precision | Recall | mAP50 | mAP50-95 |
|---|---|---|---|---|
| **all** | 0.689 | 0.449 | 0.391 | 0.212 |
| fire | 0.708 | 0.455 | 0.408 | 0.218 |
| smoke | 0.732 | 0.341 | 0.295 | 0.141 |
| person | 0.626 | 0.550 | 0.471 | 0.276 |

Both are reported because the confidence floor changes mAP: the first
is the comparable research number, the second reflects behaviour at
the configured operating point.

Progression (mAP50 by epoch): 0.309 → 0.325 → 0.343 → 0.459 → 0.509 —
still climbing steeply at epoch 5; the model is far from converged.

## Checkpoints and artifacts

```
ai/object_detection/models/checkpoints/firerescue-detector-20260703-003931/
├── weights/best.pt            best checkpoint (epoch 5)     ~5.9 MB
├── weights/last.pt            resume point                  ~5.9 MB
├── weights/best.onnx          ONNX export (see below)
├── results.csv                per-epoch metrics (5 epochs)
├── events.out.tfevents.*      TensorBoard logs (3 files: one per leg)
├── confusion_matrix*.png · BoxPR/BoxF1/BoxP/BoxR_curve.png
├── train_batch*.jpg · val_batch*_{labels,pred}.jpg
└── evaluation/                Step-4 eval: metrics.json,
                               confusion matrices, PR/F1/P/R curves,
                               val prediction images
```

## ONNX export

| Item | Value |
|---|---|
| File | `weights/best.onnx`, copied to `models/exports/firerescue-detector-20260703-003931-best.onnx` |
| Size | 11.7 MB · opset 20 |
| Input | `images` — `[1, 3, 640, 640]` float32 |
| Output | `output0` — `[1, 7, 8400]` (4 box coords + 3 class scores × 8,400 anchors) |
| Verification | `onnx.checker` passed; onnxruntime session loaded; dummy forward pass returned the expected shape |

## Observations

1. The full pipeline works end-to-end: config system → dataset →
   training → checkpoints → TensorBoard → resume → evaluation → ONNX.
   No runtime exceptions occurred in training itself.
2. mAP50 0.51 after only 5 epochs of yolov8n is a healthy baseline;
   the curve had not flattened, so the committed 50-epoch config
   should land dramatically higher.
3. **Smoke is the weakest class** (recall 0.35) — expected: smoke is
   diffuse, and the D-Fire source (the biggest smoke corpus and all
   the negatives) is not merged yet.
4. Person performs well despite being trained only on COCO val2017.
5. CPU is the binding constraint: ~51 min/epoch means the full
   50-epoch run would take ~42 h on this machine.

## Recommended next improvements

1. **Install a CUDA torch build** — an RTX 3060 Ti 8 GB is sitting
   idle; it would cut epoch time from ~51 min to ~1–2 min and make
   the 50-epoch run practical (~1–2 h).
2. **Add D-Fire** (manual download, `docs/download_instructions.md`)
   before the real training run — +21.5k images including 9.8k
   negatives; biggest expected gain for smoke and false-positive
   suppression.
3. Run the **full 50-epoch training** on the committed config once
   CUDA (and ideally D-Fire) are in place; consider `yolov8s` if the
   GPU handles it comfortably.
4. After the real run, pick the operating confidence threshold from
   the F1/PR curves instead of the default 0.25.
5. Evaluate on the held-out **test split** only for the final model
   candidate (keep val for iteration).
