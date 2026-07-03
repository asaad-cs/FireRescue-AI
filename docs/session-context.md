# FireRescue AI — Future Session Context

> Paste this document at the start of any new AI session to provide complete project context without reading the repository. Last updated: 2026-07-03, end of Phase 8F (simulated camera integration).

---

## What Is FireRescue AI?

FireRescue AI is a personal software research prototype — NOT a commercial product, NOT a startup, NOT a production system. It explores how an AI-assisted situational awareness system could support firefighters operating inside burning buildings.

A virtual drone explores a simulated building using breadth-first search, sensors detect hazards and victim signals, and an operator monitors a live tactical dashboard. Everything runs in software simulation. The architecture is explicitly hardware-agnostic: real sensor input can be wired in by replacing a single adapter class.

**Version:** 1.0.0 (MVP complete, frozen, published on GitHub) + Version 2 in progress (AI workspace)
**Stack:** Python 3.12 + FastAPI (backend) · React 18 + TypeScript + Vite + Tailwind + Zustand (frontend) · Ultralytics YOLO + PyTorch (AI workspace, V2)

---

## Git / GitHub Status

| Item | Value |
|---|---|
| Repository | https://github.com/asaad-cs/FireRescue-AI (public) |
| Branch | `main` (tracking `origin/main`) |
| Latest commit | `c5edef9` — "FireRescue AI v1.0.0 — Initial MVP Release" |
| Tag | `v1.0.0` → `c5edef9` |
| GitHub Release | "FireRescue AI v1.0.0" published, attached to the tag |
| Git identity | `asaad-cs <ahmed.s.alfaidi@gmail.com>` (global config; fixed 2026-07-02 — the initial commit was amended from a placeholder identity and force-pushed with lease; the tag was moved to match) |
| License | MIT |

**Version 2 checkpoints:** annotated tags `v2.0-phase-8c` (dataset engineering) and `v2.0-phase-8f` (training + YOLO integration + simulated camera) exist locally on `main` after `c5edef9`. NOTHING has been pushed to GitHub; pushing is pending a user decision. Generated data (raw downloads, merged/, processed/, checkpoints, exports, simulation/camera/images/) is gitignored — only code, configs, docs, tests, and reports are tracked.

---

## MVP v1.0.0 — Frozen

The MVP is complete and frozen. All 286 MVP backend tests, 295 frontend tests, and `tsc --noEmit` (0 errors) pass unchanged. Never modify frozen MVP logic. The ONLY exceptions ever made (Phases 8E/8F, via the officially documented integration seams) are: additive config fields in `backend/config/settings.py`, the detector registration block in `backend/main.py`, a two-line adapter-construction swap in `backend/main.py` + `backend/api/routes.py`, and NEW additive files (`perception/detectors/yolo.py`, `simulation/camera/`, `backend/ingestion/camera_adapter.py`, new test files). No existing MVP behavior changed; frontend, REST, and WebSocket contracts are untouched.

### Architecture (unchanged)

```
┌──────────────────────────────────────────────────────────────────────┐
│  Operator Dashboard  (React 18 + TypeScript + Vite + Tailwind)       │
│  http://localhost:5173                                                │
│                                                                       │
│  Zustand Store (4 slices) ← useWebSocket hook ← ws://localhost:8000  │
│  REST calls → /api/* (Vite proxy) → http://localhost:8000            │
└───────────────────────────────────┬──────────────────────────────────┘
                                    │  WebSocket — full MissionState push
                                    │  REST — mission control + scenarios + replay
┌───────────────────────────────────▼──────────────────────────────────┐
│  Backend  (FastAPI + uvicorn)  http://localhost:8000                 │
│                                                                       │
│  Broadcaster ──┐                                                      │
│  Recorder ─────┤← MissionManager ← Pipeline ← PerceptionEngine      │
│                │        ↑                                             │
│                │   SimAdapter → SimulationRunner (active scenario)    │
└────────────────┘──────────────────────────────────────────────────────┘
```

### Data flow (one simulation tick)

1. `SimulationRunner` moves drone to next zone, generates a `Frame` (pose + sensor channels)
2. `SimAdapter` delivers `Frame` to `MissionManager.on_frame()`
3. `Pipeline`: Validate → Enrich (pose → zone_id) → `PerceptionEngine`
4. `PerceptionEngine` → `GroundTruthDetector` → returns HazardLevel, victim probability, alerts
5. `MissionManager` merges result into `MissionState`, notifies all listeners
6. `Broadcaster.on_state_change()` pushes full `MissionState` JSON to all WebSocket clients
7. `Recorder.on_state_change()` deep-copies and stores the snapshot for replay
8. Frontend `setMissionState()` updates Zustand store → React re-renders

### The one invariant that must never break

**The frontend only ever receives `MissionState`.** No `Frame`, no `PerceptionResult`, no internal backend type is ever sent to the frontend. All derived values are computed server-side.

### Major architectural decisions that must never be broken

1. **Frontend receives only `MissionState`** — never expose internal backend types.
2. **DataSource interface is the hardware boundary** — `backend/ingestion/interface.py` is the only seam between simulation (or future hardware) and the backend.
3. **MissionManager is the single source of truth** — everything derives from `manager.get_state()`.
4. **Dashboard components are pure UI** — props from layout components; they never read the Zustand store directly.
5. **Inline styles for dynamic CSS values** — Tailwind purges dynamic class names.
6. **Scenario instances are never cached** — `SCENARIO_REGISTRY` stores factory functions.
7. **State-change listener pattern** — components register `on_state_change(state)` via `manager.register_state_change()`.

### REST API (http://localhost:8000)

```
GET  /                          Service info (reports version 1.0.0)
GET  /health                    Liveness check
POST /mission/start             IDLE/PAUSED → ACTIVE; restart from ENDED
POST /mission/pause             ACTIVE → PAUSED (409 if not ACTIVE)
POST /mission/resume            PAUSED → ACTIVE (409 if not PAUSED)
POST /mission/end               Any → ENDED
GET  /scenarios                 { active, scenarios: [{key, display_name, zone_count}] }
POST /scenarios/{key}/activate  Set scenario for next mission (404 if unknown)
GET  /replay/frames             { frames: [MissionState], count: N }
GET  /replay/frames/count       { count: N }
```

WebSocket `ws://localhost:8000/ws`: push-only, full `MissionState` JSON on every state change.

### Scenarios (5, default Warehouse Alpha)

`warehouse_alpha` 20 zones · `office_building` 12 · `hospital` 16 · `shopping_mall` 15 · `school` 16. Each has one CRITICAL hazard zone and deterministic sensor values.

### Replay system

`MissionRecorder` (backend) + `ReplaySlice`/`useReplayEngine` (frontend); REPLAY button after mission end; 0.5×/1×/2×; EXIT restores final state; WS messages for the same mission ignored during replay.

---

## Version 2 — Completed Phases

### Phase 8A — AI workspace scaffold (complete)
Created the isolated `ai/` package: directory structure, config placeholders, standalone utils (logger/paths/seed), scaffold entry points, utility tests. Nothing in `ai/` is imported by the MVP.

### Phase 8B — YOLO training infrastructure (complete)
Full training/evaluation/prediction pipeline for an Ultralytics YOLO detector (transfer learning, no custom networks):
- `train.py`: loads + eagerly validates all three configs (`ConfigError` names file and field), seeds RNGs, resolves device, creates timestamped run dir with a resolved `data.yaml`, then `YOLO(yolov8<size>.pt).train(**kwargs)`. Training starts ONLY on direct execution, never on import.
- `evaluate.py`: newest `best.pt` by default, `--weights`/`--split`, reports mAP50 / mAP50-95 / precision / recall.
- `predict.py`: single image or folder, `--conf`, saves annotated images; no webcam/video.
- `ai/requirements.txt` (ultralytics, torch, torchvision, opencv-python, numpy, matplotlib, pyyaml) — installed on this machine, **CPU-only torch (no CUDA)**.
- All ultralytics/torch imports are lazy so tests and config handling run without the ML stack.

### Phase 8B.1 — Multi-model architecture refactor (complete)
Pure filesystem/import refactor, zero behavior change, performed BEFORE dataset work (Phase 8C) so the workspace supports multiple AI modules. The YOLO infrastructure became the Object Detection module.

**Training entry point is now:** `python -m ai.object_detection.training.train`

### Phase 8C — Dataset engineering (complete, 2026-07-03)
Built the full dataset pipeline in `ai/object_detection/data_tools/` (download, image_utils, labels, coco, sources, validator, merge, split, build, quality, pipeline) plus `configs/sources.yaml`, and implemented `training/dataset_info.py` (no longer a scaffold).

- **Sources** (rationale in `ai/object_detection/docs/dataset-manifest.md`): Figshare CQU Fire-Smoke (11,027 imgs, CC BY 4.0, auto-downloaded + md5-verified), COCO 2017 val person subset (CC BY 4.0 annotations, auto-downloaded), D-Fire (21,527 imgs — login-gated, MANUAL download pending; steps in `docs/download_instructions.md`; its class order 0=smoke/1=fire is pre-mapped in sources.yaml and must be verified after download).
- **Unified classes:** 0 fire · 1 smoke · 2 person. Reproduce with `python -m ai.object_detection.data_tools.download` then `...data_tools.pipeline` (seed 42, stratified 70/20/10).
- **Result:** datasets/processed/ holds 12,545 images / 32,783 boxes (fire 12,043, smoke 9,963, person 10,777), split 8,781/2,509/1,255, validated CLEAN (0 errors; 1,169 byte-identical duplicates removed at merge). Reports in `datasets/reports/` (dataset_report.json/md, merge/split/quality_report.md — tracked in git). Raw/merged/processed data itself is gitignored; the pipeline skips missing sources and absorbs D-Fire automatically once it lands in `raw/dfire/`.

### Phase 8D — First training run (complete, 2026-07-03, smoke test)
Trained yolov8n for 5 epochs (in-memory override of the committed 50; configs untouched) on CPU (~4h15m — torch is CPU-only; the machine's RTX 3060 Ti is unused until a CUDA torch build is installed). Run `firerescue-detector-20260703-003931` under `models/checkpoints/` (gitignored): best.pt/last.pt, results.csv, TensorBoard logs, curves, evaluation/ artifacts. **Val metrics (standard protocol): P 0.621 / R 0.458 / mAP50 0.509 / mAP50-95 0.270** — still climbing at epoch 5, far from converged. ONNX export verified (11.7 MB, opset 20, `images [1,3,640,640]` → `[1,7,8400]`) and copied to `models/exports/`. Full report: `ai/object_detection/models/reports/training_report.md` (tracked).

### Phase 8E — YOLO integration (complete, 2026-07-03)
`perception/detectors/yolo.py`: `YOLODetector(AbstractDetector)` runs the exported ONNX via onnxruntime — letterbox preprocess, decode, confidence filter, class-aware numpy NMS, mapping to DetectionResult (fire→HazardSignal HIGH/CRITICAL, smoke→LOW/MODERATE, person→VictimSignal "unknown"). Registered in `backend/main.py` alongside `ground_truth`; selection via `settings.perception_detector` (**default is still "ground_truth"**); `yolo_*` settings hold thresholds + model location (newest export auto-discovered). Never raises: missing model/runtime/rgb-channel → graceful UNOBSERVED. 40 tests (mocked ORT + real-model integration test).

### Phase 8F — Simulated camera (complete, 2026-07-03)
`simulation/camera/` (provider.py + simulation_camera.yaml): zones map to folders of real photographs by scenario hazard level + victim presence (+ per-zone overrides), with seeded deterministic random selection, LRU cache, and fallback chain. `backend/ingestion/camera_adapter.py`: `CameraSimAdapter` DataSource-decorator attaches `frame.channels["rgb"]`; `make_data_source()` used by main.py AND the routes.py restart path. Controlled by `settings.camera_enabled` / `camera_config_path`; any problem degrades to plain SimAdapter. Populate the (gitignored) image library with `python -m ai.object_detection.data_tools.export_sim_images`. Live-verified: with `perception_detector="yolo"` the model detected the warehouse victim at 0.85 from an actual image. 34 tests.

---

## Long-Term Multi-Model AI Architecture

| Module | Status | Purpose |
|---|---|---|
| `ai/object_detection/` | **Implemented** | YOLO transfer learning — classes: `fire`, `smoke`, `person` |
| `ai/fire_detection/` | Planned (empty placeholder) | Dedicated fire & smoke analysis |
| `ai/mapping/` | Planned (empty placeholder) | SLAM / building mapping |
| `ai/sensor_fusion/` | Planned (empty placeholder) | Fusing vision with environmental sensor channels |

Rules: each module is self-contained (own `paths.py`, `configs/`, `datasets/`, `models/`, `training/`, `tests/`); generic utilities live in `ai/shared/utils/` and must stay model-agnostic; modules never import each other; dependency direction is strictly `module → shared`.

---

## Current AI Workspace Structure

```
ai/
├── requirements.txt            AI-only deps; backend requirements.txt untouched
├── shared/
│   └── utils/
│       ├── config.py           Generic: ConfigError, load_yaml, require
│       ├── device.py           select_device('auto'/'cpu'/'cuda'/index), lazy torch
│       ├── experiment.py       make_run_name, list_runs, find_weights (checkpoints_dir is a REQUIRED param — no module-specific defaults in shared code)
│       ├── logger.py           get_logger under 'firerescue.ai' namespace
│       ├── paths.py            AI_ROOT, PROJECT_ROOT, NOTEBOOKS_DIR, ensure_dir
│       └── seed.py             seed_everything (stdlib always; numpy/torch if installed)
├── object_detection/
│   ├── paths.py                MODULE_ROOT, CONFIGS_DIR, DATASETS_DIR, RAW/PROCESSED/EXTERNAL, MODELS_DIR, CHECKPOINTS_DIR, EXPORTS_DIR
│   ├── config.py               DatasetConfig / ModelConfig / TrainingConfig + loaders
│   ├── configs/
│   │   ├── dataset.yaml        root: datasets/processed · nc: 3 · names: fire, smoke, person · splits images/{train,val,test}
│   │   ├── model.yaml          size: n · epochs: 50 · image_size: 640 · batch: 16 · device: auto · optimizer: auto · lr: 0.01 · conf: 0.25 · iou: 0.45 · export: onnx
│   │   ├── training.yaml       seed: 42 · workers: 0 · AMP: true · patience: 10 · save_period: -1 · experiment: firerescue-detector · resume: false
│   │   └── sources.yaml        raw source registry + per-source class id maps (figshare identity · dfire swap · coco person→2)
│   ├── docs/                   dataset-manifest.md · download_instructions.md
│   ├── data_tools/             download · image_utils · labels · coco · sources
│   │                           · validator · merge · split · build · quality · pipeline
│   ├── datasets/
│   │   ├── raw/                Downloads (gitignored): figshare_fire_smoke, coco_person, dfire (manual, pending)
│   │   ├── merged/             Unified deduplicated set + provenance.json + splits.json (gitignored)
│   │   ├── processed/          FINAL YOLO dataset: 12,545 imgs, images/labels/{train,val,test}, data.yaml (gitignored)
│   │   ├── external/           (unused so far)
│   │   └── reports/            dataset/merge/split/quality reports (TRACKED in git)
│   ├── models/{checkpoints,exports}/          EMPTY — training populates
│   ├── training/
│   │   ├── train.py · evaluate.py · predict.py
│   │   └── dataset_info.py     Implemented — prints sources/splits/class balance
│   └── tests/                  20 files, 218 tests (+ _helpers.py synthetic fixtures)
├── fire_detection/{configs,training,models}/  .gitkeep placeholders
├── mapping/  sensor_fusion/                   .gitkeep placeholders
└── notebooks/                                 empty
```

---

## Current Test Counts (verified 2026-07-02)

```
Backend:    578 tests + 50 subtests   (python -m pytest)
            = 286 MVP + 218 AI + 40 YOLO integration + 34 camera
Frontend:   295 tests                  (npx vitest run)
TypeScript: 0 errors                   (npx tsc --noEmit)
```
(verified 2026-07-03, end of Phase 8F)

---

## Important Implementation Decisions (do not forget)

1. **Lazy heavy imports.** ultralytics/torch are imported inside functions (`load_yolo_class()`, `cuda_available()`), never at module top level. Config validation and all tests run without the ML stack.
2. **Training never auto-starts.** Only `if __name__ == "__main__"` triggers `model.train()`. `prepare_session()` is side-effect-light (creates run dir + resolved data.yaml only) and is independently testable via injected configs and `require_data=False`.
3. **No hardcoded paths anywhere.** Every path derives from `Path(__file__)`. The committed `dataset.yaml` keeps a RELATIVE root resolved against `ai/object_detection/` (MODULE_ROOT); each training run writes a resolved absolute `data.yaml` into its run dir because Ultralytics needs one.
4. **Shared utils stay generic.** `experiment.py` takes `checkpoints_dir` as a required argument — adding a module-specific default to shared code is a layering violation.
5. **Windows path gotcha.** `Path("/x").is_absolute()` is False on Windows Python 3.12. Relative-path validation must also reject `p.drive or p.root`.
6. **pytest logging gotcha.** pytest 9's logging plugin attaches capture handlers to non-propagating loggers — never assert absolute handler counts; assert that repeated calls don't add handlers.
7. **Fail-fast contract.** `train` raises ConfigError listing missing dataset split dirs; `evaluate` raises if no checkpoint exists; `predict` validates source paths and image extensions (.jpg .jpeg .png .bmp).
8. **Ultralytics arg mapping.** patience=0 disables early stopping; batch=-1 auto-tunes; save_period=-1 keeps only best/last; run dirs are `<experiment>-<YYYYmmdd-HHMMSS>` under `models/checkpoints/`, layout `<run>/weights/{best,last}.pt`.
9. **.gitignore** uses wildcard patterns (`ai/*/datasets/raw/*` etc. with `.gitkeep` exceptions, plus `yolov8*.pt`, `.ipynb_checkpoints/`) so future modules are covered automatically. `.claude/settings.local.json` is ignored.
10. **Logger namespace** is `firerescue.ai.*` (consistent with the backend's `firerescue.*`); AI logging never imports backend settings.
11. **CPU-only torch** is installed on this machine; `device: auto` resolves to `cpu`. Real training will be slow until a CUDA build is installed.
12. **Open item:** `npm audit` flags a dev-only esbuild/vite/vitest chain (GHSA-67mh-4wv8-2f99); the fix is a breaking Vite upgrade — user has not decided. No runtime/production exposure.

---

## Known Limitations

MVP (unchanged from v1.0.0):
1. No database — in-memory state only; backend restart clears history
2. No scenario selection UI — switching requires a REST API call
3. Deterministic sensor data — fixed values per zone
4. Ground-truth perception only — no false positives, no ML inference in the running system yet
5. One drone per mission
6. No persistent alert acknowledgements
7. No authentication — local research tool only
8. Client-side replay history lost on page reload

Version 2 (current):
9. D-Fire is not merged yet — its download is manual (login required); the dataset has only 2 negative samples (and the camera's `safe/` category only those 2 images) until D-Fire's 9,838 negatives arrive
10. Person images come from COCO val2017 only (≈2,700); fire+person co-occurrence is under-represented (scale-up path documented in download_instructions.md)
11. The deployed model is the 5-epoch smoke-test baseline (val mAP50 0.509) — noticeable false positives (LOW smoke suspicions, ~0.27 spurious victim confidence in safe zones); the 50-epoch run is pending
12. Torch is CPU-only — training is ~51 min/epoch until a CUDA build is installed (RTX 3060 Ti present); ONNX inference also runs on CPU (~0.3 s/frame, fine at 1 s ticks)
13. `perception_detector` default remains "ground_truth"; "yolo" is opt-in until the real model lands
14. The dashboard does not display camera images or bounding boxes (frontend deliberately untouched)
15. V2 work is committed locally (tags v2.0-phase-8c, v2.0-phase-8f) but not pushed

---

## Version 2 Roadmap

| Phase | Title | Status |
|---|---|---|
| 8A | AI workspace scaffold | Complete |
| 8B | YOLO training infrastructure | Complete |
| 8B.1 | Multi-model architecture refactor | Complete |
| 8C | Dataset engineering (data_tools pipeline, sources, validation, reports) | Complete |
| 8D | First training run (5-epoch smoke test, mAP50 0.509) + verified ONNX export | Complete |
| 8E | YOLODetector integration via DetectorRegistry (config-driven switching) | Complete |
| 8F | Simulated drone camera (real images → Frame.channels["rgb"]) | Complete |
| **8G** | **To be defined by the user — do not start without instruction** | **NEXT** |
| — | Fire detection, SLAM/mapping, sensor fusion modules | Future |

Integration path (unchanged, requires zero frozen-module edits): a learned detector implements `BaseDetector` (`perception/base/detector.py`), loads an exported model from `ai/object_detection/models/exports/`, registers in `DetectorRegistry` alongside `ground_truth`, and is activated via `perception_detector` in `backend/config/settings.py`.

**Constraints that remain in Version 2:** no authentication, no analytics dashboards, no cloud infrastructure, no mobile optimization, and **"STOP after each phase, wait for user instruction" always applies.**

---

## THE EXACT NEXT TASK

> **Note:** Phases 8A through 8F are all complete and committed (tags `v2.0-phase-8c`, `v2.0-phase-8f`, 2026-07-03). Do NOT redo them. The system runs end-to-end: simulated camera → YOLO ONNX inference → MissionState → dashboard.

**Phase 8G is not yet defined — wait for the user.** The highest-value candidates, in recommended order:
1. Install a CUDA torch build (an RTX 3060 Ti 8 GB sits idle; ~51 min/epoch → ~1–2 min) and run the full 50-epoch training on the committed config, ideally after manually downloading D-Fire (docs/download_instructions.md; +21.5k images incl. 9.8k negatives — biggest gain for smoke recall and false-positive suppression).
2. Threshold calibration from the PR/F1 curves, then consider flipping `perception_detector` default to "yolo".
3. Dashboard camera/detection view (frontend work — has been deliberately out of scope so far).

Also pending user decisions: pushing the checkpoints to GitHub.

---

## Documentation Status

`docs/` (14 files): api-design, architecture, database, demo-guide, developer-guide, handoff-report, project-status, requirements, roadmap, session-context (this file), simulation, system-overview, tech-stack, ui-design — all reflect MVP v1.0.0. `ai/README.md` documents the V2 multi-model architecture, all commands, config semantics, expected outputs, and the module-addition recipe. Root `README.md` covers the MVP (does not yet mention `ai/` — intentional until V2 is committed/released).

---

## How to Start the Application (MVP — unchanged)

```bash
# Prerequisites: Python 3.12+, Node.js 18+
pip install -r requirements.txt
cd frontend && npm install && cd ..

# Terminal 1 — Backend
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --ws websockets

# Terminal 2 — Frontend
cd frontend && npm run dev
```

Open `http://localhost:5173`. Mission auto-starts.

```bash
# Run all tests
python -m pytest               # Backend: 375 + 50 subtests
cd frontend && npx vitest run  # Frontend: 295
cd frontend && npx tsc --noEmit

# AI workspace (requires ai/requirements.txt installed)
python -m ai.object_detection.training.train      # fails fast until Phase 8C dataset exists
python -m ai.object_detection.training.evaluate   # fails fast until a model is trained
```
