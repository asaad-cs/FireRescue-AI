# FireRescue AI — Project Context (Read This First)

> This document is written for an AI agent or developer with **zero prior context** on this project. Read it top to bottom before touching any code. It is the authoritative project brief — if anything in another doc conflicts with this file, trust this file and flag the discrepancy.

**Repository status as of this document: FROZEN, COMMITTED, PUSHED.**
Latest commit: `0861ff0` — "Checkpoint: Demo-ready architecture + AI v2 baseline" — on branch `main`, in sync with `origin/main` at `https://github.com/asaad-cs/FireRescue-AI`. This was a **documentation-and-checkpoint session only**: no features were added, no model was retrained, no architecture changed. See the **Migration Report** section at the end for full verification detail.

---

# ==================================================
# PROJECT OVERVIEW
# ==================================================

## What this project is

FireRescue AI is a **personal research and portfolio prototype** — not a commercial product, not a startup, not a system intended for real emergency operations. It explores how an AI-assisted situational awareness system could help firefighters operating inside dangerous buildings.

A virtual drone explores a simulated building using breadth-first search. Simulated sensors report hazard levels (temperature, CO, smoke) and victim-signal probabilities per zone. A live operator dashboard (the "EOC" — Emergency Operations Center view) shows the drone's progress, a tactical map, alerts, and — in Version 2 — a live camera feed with real-time AI object detection (fire / smoke / person) running against real photographs.

Everything runs in software simulation. The system is explicitly architected so that real hardware could be substituted later by replacing exactly one adapter class — nothing else would need to change.

## High-level architecture

```
┌───────────────────────────────────────────────────────────────────────┐
│  Frontend Dashboard  (React 18 + TypeScript + Vite + Tailwind)        │
│  http://localhost:5173                                                 │
│                                                                        │
│  Zustand Store (4 slices) ← useWebSocket hook ← ws://localhost:8000   │
│  REST calls → /api/* (Vite proxy) → http://localhost:8000             │
└───────────────────────────────────┬───────────────────────────────────┘
                                    │  WebSocket — full MissionState push
                                    │  REST — mission control + scenarios + replay
┌───────────────────────────────────▼───────────────────────────────────┐
│  Backend  (FastAPI + uvicorn)  http://localhost:8000                  │
│                                                                        │
│  Broadcaster ──┐                                                       │
│  MissionRecorder┤← MissionManager ← Pipeline ← PerceptionEngine       │
│                │        ↑                                              │
│                │   SimAdapter/CameraSimAdapter → SimulationRunner      │
└────────────────┘───────────────────────────────────────────────────────┘
```

### The one invariant that must never break

**The frontend only ever receives `MissionState`.** It has zero knowledge of `Frame`, `PerceptionResult`, `ZoneHistory`, or any other internal backend type. All derived values (explored %, alert counts, victim signal counts, the live camera image itself) are computed server-side and included in `MissionState`. This has held from the MVP through every Version 2 phase without exception.

## Folder structure

```
FireRescue-AI/
├── backend/                    FastAPI application
│   ├── main.py                 App entry point, lifespan, WebSocket endpoint, detector registration
│   ├── api/routes.py           REST endpoints (mission control, scenarios, replay)
│   ├── config/settings.py      ALL tuneable values — the single config surface for the whole app
│   ├── mission/
│   │   ├── manager.py          Mission state machine; single source of truth for MissionState
│   │   └── recorder.py         Records every MissionState snapshot for replay
│   ├── models/                 Pydantic models: MissionState, Alert, Frame, VisionFrame, etc.
│   ├── pipeline/                Validator → Enricher → PerceptionEngine orchestration
│   ├── ingestion/
│   │   ├── interface.py        DataSource protocol — THE hardware-independence boundary
│   │   ├── sim_adapter.py      Adapts SimulationRunner to DataSource (no camera)
│   │   └── camera_adapter.py   CameraSimAdapter — decorates a DataSource, attaches Frame.channels["rgb"]
│   ├── websocket/broadcaster.py  Fans MissionState JSON to all WebSocket clients
│   └── tests/                  Backend test suite (part of the 623-test total, see below)
│
├── simulation/                 Simulation engine (building, drone BFS, sensors, scenarios)
│   ├── camera/
│   │   ├── provider.py         ZoneCategoryResolver + ZoneImageProvider — hazard-category image selection
│   │   ├── simulation_camera.yaml  Camera config: image root, category folders, seed mode
│   │   └── images/             GENERATED runtime folder (gitignored) — rebuilt from assets/simulation_dataset/
│   └── tests/
│
├── perception/                 Detection framework
│   ├── engine.py                PerceptionEngine — orchestrates a registered detector
│   ├── detectors/
│   │   ├── ground_truth.py      Reads static hazard/victim maps from the active scenario (MVP default)
│   │   └── yolo.py               YOLODetector — runs an exported ONNX model via onnxruntime
│   ├── base/detector.py         AbstractDetector interface both detectors implement
│   ├── registry/registry.py     DetectorRegistry — name → detector instance, switched via settings
│   └── tests/
│
├── frontend/                    Operator dashboard (React 18 + TS + Vite + Tailwind + Zustand)
│   └── src/
│       ├── types/mission.ts     TypeScript mirror of backend Pydantic models
│       ├── stores/missionStore.ts  Zustand store: connection / mission / ui / replay slices
│       ├── components/dashboard/MissionCamera.tsx  Live camera monitor UI (see Current State)
│       └── ...
│
├── ai/                           AI/ML workspace — isolated, nothing here is imported by the MVP runtime
│   ├── shared/utils/             Generic, model-agnostic utilities (config, device, experiment, logger, paths, seed)
│   ├── object_detection/         The only implemented AI module (YOLO fire/smoke/person detector)
│   │   ├── configs/               dataset.yaml, model.yaml, training.yaml, sources.yaml
│   │   ├── data_tools/             download/validate/merge/split/build/quality/pipeline + export tools
│   │   ├── datasets/               raw/ merged/ processed/ (all gitignored, regenerate via data_tools) + reports/ (tracked)
│   │   ├── models/                 checkpoints/ exports/ (BOTH GITIGNORED — see Known Issues: model files are NOT in git)
│   │   └── training/               train.py, evaluate.py, predict.py, dataset_info.py
│   ├── fire_detection/ mapping/ sensor_fusion/   Empty placeholders for future modules — do not build yet
│   └── requirements.txt          AI-only Python deps (ultralytics, torch, onnxruntime, etc.)
│
├── assets/
│   ├── simulation_dataset/       PRODUCTION master image library (Architecture A: category/scene), tracked in git
│   │   └── _curation/            approved / manual_review / rejected staging area — NOT wired into the runtime
│   └── demo_dataset/             ISOLATED demo image set (flat, Architecture-A-shaped), tracked in git
│
├── docs/                         All project documentation (this file is the most current)
├── memory/                       NOT part of the git repo — Claude Code's cross-session memory (separate machine-local store)
├── requirements.txt              Backend Python dependencies
└── README.md                     Public-facing project overview
```

## Runtime flow — one simulation tick

1. `SimulationRunner` moves the drone to the next zone (BFS), generates a `Frame` (pose + sensor channels).
2. The active `DataSource` delivers the `Frame` to `MissionManager.on_frame()`. If the camera is enabled, `CameraSimAdapter` has already decorated the frame with `channels["rgb"]` — a real photograph selected by `ZoneImageProvider` based on the zone's hazard/victim category.
3. `MissionManager` runs the frame through the `Pipeline`: **Validate → Enrich (pose → zone_id) → PerceptionEngine**.
4. `PerceptionEngine` calls whichever detector is registered as `settings.perception_detector` (`"ground_truth"` or `"yolo"`) and returns a `PerceptionResult` (hazard level, victim probability, any new alerts). If YOLO is active, its result also carries a `vision` payload (base64 JPEG of the analyzed frame + bounding boxes + inference time).
5. `MissionManager` merges the result into `MissionState` (including `MissionState.vision` if present) and notifies all registered listeners.
6. `Broadcaster` pushes the full `MissionState` as JSON to every connected WebSocket client. `Recorder` deep-copies and stores the same state for replay.
7. The frontend's `useWebSocket` hook receives the message, calls `setMissionState()` in the Zustand store, and React re-renders — including `MissionCamera`, which shows the live image and detection boxes if `vision` is present.

## AI pipeline

- **Framework:** Ultralytics YOLO (transfer learning on `yolov8n`), exported to ONNX, run via `onnxruntime` inside `perception/detectors/yolo.py`.
- **Classes:** `0=fire`, `1=smoke`, `2=person`.
- **Training path (offline, in `ai/`):** `python -m ai.object_detection.training.train` reads `configs/{dataset,model,training}.yaml`, trains on GPU or CPU, writes a timestamped run under `ai/object_detection/models/checkpoints/<run>/weights/{best,last}.pt`, and can export to ONNX under `ai/object_detection/models/exports/`.
- **Serving path (online, in the running app):** `YOLODetector` auto-discovers the **newest** `.onnx` file in `ai/object_detection/models/exports/` (or an explicit path via `settings.yolo_model_path`), and runs letterbox-preprocess → inference → confidence filter → class-aware NMS → maps detections to `HazardSignal` / `VictimSignal`. It never raises — any problem (missing model, bad channel data) degrades gracefully to `UNOBSERVED`.
- **Switching detectors is config-only:** both detectors are always registered in `DetectorRegistry`; `settings.perception_detector` selects which one runs. The default remains `"ground_truth"` (deterministic, no ML) — `"yolo"` is opt-in.

## Simulation pipeline

- **Scenarios (5):** `warehouse_alpha` (20 zones, default), `office_building` (12), `hospital` (16), `shopping_mall` (15), `school` (16). Each has one CRITICAL hazard zone and fixed victim placements.
- **Drone:** breadth-first search over the zone graph; deterministic, completes in `zone_count × tick_interval` seconds (default tick = 1.0s).
- **Camera:** `simulation/camera/provider.py` maps each zone to a hazard/victim **category** (fire, smoke, fire_smoke, person, safe, and combination categories) via `ZoneCategoryResolver`, then `ZoneImageProvider` deterministically-or-randomly picks a real photograph from that category's folder — with a **mission-scoped no-repeat pool** (an image is never reused within a mission until its folder is exhausted, and the image that just closed a cycle is excluded from the next cycle's opening pick). Selection mode is controlled by `simulation_camera.yaml`'s `seed` field: `null` (default — fresh random seed per mission, logged as `provider.effective_seed` for after-the-fact reproduction), an integer (deterministic), or `randomize: false` (always the first image).
- **Image source root** is `assets/simulation_dataset/` (production) or `assets/demo_dataset/` (Demo Mode) — see Current State below. The runtime folder actually read by the provider, `simulation/camera/images/`, is a **generated, gitignored mirror** rebuilt by `python -m ai.object_detection.data_tools.export_simulation_library`.

---

# ==================================================
# CURRENT STATE
# ==================================================

## Completed work (all phases, chronological)

| Phase | Deliverable |
|---|---|
| 0–7C | MVP v1.0.0 — simulation engine, backend, perception (ground truth only), frontend dashboard, 5 scenarios, replay. **Frozen since 2026-07-01.** |
| 8A–8C | AI workspace scaffold, YOLO training infrastructure, dataset engineering pipeline (12,545 images / 32,783 boxes, sources: Figshare CQU fire-smoke + COCO val2017 person subset; D-Fire still not merged, manual download) |
| 8D–8F | First trained model (5-epoch CPU smoke test), `YOLODetector` integration via `DetectorRegistry`, simulated drone camera (`CameraSimAdapter`) |
| 8G–8I.1 | Live AI Vision inside `MissionState.vision`, permanent master image library (`assets/simulation_dataset/`), EOC dashboard redesign (`MissionCamera`, `DetectionCards`, `MissionOpsPanel`) |
| 8J | Scene-aware dataset split — fixed near-duplicate train/val/test leakage (whole "scenes" assigned together, not individual images). Regenerated split: 8,783/2,515/1,247. This is why later benchmark numbers are not comparable to the original 5-epoch smoke-test metric. |
| 8K + 8K.1 | Camera experience — mission-scoped no-repeat image pool, `seed: null` entropy mode as the new default; `MissionCamera` redesigned as a live camera monitor (HUD, edge-aware detection labels, LIVE/STALE/ACQUIRING/standby link states, mission-scoped history, REPLAY-aware badge) |
| 9A/9B | Read-only dataset assessment (found the training set is ~85% outdoor with near-zero indoor-building imagery) + curation staging (234 images sorted into `assets/simulation_dataset/_curation/{approved,manual_review,rejected}/`) |
| 10A.1–10A.4, 10B.1 | Extended the dataset README with target counts/acceptance rules; **built, then reversed, a competing "Environment→Scene" folder layout**; formally decided **Architecture A (Category→Scene) is the sole official dataset filesystem standard project-wide** |
| Demo.1–Demo.6 | Built an isolated `assets/demo_dataset/`; added **Demo Mode** as a single settings flag; fixed a real image-recycle-repetition bug in `ZoneImageProvider`; expanded the Safe category from 2 images to 46–48 using only pre-existing repo assets |
| AI.1 | Retrained YOLO on GPU (60 epochs) and ran a full 7-mission live validation. **Verdict: "Demo Ready with Minor Issues." Training has converged — the data, not the model, is now the bottleneck.** |
| **This session** | Verified all of the above is intact (tests pass, file counts match), created **one checkpoint commit** (`0861ff0`), pushed everything (branch + 4 tags) to GitHub, rewrote all project documentation for a clean handoff. **No code, dataset, or model changes were made.** |

## Production-ready components

These are stable, tested, and safe to build on without re-verifying from scratch:
- MVP simulation/backend/frontend loop (unchanged since v1.0.0)
- `GroundTruthDetector` (the committed default — deterministic, no ML, zero false positives/negatives)
- `YOLODetector` integration plumbing (ONNX loading, NMS, never-raises fallback) — the *code path* is production-quality even though the *model weights* behind it are still improving
- Simulated camera pipeline (`CameraSimAdapter`, `ZoneImageProvider`, mission-scoped no-repeat pool)
- Replay system (`MissionRecorder`, `ReplayControls`, `useReplayEngine`)

## Demo-only components

- **Demo Mode** (`settings.camera_demo_mode = True`): swaps the camera's image source to `assets/demo_dataset/` (a smaller, hand-curated, better-balanced set: fire 41 / smoke 30 / fire_smoke 39 / person 45 / safe 46, ≈201 images). Built specifically to give live demos a reliable, non-repetitive, non-mislabeled experience. **This flag is fully isolated** — zero changes to selection logic, resolver, or config format; only the image root path swaps in `make_data_source()`.
- The "yolo" detector itself is demo/experimental in the sense that it is not the committed default (`ground_truth` is) — flipping the default is a pending decision, not yet made.

## Experimental / not implemented

- **Scene-Aware Simulation Architecture** — a full design document exists (produced in chat during a prior session) proposing that zones carry an explicit "environment" tag (kitchen, warehouse, hospital, etc.) alongside their hazard category. **Nothing from this design has been implemented or approved.** Do not assume any environment-awareness exists in the simulator — `ZoneCategoryResolver` is hazard-category-only today.
- `ai/fire_detection/`, `ai/mapping/`, `ai/sensor_fusion/` — empty placeholder directories for future AI modules. No code exists in them.
- `CameraMediaSource` video/stream kinds — typed in the frontend (a deliberate video-first design decision) but never implemented; only `image` is functional.

---

# ==================================================
# LATEST MODEL
# ==================================================

- **Model name / run:** `firerescue-detector-20260705-064246`
- **Architecture:** YOLOv8n (Ultralytics transfer learning), exported to ONNX (opset 20)
- **File location:** `ai/object_detection/models/exports/firerescue-detector-20260705-064246-best.onnx` — **this file exists only on the machine that trained it; it is gitignored and was NOT pushed to GitHub.** See Known Issues.
- **Training configuration:** 60 epochs (in-memory override of the committed default of 50), batch 32 (was 16), patience 15 (was 10), cosine LR schedule (was off), GPU (RTX 3060 Ti). Image size, optimizer, base learning rate, seed (42), and augmentation were left at the committed `configs/*.yaml` defaults. Trained on the Phase 8J scene-aware split (8,783/2,515/1,247 images).
- **Training time:** 2.43 hours for 60 GPU epochs (vs. 2.53 hours for the original 5 CPU epochs — roughly 12.5× faster per epoch on GPU). Effectively converged by epoch ~57; the patience-15 early stop never triggered.

### Metrics (val split, evaluate.py, standard protocol)

| Metric | True old baseline (5 ep, CPU, re-measured on corrected split) | Current model (60 ep, GPU) |
|---|---:|---:|
| Precision (overall) | 0.702 | 0.685 |
| Recall (overall) | 0.450 | 0.528 |
| mAP50 (overall) | 0.3997 | **0.601** |
| mAP50-95 (overall) | 0.2255 | 0.334 |
| Fire — P/R/AP50/AP50-95 | .723/.457/.416/.235 | .682/.542/.628/.335 |
| Smoke — P/R/AP50/AP50-95 | .718/.324/.283/.139 | .674/.448/.534/.271 |
| Person — P/R/AP50/AP50-95 | .664/.569/.501/.303 | .697/.594/.642/.396 |
| Inference speed | 2.4 ms/img | 1.2 ms/img |

> Note: an earlier, informal citation of "mAP50 0.509" for the original 5-epoch model was measured on a dataset split that later turned out to leak near-duplicate images between train/val/test (fixed in Phase 8J). The 0.3997 figure above is the corrected, trustworthy baseline. Always compare new results against 0.3997/0.2255, never 0.509.

### Strengths

- Zero crashes across 7 full live-mission validations (real backend + WebSocket, not mocked).
- Fire detection: 6/6 live opportunities detected.
- Victim detection: 11/12 live opportunities detected (one miss).
- Near-zero fire↔smoke class confusion.
- Fast enough for real-time use at the app's 1-second tick rate (1.2 ms/image inference; onnxruntime runs on CPU by design even though training used GPU).

### Weaknesses

- Recall is still moderate (0.528 overall) — the model misses a meaningful fraction of true hazards/people, especially smoke (recall 0.448).
- **Confuses animals with people** — see Known Issues.
- **Two mislabeled training negatives cause false positives** — see Known Issues.
- Training has **converged on the current dataset** — running more epochs on the same data is not expected to improve these numbers further. The path to improvement is better/more diverse training data, specifically indoor-building imagery (see Next Priority).

---

# ==================================================
# KNOWN ISSUES
# ==================================================

1. **Animal → person false positives.** Confirmed live with 5 concrete, low-confidence (<0.7) examples: two zebras (0.68), a dog (0.34), a bird (0.41), a horse+dog (0.30), two seagulls (0.47/0.27). **Root cause: the 12,545-image training corpus contains zero animal images anywhere**, so the model has never been shown a "this is not a person" example for a non-human animal subject. More training on the existing data cannot fix this — it requires new negative examples.

2. **Two mislabeled "Safe" images in the production master library.** Files:
   - `assets/simulation_dataset/safe/dataset/figshare_fire_smoke__937_jpg.rf.ed5ada21f7d6a324aa17c59805e2000b.jpg` — actually shows an active wildfire with a fleeing bystander.
   - `assets/simulation_dataset/safe/dataset/figshare_fire_smoke__H_00980_png.rf.4d84d566b0beb02f02eaa97e20bb63df.jpg` — actually shows a large smoke/steam plume.

   Both were only "negative" in the training-annotation sense (their label file happened to be empty) — never in the sense of being visually hazard-free. `H_00980` is confirmed, via directly captured live evidence, to be the recurring source of false "smoke" detections in Production Mode. **These two files are NOT in the isolated Demo Mode dataset** (`assets/demo_dataset/safe/`, which was built later from a separately reviewed COCO pool + one new master-library image) — the isolated demo set is not affected by this issue. It only affects the production/master library path (`camera_demo_mode = False`).

3. **Indoor-building imagery is almost entirely absent from the training corpus.** A read-only dataset assessment found the 12,545-image training set is ~85% outdoor (wildland fires, industrial exteriors, vehicles). Near-zero imagery exists for any indoor environment — kitchens, offices, hospitals, malls, schools, hotels, corridors, electrical/server rooms, basements, stairwells. This is the confirmed **primary bottleneck** for any further model improvement; see Next Priority.

4. **Indoor smoke is weak for the same reason as #3** — smoke has the lowest recall of the three classes (0.448) and almost all smoke examples in the corpus are outdoor/wildfire smoke, not the denser, more confined smoke plumes typical of an indoor structure fire.

5. **Fire+person co-occurrence is underrepresented.** The fire source (Figshare) has no person labels and the person source (COCO) has no fire — there are essentially no training examples of "a person near/in a fire," which is one of the most operationally important cases for this application. The master library's `fire_person`/`fire_smoke_person` category folders exist but are empty; the simulator's fallback chain covers this today, not real imagery.

6. **D-Fire dataset (21,527 images) is not merged.** It requires a manual, login-gated download. A prior analysis found it would **not** close the indoor-imagery gap (D-Fire itself is described as "mostly outdoor and surveillance viewpoints" in its own manifest notes) — safe to keep deferring independently of the indoor-dataset work in Next Priority, but it would still add ~9,800 additional negative (safe) examples if merged.

7. **165 "Manual Review" curation images have not been individually adjudicated.** They sit in `assets/simulation_dataset/_curation/manual_review/` pending a human decision — sample-staged, not individually opened.

8. **One flagged special case:** `assets/simulation_dataset/_curation/manual_review/special_case_needs_decision/` holds the dataset's one genuine kitchen-fire photo, originally mis-tiered as a "letterboxing example." Needs a decision: promote as-is, crop the black letterbox bars first, or leave in review.

9. **Pre-existing backend bug, deliberately not fixed:** the mission-restart path in `backend/api/routes.py` replaces `app.state.adapter` without stopping the old one (and `/mission/end` doesn't stop it either). Ending a mission mid-run and immediately restarting lets the old runner's frames interleave into the new mission until its BFS finishes. Harmless under normal natural mission endings; only manifests under forced end→immediate-restart.

10. **Trained model weights (`.pt` checkpoints and `.onnx` exports) are gitignored and were never pushed to GitHub.** This is by long-standing project convention (`ai/*/models/{checkpoints,exports}/*` in `.gitignore`), not something introduced or changed this session. See the Migration Report's reproducibility caveat.

11. **`npm audit` flags a dev-only esbuild/vite/vitest dependency chain** (GHSA-67mh-4wv8-2f99). Fixing it requires a breaking Vite upgrade; the user has not decided whether to take it. No runtime/production exposure.

12. Minor, low-priority, long-standing: no responsive layout below ~1400px width; replay has no scrubbing controls; `wsStatus` is a string union rather than an enum.

---

# ==================================================
# NEXT PRIORITY
# ==================================================

**Do not retrain the model as the first step.** Training has already converged on the existing dataset (see Latest Model). The confirmed bottleneck is dataset composition, not model iteration. The required order is:

### Phase 1 — Collect high-quality REAL indoor-building fire images
Kitchens, offices, warehousing interiors, hospitals, schools, shopping malls, hotels, corridors, electrical rooms, server rooms, basements, stairwells. Must be real photographs — no toy/miniature models, no watermarks, no collages, no synthetic/AI-generated images (except the three pre-existing, explicitly grandfathered `Gemini_Generated_Image_*` placeholders already documented in `assets/simulation_dataset/README.md`).

### Phase 2 — Collect indoor smoke
Same environments as Phase 1, focused on dense, confined-space smoke rather than outdoor/wildfire smoke plumes.

### Phase 3 — Collect indoor victims
People in indoor hazard scenes — this is the category with the least existing co-occurrence data (see Known Issue #5).

### Phase 4 — Collect indoor safe negatives
True negative examples (no fire, no smoke, no person) set indoors, across the same environment list, to teach the model what a normal indoor scene looks like.

### Phase 5 — Collect hard negatives
Animals, statues, mannequins, reflections, posters/photographs-of-people-on-walls, and similar look-alike-but-not-a-person or look-alike-but-not-fire subjects. This directly targets Known Issue #1 (animal→person misclassification) — the corpus currently has **zero** images of this kind.

**Only after Phases 1–5 are curated and organized under Architecture A (Category → Scene — the sole, finally-decided filesystem standard; do not build an Environment-first structure, see Current State) should retraining happen**, following the same GPU training pattern used in AI.1 (in-memory config overrides, new timestamped run directory, never touch the existing checkpoints). After retraining: benchmark against `firerescue-detector-20260705-064246` using the identical evaluation methodology (same split, P/R/mAP50/mAP50-95 overall and per-class, confusion matrix, inference speed), then perform a full live end-to-end validation before declaring anything ready.

In the same pass as Phases 1–5, also address: removing/replacing the two mislabeled Safe images (Known Issue #2) in the production master library, and deciding on the flagged kitchen-fire special case (Known Issue #8).

Secondary, lower-priority items that remain valid but are **not** blocking: D-Fire merge, the pending `npm audit` Vite upgrade decision, 165 Manual Review image adjudication, deciding whether to flip the committed default detector from `ground_truth` to `yolo`.

---

# ==================================================
# SETUP GUIDE
# ==================================================

Complete instructions for a brand-new machine, using **only what is in GitHub**.

### Prerequisites
- Python 3.12+
- Node.js 18+
- Git
- (Optional, for AI training/inference at real speed) an NVIDIA GPU + CUDA-capable PyTorch build

### 1. Clone the repository

```bash
git clone https://github.com/asaad-cs/FireRescue-AI.git
cd FireRescue-AI
```

### 2. Backend — virtual environment and dependencies

```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

pip install -r requirements.txt
```

### 3. Frontend dependencies

```bash
cd frontend
npm install
cd ..
```

### 4. (Optional) AI workspace dependencies

Only needed if you intend to train or run the YOLO detector (as opposed to the default `ground_truth` detector, which needs none of this):

```bash
pip install -r ai/requirements.txt
```

This installs `ultralytics`, `torch`, `torchvision`, `onnxruntime`, `opencv-python`, and related packages. For GPU training, install a CUDA-matched `torch`/`torchvision` build separately (see [pytorch.org](https://pytorch.org)) — the plain `pip install` from `ai/requirements.txt` gives you CPU-only PyTorch.

### 5. Model download / location — IMPORTANT

**No trained model weights are in this GitHub repository.** `ai/object_detection/models/checkpoints/` and `ai/object_detection/models/exports/` are gitignored by design (project convention since Phase 8B). A fresh clone has an empty (or `.gitkeep`-only) `exports/` directory. You have two options:

- **Option A — retrain from scratch:** run the dataset pipeline, then training (see below). This reproduces the pipeline exactly but requires re-downloading the raw source datasets and several hours of training.
- **Option B — copy the model file(s) from the original machine out-of-band** (e.g. USB drive, cloud storage, direct file transfer) into `ai/object_detection/models/exports/`. The known-good file from this session is `firerescue-detector-20260705-064246-best.onnx`. This is the fast path if you just want the app running with AI vision.

Without either option, `perception_detector = "yolo"` will run with no model found and gracefully degrade to `UNOBSERVED` for every frame — it will not crash, but it also won't detect anything.

To reproduce the dataset + retrain from scratch:
```bash
python -m ai.object_detection.data_tools.download     # auto-downloads Figshare + COCO sources
python -m ai.object_detection.data_tools.pipeline      # merge → validate → scene-aware split → build
python -m ai.object_detection.training.train           # trains per configs/*.yaml (fails fast if data is missing)
python -m ai.object_detection.training.evaluate        # reports P/R/mAP50/mAP50-95 on the newest checkpoint
```
D-Fire (21,527 images) requires a manual, login-gated download — see `ai/object_detection/docs/download_instructions.md`. The pipeline works without it (it just skips the missing source).

### 6. Populate the simulated camera's runtime image folder

The simulator reads from `simulation/camera/images/` — a **generated, gitignored** folder. It is rebuilt from the tracked master library:

```bash
python -m ai.object_detection.data_tools.export_simulation_library
```

(`assets/simulation_dataset/` — the master library — and `assets/demo_dataset/` — the Demo Mode library — ARE both tracked in git, so this step works immediately after cloning with no downloads needed.)

### 7. Run the backend

```bash
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --ws websockets
```

The mission auto-starts (Warehouse Alpha scenario, `ground_truth` detector, Production Mode) on launch.

### 8. Run the frontend

```bash
cd frontend
npm run dev
```

Open `http://localhost:5173`. It proxies `/api/*` and `/ws` to `http://localhost:8000` automatically.

### 9. Enable Demo Mode

Edit `backend/config/settings.py`:
```python
camera_demo_mode: bool = True
```
This swaps the camera's image source to the smaller, curated, non-repetitive `assets/demo_dataset/` set. No other file needs to change. Restart the backend to pick up the change.

### 10. Switch between Ground Truth and YOLO detection

Edit `backend/config/settings.py`:
```python
perception_detector: str = "yolo"   # or "ground_truth" (the committed default)
```
Both detectors are always registered — this is a config-only switch, no code changes needed. If switching to `"yolo"`, make sure a model file is present per step 5 above. Restart the backend to pick up the change.

### 11. Run the test suites (do this before any commit — see Instructions for Future AI Agents)

```bash
python -m pytest                        # Backend: expect 623 passed + 50 subtests
cd frontend && npx vitest run           # Frontend: expect 334 passed
cd frontend && npx tsc --noEmit         # TypeScript: expect 0 errors
```

---

# ==================================================
# INSTRUCTIONS FOR FUTURE AI AGENTS
# ==================================================

### Architecture decisions that must never change

1. **The frontend receives only `MissionState`** over the WebSocket. Never send `Frame`, `PerceptionResult`, `ZoneHistory`, or any other internal backend type to the frontend.
2. **`backend/ingestion/interface.py` (`DataSource`) is the only hardware boundary.** Any future real-hardware integration replaces the adapter, not anything upstream.
3. **`MissionManager` is the single source of truth.** No component computes mission state independently — everything derives from `manager.get_state()`.
4. **Dashboard components are pure UI** — they receive props from layout components and never read the Zustand store directly.
5. **Any CSS property derived from a runtime value must use an inline `style={{}}`, not a dynamic Tailwind `className`** — Tailwind purges class names that don't appear as literal strings in source.
6. **`SCENARIO_REGISTRY` stores factory functions, never cached instances** — every `get_scenario(key)` call must return a fresh `Scenario`.
7. **Architecture A (Category → Scene) is the sole, finally-decided dataset filesystem standard.** Do not reintroduce an Environment-first folder structure — this was tried, found to silently break the export tool's category scan, and explicitly reversed (see Current State).
8. **Detector switching is config-only** (`settings.perception_detector`), and **Demo Mode is a single isolated flag** (`settings.camera_demo_mode`). Do not add a second mechanism for either — extend the existing one.
9. **`ground_truth` remains the committed default detector.** Flipping the default to `yolo` is a pending decision for a human, not something to change unilaterally.

### Protected components — modify only through documented seams, with full test coverage

- `simulation/` (all files) — building, drone BFS, sensors, scenarios
- `perception/` (all files) — engine, detectors, registry
- `backend/models/` — any change requires a matching update to `frontend/src/types/mission.ts`
- `backend/mission/manager.py` — the core state machine
- `backend/websocket/broadcaster.py`
- `backend/ingestion/interface.py`, `sim_adapter.py`
- `frontend/src/types/mission.ts`, `frontend/src/stores/missionStore.ts`, `frontend/src/services/websocket.ts`, `frontend/src/hooks/useWebSocket.ts`

All prior extensions to these areas (Phases 8E–8K) were small, additive, explicitly user-authorized changes — new optional fields, new files, a few-line conditional — never a rewrite. Follow that pattern.

### Files that should rarely be modified

- `.gitignore` — only to add narrowly-scoped entries for genuinely new generated-artifact patterns (as this session did for two stray Ultralytics output paths). Never remove existing entries without understanding why they're there.
- `backend/config/settings.py` — additive fields only; never repurpose an existing field's meaning.
- `ai/object_detection/configs/*.yaml` — the committed training defaults. Experiment via in-memory overrides in a throwaway script (as Phase AI.1 did), not by editing these files, unless the user explicitly asks for a new committed default.

### Coding style

- Lazy-import heavy ML dependencies (`ultralytics`, `torch`) inside functions, never at module top level — config validation and most tests must run without the ML stack installed.
- No hardcoded paths — derive everything from `Path(__file__)`.
- Fail fast with clear errors (`ConfigError` naming the missing file/field) rather than silently defaulting.
- Detectors must never raise — degrade to `UNOBSERVED` on any problem (missing model, bad input channel, runtime error).
- Comments are rare and short — only where a non-obvious constraint or workaround needs explaining, never to restate what the code already says.

### Testing procedure before every commit

```bash
python -m pytest                        # must show 623 passed + 50 subtests (or more, if you added tests)
cd frontend && npx vitest run           # must show 334 passed (or more)
cd frontend && npx tsc --noEmit         # must show 0 errors
```
All three must be clean before committing. Never weaken an existing test to make it pass — strengthen or add tests instead.

### Validation procedure before merging/committing changes

1. Run the full test suite above.
2. If you touched anything under `simulation/`, `perception/`, `backend/mission/`, `backend/models/`, or the WebSocket/REST contracts, manually launch the backend + frontend and drive at least one full mission end-to-end (see Setup Guide steps 7–8) — tests verify correctness, not necessarily that the live feature actually works end-to-end.
3. Run `git status` and review every file about to be staged — do not blanket `git add -A` without checking the list first. Watch specifically for stray generated artifacts (this session found an accidental `runs/` folder and a `yolo26n.pt` file at the repo root, neither part of any documented pipeline step — always sanity-check that new untracked files are ones you intended).
4. **Stop after each logical phase and wait for user instruction** — this has been the standing rule for the entire project and applies to you too. Do not chain multiple phases of work into one unreviewed change.
5. Do not retrain the model, download new datasets, or restructure the dataset filesystem without an explicit user instruction to do so — see Next Priority for the one exception (the indoor-dataset work), and even that is phased and should be checked in with the user between phases.

---

# ==================================================
# MIGRATION REPORT
# ==================================================

**Date:** 2026-07-05
**Task:** Project freeze + GitHub migration (documentation-only session; no feature/model/architecture changes)

### Commit / push status

| Item | Value |
|---|---|
| Checkpoint commit hash | `0861ff0` |
| Commit message | `Checkpoint: Demo-ready architecture + AI v2 baseline` |
| Branch | `main` |
| Remote | `https://github.com/asaad-cs/FireRescue-AI.git` |
| Push result | Success — `c5edef9..0861ff0 main -> main` |
| Tags pushed this session | `v2.0-phase-8c`, `v2.0-phase-8f`, `v2.0-phase-8i1`, `v2.0-phase-8j` (previously local-only; `v1.0.0` was already on the remote) |
| Files changed in the checkpoint commit | 451 files (437 additions, 14 modifications), +1617/-108 lines |

### Repository status (verified)

- `git status` → clean, "nothing to commit, working tree clean"
- `git rev-parse main` == `git rev-parse origin/main` → identical SHA (`0861ff0...`)
- `git branch -vv` → `main` tracks `origin/main`, zero ahead/behind
- `git branch -r --contains 0861ff0` → confirmed present on `origin/main`
- No untracked work remains
- Full backend suite: **623 passed + 50 subtests** (verified immediately before committing)
- Full frontend suite: **334 passed**, TypeScript: **0 errors** (verified immediately before committing)

### Generated-artifact hygiene

Before committing, a stray `runs/` directory (Ultralytics validation output — confusion matrices, PR curves — at the repo root) and a stray `yolo26n.pt` file (an auto-downloaded weight for a model architecture never used by this project) were found untracked. Neither is produced by any documented pipeline step (`evaluate.py` does not write to `runs/`). They were **not committed**; two narrowly-scoped `.gitignore` entries (`/runs/`, `yolo26*.pt`) were added so they won't be accidentally staged in the future. The files themselves were left on disk untouched — nothing was deleted.

### Required project files — verified present and tracked

`requirements.txt`, `ai/requirements.txt`, `frontend/package.json`, `backend/config/settings.py`, `backend/main.py`, `simulation/camera/simulation_camera.yaml`, all three `ai/object_detection/configs/*.yaml`, `assets/simulation_dataset/README.md`, `docs/session-context.md` — all confirmed tracked via `git ls-files`. No dataset `raw/`/`processed`/`merged` directories or model `checkpoints/`/`exports/` directories were accidentally committed (only their `.gitkeep` placeholders remain tracked, as intended).

### Reproducibility caveat — read before assuming "clone and go"

**A fresh clone of GitHub alone reproduces the entire codebase, all documentation, the full simulation image libraries (master + demo, both tracked), and the dataset pipeline reports — but NOT the trained model weights.** `ai/object_detection/models/{checkpoints,exports}/` are gitignored by long-standing project convention (predates this session) and were never pushed. Anyone continuing this project on a new machine must either retrain from scratch (hours of GPU time + the dataset download steps in the Setup Guide) or receive the `.onnx`/`.pt` files through an out-of-band transfer. This was not introduced by this session and was not something this task was authorized to change (it would mean committing large binary model files, a real architectural/workflow decision) — it is reported here, not fixed, per this task's explicit instruction to report rather than implement anything discovered missing.

### Remaining TODOs (none started or implemented this session)

- Curate a real, high-quality indoor-building dataset — Phases 1–5 in Next Priority (highest priority; do not retrain before this)
- Retrain, benchmark, and re-validate only after the above (Next Priority Phases continuing beyond 5)
- Replace/remove the 2 mislabeled Safe images in the production master library (Known Issue #2)
- Decide on the flagged kitchen-fire special case (Known Issue #8)
- Adjudicate the 165 "Manual Review" curation images (Known Issue #7)
- Decide whether to merge D-Fire (Known Issue #6) — independently valid, not blocking
- Decide whether to flip the committed default detector to `"yolo"` (currently `"ground_truth"`)
- Decide on the `npm audit` dev-dependency Vite upgrade (Known Issue #11)
- Fix the pre-existing mission-restart adapter-leak bug if it ever becomes practically relevant (Known Issue #9)
- Get the trained `.onnx` model file(s) onto any new development machine out-of-band, or retrain (see Reproducibility caveat above)

### Confirmation

Another machine can clone `https://github.com/asaad-cs/FireRescue-AI` (branch `main`, commit `0861ff0`) and, by following the Setup Guide above, run the full simulation + backend + frontend + Demo Mode experience immediately (all required assets are tracked in git). Running AI vision (`perception_detector = "yolo"`) additionally requires either retraining or obtaining the model file out-of-band, as documented in the caveat above — this is the one gap between "clone from GitHub" and "fully identical to this machine's current running state."
