# FireRescue AI — Future Session Context

> Paste this document at the start of any new AI session to provide complete project context without reading the repository. Last updated: 2026-07-04, end of Phase 8K (camera experience + live camera monitor) — implemented and verified, NOT yet committed (awaiting user approval).

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

**Git state (2026-07-04, post-Phase-8K):** branch `main`; HEAD = annotated tag `v2.0-phase-8j`; **working tree carries the UNCOMMITTED Phase 8K changes** (see the Phase 8K section + `docs/phase-8k-report.md`) pending user approval of a checkpoint commit. Pre-8K state: HEAD = annotated tag `v2.0-phase-8j` (Phase 8J scene-aware split checkpoint, tests verified green — 609 BE + 50 subtests — immediately before committing); earlier checkpoints `fe9fc19` = `v2.0-phase-8i1` (Phases 8G/8H/8I.1), `68fcc6f` = `v2.0-phase-8f`, `09f9388` = `v2.0-phase-8c`; all after MVP `c5edef9` (`v1.0.0`). Working tree clean. NOTHING beyond `v1.0.0` pushed to GitHub — all V2 commits and tags are local only. Generated data (raw downloads, merged/, processed/, checkpoints, exports, simulation/camera/images/) is gitignored — only code, configs, docs, tests, and reports are tracked. `assets/simulation_dataset/` (50 images, ~4 MB) IS tracked in git per user decision (2026-07-03) — the master library is reproducible from a fresh clone.

---

## MVP v1.0.0 — Frozen

The MVP is complete and frozen. All 286 MVP backend tests and `tsc --noEmit` (0 errors) pass unchanged. Never modify frozen MVP logic without explicit user instruction. Exceptions made so far, each explicitly user-authorized through documented seams:
- **8E/8F:** additive settings fields, detector registration in `backend/main.py`, two-line adapter swap in `main.py` + `routes.py`, plus NEW files (`perception/detectors/yolo.py`, `simulation/camera/`, `backend/ingestion/camera_adapter.py`).
- **8G:** additive `vision` field on `MissionState` (+ `VisionFrame`/`VisionDetection` models), an 8-line merge in `MissionManager`, one metadata pass-through line in `perception/engine.py`, mirrored `frontend/src/types/mission.ts` (the documented paired change).
- **8I.1 (frontend-only, user-directed redesign):** new `MissionCamera`/`DetectionCards`/`MissionOpsPanel` components, restyled `TacticalMap`/`AlertPanel`/`MissionTimeline`, restructured `MainWorkspace`/`RightSidebar`.
REST and WebSocket contracts remain untouched throughout; the frontend still receives ONLY `MissionState`. All 295 original frontend tests still pass unmodified.

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
- **Result:** datasets/processed/ holds 12,545 images / 32,783 boxes (fire 12,043, smoke 9,963, person 10,777), validated CLEAN (0 errors; 1,169 byte-identical duplicates removed at merge). Original per-image split 8,781/2,509/1,255 was superseded by the Phase 8J scene-aware split (8,783/2,515/1,247). Reports in `datasets/reports/` (dataset_report.json/md, merge/split/quality_report.md — tracked in git). Raw/merged/processed data itself is gitignored; the pipeline skips missing sources and absorbs D-Fire automatically once it lands in `raw/dfire/`.

### Phase 8D — First training run (complete, 2026-07-03, smoke test)
Trained yolov8n for 5 epochs (in-memory override of the committed 50; configs untouched) on CPU (~4h15m — torch is CPU-only; the machine's RTX 3060 Ti is unused until a CUDA torch build is installed). Run `firerescue-detector-20260703-003931` under `models/checkpoints/` (gitignored): best.pt/last.pt, results.csv, TensorBoard logs, curves, evaluation/ artifacts. **Val metrics (standard protocol): P 0.621 / R 0.458 / mAP50 0.509 / mAP50-95 0.270** — still climbing at epoch 5, far from converged. ONNX export verified (11.7 MB, opset 20, `images [1,3,640,640]` → `[1,7,8400]`) and copied to `models/exports/`. Full report: `ai/object_detection/models/reports/training_report.md` (tracked).

### Phase 8E — YOLO integration (complete, 2026-07-03)
`perception/detectors/yolo.py`: `YOLODetector(AbstractDetector)` runs the exported ONNX via onnxruntime — letterbox preprocess, decode, confidence filter, class-aware numpy NMS, mapping to DetectionResult (fire→HazardSignal HIGH/CRITICAL, smoke→LOW/MODERATE, person→VictimSignal "unknown"). Registered in `backend/main.py` alongside `ground_truth`; selection via `settings.perception_detector` (**default is still "ground_truth"**); `yolo_*` settings hold thresholds + model location (newest export auto-discovered). Never raises: missing model/runtime/rgb-channel → graceful UNOBSERVED. 40 tests (mocked ORT + real-model integration test).

### Phase 8F — Simulated camera (complete, 2026-07-03)
`simulation/camera/` (provider.py + simulation_camera.yaml): zones map to folders of real photographs by scenario hazard level + victim presence (+ per-zone overrides), with seeded deterministic random selection, LRU cache, and fallback chain. `backend/ingestion/camera_adapter.py`: `CameraSimAdapter` DataSource-decorator attaches `frame.channels["rgb"]`; `make_data_source()` used by main.py AND the routes.py restart path. Controlled by `settings.camera_enabled` / `camera_config_path`; any problem degrades to plain SimAdapter. Populate the (gitignored) image library with `python -m ai.object_detection.data_tools.export_sim_images`. Live-verified: with `perception_detector="yolo"` the model detected the warehouse victim at 0.85 from an actual image. 34 tests.

### Phase 8G — Live AI Vision dashboard (complete 2026-07-03, committed `v2.0-phase-8i1`)
The operator sees what the AI sees. `YOLODetector` adds a `vision` payload (base64-JPEG of the exact analysed image + detections + inference ms + model facts) to `DetectionResult.metadata`; the engine passes metadata through; `MissionManager` lifts it into the new optional `MissionState.vision` (`VisionFrame` model). The image travels INSIDE MissionState, so replay and history work for free and no inference ever runs twice. GroundTruth mode → `vision: null` → dashboard fallback. Per-frame cost: one JPEG encode (~5 ms), ~60–120 KB per WS push. 10 backend tests (`backend/tests/test_vision_state.py`).

### Phase 8H — Permanent simulation image library (complete 2026-07-03, committed `v2.0-phase-8i1`)
`assets/simulation_dataset/` is the permanent master library (categories × scene sub-folders per its README; 50 dataset-sourced images seeded into `dataset/` sub-folders). `simulation/camera/images/` is now a GENERATED runtime folder, rebuilt via `python -m ai.object_detection.data_tools.export_simulation_library` (`--categories --subcategories --limit --random --seed --overwrite --clean`). Regeneration proven content-exact against the runtime folder; runtime folder byte-identical after the phase (zero behavior change). 17 tests.

### Phase 8I.1 — Professional dashboard UX redesign (complete 2026-07-03, committed `v2.0-phase-8i1`, frontend-only)
Emergency-operations-center layout: **`MissionCamera`** is the primary element, built on a `CameraMediaSource` abstraction (`image` today; `video`/`stream` kinds typed + reserved so future video needs only the `CameraMedia` switch — a deliberate video-first design decision). `DetectionCards` (🔥/🌫/👤 status cards), `MissionOpsPanel` (status, timer, rooms scanned/remaining, victims, hazards, detector/model/inference/camera source), enlarged glowing tactical map with explored-progress track, alert cards with level accent bars, polished timeline (visually ready for future replay controls). `AIVisionPanel` from 8G was superseded and removed; all its capabilities and tests were ported to `MissionCamera`. All 295 original frontend tests pass unmodified; 24 new component tests.

### Phase 8J — Scene-aware dataset split (complete 2026-07-04, committed `v2.0-phase-8j`)
Fixed the audit's 🔴 finding 1 (near-duplicate split leakage). `data_tools/split.py` now assigns whole **scenes** — merged file names with the Roboflow `.rf.<32-hex>` export suffix stripped — instead of single images, stratified by dominant class signature, deterministic under seed 42; `splits.json` records `method: "scene"` + scene stats. Dataset regenerated via the full pipeline: **8,783 / 2,515 / 1,247** (70.0/20.0/9.9%), 12,545 images unchanged, validator CLEAN. Verified independently: **0 scenes span splits** (9,956 scenes, 1,061 multi-image, largest 22); class-share spread across splits ≤ 0.56%; residual exact-dHash overlap with train fell **16.9% → 8.0% (val)** and **15.6% → 6.2% (test)** — the remainder are cross-name near-duplicates (video frames/re-uploads), fixable later via dHash-cluster grouping or pruning. **Phase 8D metrics (mAP50 0.509) were measured on the old split and are NOT comparable to anything evaluated on the new one.** +4 tests in `tests/test_split.py` (16 total). Reports: `datasets/reports/split_fix_2026-07-04.md` (technical report) + addendum in `dataset_audit_2026-07-03.md`. Post-fix, the full system was launch-verified end-to-end (YOLO detector, camera, live vision on the dashboard).

### Phase 8K — Camera experience + live camera monitor (complete 2026-07-04, NOT yet committed)
Fixed known issues 1–3 without touching architecture, model, dataset, replay, or APIs. Full detail: `docs/phase-8k-report.md`.
- **Mission-scoped no-repeat pool** (`simulation/camera/provider.py`): with randomize on, an image is never reused within a mission until its category folder is exhausted (then the pool recycles, logged); pools are keyed by the folder actually served so fallback categories share them; zones keep their first-assigned image on revisits. The provider is built per mission, so the state is mission-scoped by construction.
- **Selection modes:** `CameraConfig.seed` is now `Optional[int]` — `randomize: false` (fixed first image), `seed: <int>` (deterministic mission), `seed: null` (**new committed default**: fresh 63-bit entropy seed per mission, exposed as `provider.effective_seed` and logged, so any mission is reproducible after the fact by pinning that seed).
- **MissionCamera → live camera monitor** (frontend-only): stage HUD (corner brackets, zone + UTC clock, frame counter, feed identity, scanlines/vignette, frame fade-in), edge-aware detection labels (flip inside near the top edge, right-align near the right edge — fixes the label-overflow known issue), link-state awareness via new optional `wsStatus`/`isStale` props (LIVE / STALE + on-stage chip / ACQUIRING SIGNAL / no-inference STANDBY as four distinct states), telemetry adds Targets + Link fields, header adds a contacts chip, history thumbnails add class-colored dots. `CameraMediaSource` abstraction untouched — video/stream remain typed, reserved, unimplemented.
- **Tests:** +10 backend (pool/modes/reproducibility) → 619 (+50 subtests); +15 frontend → 334; every pre-8K test passes unmodified; tsc 0 errors. Verified live end-to-end (two missions, distinct effective seeds, different imagery, fire 0.92 in the Loading Dock over WebSocket) and by script against the committed config (no repeats until exhaustion; 10/20 zones differed between missions; seeded + logged-seed reproduction exact).
- **8K.1 UX fix pass** (after full visual verification with screenshots in `Desktop\firerescue-8k-screenshots\`): (1) history rail is mission-scoped — clears on `mission_id` change via new optional `missionId` prop; (2) replay awareness — new optional `isReplaying` prop shows a blue REPLAY badge instead of LIVE and freezes history recording during replay; (3) HUD chips moved into dedicated top/bottom bands outside the image area, structurally eliminating HUD/detection-label overlap. All frontend-only. **Discovered pre-existing backend issue (NOT fixed, out of scope):** the restart path in `backend/api/routes.py` never stops the old adapter (and `/mission/end` doesn't either), so ending a mission mid-run and restarting lets the old runner's frames interleave into the new mission until its BFS completes; invisible in normal natural-end operation. Fix later: stop the old adapter in the restart path.

### Phase 9A/9B/10 — Simulation Library gap analysis + curation (2026-07-04/05, PARTIALLY IN REPO)

Full detail: `ai/object_detection/datasets/reports/phase9b_promotion_manifest_2026-07-05.md`.
Status framework below separates what is done from what is only planned or deliberately postponed.

**COMPLETED**

- **Phase 9A — Dataset assessment (read-only).** Exhaustive review of the 12,545-image training set as a candidate simulation-image source. Verified: ~85% outdoor (wildland/industrial/vehicle) content; near-zero building-interior imagery for any named environment at first pass; source provenance confirmed exact (9,852 `figshare_fire_smoke__*` + 2,693 `coco_person__*` = 12,545, D-Fire still absent — `dfire__*` count = 0).
- **Phase 9B — Curation staging.** A follow-up exhaustive filename search (not just random sampling) found a previously-missed real cluster: 58 residential house-fire images (`case2_house`×32, `Ogdenhousefire`×18, `WELLInvolvedHouseFireAggressiveAttack`×6, `Insideaburninghouse`×2) and 18 indoor-training-facility images (`FlashoverDemonstration`×8, `WaterMistFireDemonstration`×8, `Firefighterhelmetcaminteriorattack`×1, `hotel-fire`×1) — plus a 49-image trap (`HouseOne`/`HouseTwo`/`HouseFive`: miniature/craft-model house fires that look convincing at a glance, visually confirmed as toy models, not real structures). 235 files staged to a session scratchpad (outside the repo) with a written classification.
- **Phase 9B Promotion (roadmap step 10A.4).** 234 unique images (235 staged copies, minus 1 duplicate file counted once) promoted from the scratchpad into `assets/simulation_dataset/_curation/{approved,manual_review,rejected}/` — a new subtree, invisible to `export_simulation_library.py` by construction (its category scan skips `_`/`.`-prefixed dirs, `export_simulation_library.py:99-101`), so the runtime pipeline and `simulation/camera/images/` are completely unaffected (re-verified independently afterward: runtime folder file count/listing unchanged, zero diff growth in `provider.py`/`camera_adapter.py`/`simulation_camera.yaml` beyond pre-existing Phase 8K changes). Breakdown: **14 Approved** (individually visually confirmed this session, no defect), **165 Manual Review** (pattern/sample-staged, not individually opened, or flagged for a judgment call), **55 Rejected** (confirmed toy-model/watermark/duplicate/collage defects — preserved, not deleted). Zero overwrites of pre-existing assets (filename collision check run before copying).
- **Design-existence audit (Phase 10).** Confirmed, by exhaustive repo-wide search (no `phase9*`/`phase10*` files, no "Simulation Library" design doc, git log checked), that no prior Simulation Library architecture document exists beyond `assets/simulation_dataset/README.md`. That README's hazard taxonomy and licensing sections are complete and correct; its environment-category list, target image counts, and acceptance rules are partial or absent. Recommendation delivered: extend, don't replace.
- **Architectural Review (read-only, separate from the design-existence audit above).** Full component-responsibility inventory of the simulation stack: `Scenario`/`Building`/`Zone` (`simulation/scenarios.py`, `simulation/environment.py`), `SimulationRunner`, `MissionManager`, `Pipeline`/`Enricher`, `ZoneCategoryResolver`/`ZoneImageProvider` (`simulation/camera/provider.py`), `CameraSimAdapter` (`backend/ingestion/camera_adapter.py`), `export_simulation_library.py`, `DataSource`, `Frame`/`MissionState`/`VisionFrame`. Confirmed: image selection is hazard-category-only (`ZoneCategoryResolver.category_for()`, `provider.py:163-176`, has no scene/environment parameter); `Frame.channels` and `Frame.metadata` are both genuine, already-used open extension points (`zone_label` already flows `Zone.label` → `frame.metadata` → `MissionState` via `runner.py:150`/`manager.py:204` — a working precedent for a future environment tag); a full dependency graph (Scenario → Building/Zone → Frame → Pipeline → MissionManager → MissionState → Frontend, with the camera branch's narrower Scenario→hazard-only extraction) was produced.
- A **Scene-Aware Simulation Architecture design document** was subsequently produced (chat-only, not persisted to a repo file) covering environment modeling, selection-strategy fallback order, compatibility analysis, and a phased migration plan — **awaiting your approval; no implementation from it exists anywhere.**

**IN PROGRESS**

- Nothing is actively in progress on this thread as of this entry. Work proceeds in discrete, user-approved steps; the next step has not yet been authorized.

**PENDING** (defined, not started)

- Roadmap steps 10A.2 (add target image counts + expanded acceptance rules to `assets/simulation_dataset/README.md`), 10A.3 (create the still-missing environment folders — Warehouse, Office, Hospital, Shopping Mall, School, Hotel, Airport, Parking Garage — and promote reviewed survivors into the live, exported library), and 10A.5 (sourcing-strategy decision for environments that remain empty).
- Human/manual adjudication of the 165 Manual Review images (not individually opened this session).
- A decision on the flagged special case: `manual_review/special_case_needs_decision/` holds the dataset's one genuine kitchen-fire photo, mis-tiered in the original Phase 9B pass as a "letterboxing example" rather than approved content — promote as-is, crop the black bars first, or leave in review.
- Scene-aware implementation itself (the migration plan's phases) — contingent on approval of the design document above.

**DEFERRED** (explicitly decided against or postponed on purpose, not merely unstarted)

- **D-Fire download** — explicitly analyzed in Phase 9A and found NOT to close the building-scene gap (D-Fire is itself "mostly outdoor and surveillance viewpoints" per `dataset-manifest.md`); safe to postpone independently of any Simulation Library work, per that analysis.
- **New image sourcing or searching** — repeatedly and explicitly out of scope for every Phase 9B/promotion instruction so far; no new datasets were downloaded or searched for at any point.
- **Making the simulator scene-aware** — deliberately not done in the same pass as promotion, per explicit instruction, to keep the runtime pipeline provably untouched while curation work proceeded.

**Current dataset status (superseded further below — see AI.1):** 12,545 training images, D-Fire not merged. **Current curation status:** 234 images in-repo across Approved/Manual Review/Rejected tiers under `_curation/`. **Current runtime status:** `simulation/camera/images/` unchanged (50 files) throughout every phase below unless explicitly stated. **Current architectural status:** Architecture A (Category → Scene) is now the **sole, finally-decided** dataset filesystem standard — see Phase 10A.4/10B.1.

### Phase 10A.2 — Simulation Dataset Standard (2026-07-05, documentation only)

Extended `assets/simulation_dataset/README.md` additively (138 insertions, **0 deletions**): Target Library Structure (Tier 1 environment names, Tier 2 scene names), Target Image Counts (planning only, not yet met), Acceptance Rules (real photo, no watermark/collage/toy-model/synthetic — with the 3 pre-existing `Gemini_Generated_Image_*` placeholders explicitly grandfathered, not silently contradicted), Dataset Curation Workflow (Candidate → Manual Review → Approved → Runtime Library, Rejected as a preserved side-branch), Current Status. No code, no images touched.

### Phase 10A.3 — Build the (then-proposed) Architecture-B Folder Structure (2026-07-05, filesystem only — later reversed, see 10B.1)

Created 8 new top-level "environment" folders (`warehouse/office/hospital/shopping_mall/school/residential/industrial/outdoor`) plus 35 Tier-2 scene subfolders (`corridor/kitchen/electrical/parking/stairs` under each of 7 environments), every one empty except a `.gitkeep`. Flagged an inconsistency: this task's example Tier-2 list (8 names incl. `lobby/storage/server_room`) exceeded the README's documented 5 — only the 5 documented names were created.

### Phase 10A.4 — Architectural Alignment Review: Architecture A vs B (2026-07-05, read-only)

Compared the pre-existing **Category → Scene** shape (Architecture A, e.g. `fire/warehouse/`, live since Phase 8H) against the **Environment → Scene** shape just built in 10A.3 (Architecture B). **Decisive finding:** `export_simulation_library.py`'s category-discovery treats any non-`_`/`.`-prefixed top-level folder as a hazard category to export — Architecture B's environment folders would be silently mis-scanned by the tool's own default (no-argument) invocation, and `ZoneCategoryResolver` would never query an "environment" category anyway, so curated images placed there could never reach the runtime. **FINAL DECISION: Adopt Architecture A.** A hybrid was explicitly rejected as unjustified — Architecture A's existing category/scene shape already represents environment names perfectly well (`fire/warehouse`, `fire/office` already exist), so a second axis would add cost with no representational gain.

### Phase 10B.1 — Migrate to Architecture A (2026-07-05, filesystem only)

Removed all 8 Architecture-B folders and their 35 subfolders (43 empty, never-committed directories — zero information lost, verified). `warehouse`/`office` were redundant with pre-existing Architecture-A locations; the other 6 environments (`hospital/shopping_mall/school/residential/industrial/outdoor`) have **no existing Architecture-A destination** and none was invented — that gap remains open, honestly unresolved, pending real content (see AI.1's conclusion and the Next Session Plan below). Architecture A confirmed as the **only** surviving dataset filesystem standard project-wide.

### Scene-Aware Simulation Architecture — Design Document (2026-07-05, produced in chat only, NOT implemented, NOT approved)

A full 12-section architecture design (goals, principles, two-tier Environment model, Scenario integration, runtime data flow, selection-strategy fallback chain, fallback philosophy, compatibility analysis, risks, future expansion, migration plan) was produced, recommending Environment flow through the *already-existing* `Scenario → make_data_source() → ZoneCategoryResolver` chain, mirroring the proven `zone_overrides`/`frame.metadata["zone_label"]` pattern. **No code was written or changed.** This remains a proposal awaiting approval — do not assume any part of it is implemented.

### Phase Demo.1 — Build a Demo Dataset (2026-07-05, curation only, new isolated directory)

Created `assets/demo_dataset/{fire,smoke,fire_smoke,person,safe}/` — flat, Architecture-A-shaped, **separate from both** the master library and `_curation/`. Initial composition (156 images): Fire 41, Smoke 30, Fire+Smoke 38, Person 45, Safe 2 (only the 2 true negatives in the whole 12,545-image training set existed at this point). Curated from `_curation/approved` + `_curation/manual_review` + fresh `coco_person` draws, with frame-burst thinning (e.g. `wildfire-video_mp4-*` and `hand_held_winnebago*` sequences) to maximize real visual diversity rather than near-duplicate frames. MD5-verified zero duplicates. Master library (77 files) and `_curation/` (234 files) confirmed unchanged.

### Phase Demo.2 — Demo Validation & Safe Integration (2026-07-05)

**Validated** all 156 demo images (0 errors/corrupt/zero-byte; decode-tested via the exact `cv2.imdecode(np.fromfile(...))` call `ZoneImageProvider._decode()` uses). **Implemented the smallest possible mode switch:** one new settings field, `camera_demo_mode: bool = False` (`backend/config/settings.py`), plus a ~7-line conditional inside `make_data_source()` (`backend/ingestion/camera_adapter.py`) that swaps `image_root` to `assets/demo_dataset` only when the flag is set — **zero changes** to `ZoneCategoryResolver`, `ZoneImageProvider`, `simulation_camera.yaml`, or `export_simulation_library.py`. Production Mode (`False`) is the unconditional default, verified against the real, unmocked `make_data_source()` function. Full backend suite: 619 passed, unmodified.

### Phase Demo.3 — End-to-End Demo Validation (2026-07-05, live system, not mocked)

Drove a complete Warehouse Alpha mission through the real WebSocket in Demo Mode + YOLO. Every lifecycle stage verified (start → camera init → frame acquisition → zone resolution → hazard/victim detection → MissionManager/MissionState updates → WS broadcast → natural `ENDED`). All 5 categories loaded successfully with zero repetition for Fire/Smoke/Fire+Smoke/Person (each hazard/victim zone is a single occurrence per mission); Safe (still only 2 images at this point) recycled ~6 times across ~13 draws — expected, matching the already-known scarcity. One pre-existing, Demo-Mode-unrelated cosmetic artifact found: the final frame is broadcast twice (once for the last tick, once for the `ENDED` transition). Zero crashes/exceptions. Readiness scored 92%, verdict **Demo Ready**.

### Phase Demo.4 — Fix the `ZoneImageProvider` Recycle-Boundary Repetition Gap (2026-07-05, minimal patch)

A read-only investigation found: on pool exhaustion, `_pick_unused()`'s `used.clear()` reopened the *entire* pool with no memory of the image that had just closed the previous cycle — allowing sequences like A, B, (recycle), A, visibly jarring with small pools (exactly the Safe category's 2-image case). **Fix:** added `self._last_shown: Dict[str, Path]` (one new field) tracking the most recent pick per folder; on recycle, that one file is excluded from the reopened pool **only when more than one file exists** (single-image categories are provably unaffected — a dedicated test confirms this). ~12 new lines total in `provider.py`, confined entirely to `_pick_unused()`; zero changes anywhere else. Added `TestRecycleBoundaryGuard` (4 new tests) to `simulation/tests/test_camera.py`. Full suite: **623 passed** (619 + 4), zero regressions.

### Phase Demo.5 — Expand the Safe Pool, Existing Assets Only (2026-07-05)

Exhaustive repo search found exactly **one** new usable Safe image anywhere: `assets/simulation_dataset/safe/dataset/cleanroom.jfif` (a real bedroom photo), copied into the demo set as `cleanroom.jpg` — the extension was corrected on the *copy only* because `.jfif` is not in `simulation_camera.yaml`'s accepted list (`.jpg/.jpeg/.png`) and would otherwise be silently invisible to the provider; the original file was never touched. **Critical finding, reported not silently fixed:** the 2 pre-existing "safe" images are visually **not** safe — one (`937...jpg`) shows an active wildfire with a fleeing bystander; the other (`H_00980...jpg`) shows a large smoke/steam plume. Both were only "negative" in the sense of an empty training-annotation file, never in the sense of visual content. (AI.1 later captured direct, live proof that `H_00980` is the exact recurring source of false-positive "smoke" detections.) Safe count: 2 → 3.

### Phase Demo.6 — Expand the Demo Dataset via the Raw COCO Pool (2026-07-05)

Discovered and mined a genuinely new, previously-unexamined source: `ai/object_detection/datasets/raw/coco_person/val2017/` — the full, unfiltered 5,000-image COCO val2017 set, of which only 2,693 ever passed the "person present" filter into the training set. The other **2,307 were excluded specifically for having no person** — a pool nobody had individually inspected. 59 were sampled and visually reviewed one by one; **45 qualified** (real photograph, no fire/smoke/person, no watermark, no toy/collage) and were copied into `assets/demo_dataset/safe/` (prefixed `coco_raw_unused__`); 14 were rejected with cause (4 watermarks, 3 incidental person/hand visible, 1 aerobatic smoke trail, 6 too object-focused or low quality). **Safe: 3 → 48** — went from the smallest demo category (by 15–20×) to the **largest**. MD5- and decode-validated, zero duplicates. Master library, `_curation/`, and the runtime folder confirmed unchanged throughout.

### Phase AI.1 — Baseline-Preserving Model Retrain + Full Validation (2026-07-05, GPU training + live system test)

**Established the true baseline** (never actually measured before): ran `evaluate.py` on the existing 5-epoch model against the already-corrected scene-aware split — **P 0.702 / R 0.450 / mAP50 0.3997 / mAP50-95 0.2255** — confirming Phase 8J's own prediction that the previously-cited 0.509 was leakage-inflated by ~11 points. Confusion matrix showed near-zero fire↔smoke cross-confusion (4 instances) but heavy missed-detection counts (fire 1,268 / smoke 1,297 / person 878 into "background").

**Trained a new model** on GPU (RTX 3060 Ti), via an in-memory override script — zero committed config files touched: epochs 50→60, batch 16→32, patience 10→15, `cos_lr` false→true; image size/optimizer/learning-rate/seed/augmentation left at the committed defaults (justified: ~79% of source images are already native 640×640, so upsizing gains nothing; augmentation left untuned absent evidence of a specific problem to fix). New run `firerescue-detector-20260705-064246`; the original checkpoint (`...20260703-003931`) was never touched.

**Results (best.pt, effectively converged by epoch ~57 of 60; patience-15 early stop never triggered because the last 10 epochs still inched forward by <0.005 mAP50-95):**

| Metric | Old (5 ep, CPU) | New (60 ep, GPU) |
|---|---:|---:|
| Precision / Recall (overall) | 0.702 / 0.450 | 0.685 / 0.528 |
| mAP50 / mAP50-95 (overall) | 0.3997 / 0.2255 | 0.601 / 0.334 |
| Fire P/R/AP50/AP50-95 | .723/.457/.416/.235 | .682/.542/.628/.335 |
| Smoke P/R/AP50/AP50-95 | .718/.324/.283/.139 | .674/.448/.534/.271 |
| Person P/R/AP50/AP50-95 | .664/.569/.501/.303 | .697/.594/.642/.396 |
| Inference speed | 2.4 ms/img | 1.2 ms/img |
| Training time | 2.53 h (5 epochs) | 2.43 h (60 epochs, ~12.5× faster/epoch) |

Exported to ONNX (opset 20) → `ai/object_detection/models/exports/firerescue-detector-20260705-064246-best.onnx`, auto-discovered as newest by the unmodified `YOLODetector`.

**Live-validated** across 7 complete Warehouse Alpha missions through the real backend + WebSocket (Demo Mode + the new model): fire detected 6/6 live opportunities; victims 11/12 (one miss, mission 2 zone `2_3_1`); 39 unexpected Safe-zone detections tracked across 6 missions, each one root-caused with a directly captured, personally-viewed image — **5 are genuine animal→person misclassifications** (two zebras 0.68, a dog 0.34, a bird 0.41, a horse+dog 0.30, two seagulls 0.47/0.27 — all low-confidence, all because **zero animal images exist anywhere in the 12,545-image training corpus**, so the model has never learned "animal ≠ person"), **2 are the exact same pre-existing mislabeled-Safe images from Demo.5** (`937`/`H_00980`, now with direct visual proof of the false detections they cause), and **1 is a single low-light instance** (a parking meter at dusk, person 0.47). Zero crashes or exceptions across all 7 missions; only legitimate `HAZARD_ELEVATED` application alerts, several spuriously triggered by the above.

**Verdict: B) Demo Ready with Minor Issues.** **Training has converged — more epochs on the same data are not expected to help further.** The bottleneck is now data quality, not model iteration.

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
│   ├── data_tools/             download · image_utils · labels · coco · sources · export_sim_images · export_simulation_library
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
Backend:    619 tests + 50 subtests   (python -m pytest)
            = 286 MVP + 222 AI + 40 YOLO integration + 44 camera
              + 10 vision-state + 17 library-export
Frontend:   334 tests / 17 files       (npx vitest run)
            = 295 original MVP (unmodified) + 39 component tests
              (24 Phase 8I.1 + 15 Phase 8K incl. the 8K.1 fixes)
TypeScript: 0 errors                   (npx tsc --noEmit)
```
(all three verified 2026-07-04, end of Phase 8K)

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
11. **CUDA torch installed 2026-07-03** (env-only change, zero project edits): torch 2.12.1+cu130 + torchvision 0.27.1+cu130 (driver 591.86, RTX 3060 Ti sm_86, cuDNN 9.20 bundled — no system CUDA toolkit needed or present). `torch.cuda.is_available()` True; `select_device('auto')` → `cuda`; verified with tensor test + real YOLODetector ONNX inference (48 ms). onnxruntime remains the CPU package and the detector pins CPUExecutionProvider by design — fine at 1 s ticks.
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
10. Person images come from COCO val2017 only (≈2,700); fire+person co-occurrence is under-represented (scale-up path documented in download_instructions.md); master-library person-combination folders (fire_person/ etc.) are empty and rely on the provider's fallback chain
11. ~~The deployed model is the 5-epoch smoke-test baseline~~ — **superseded by Phase AI.1**: a new 60-epoch GPU-trained model (`firerescue-detector-20260705-064246`) exists, live-validated, verdict "Demo Ready with Minor Issues" (true old-model baseline on the corrected split: mAP50 0.3997, not the previously-cited 0.509 which was leakage-inflated). The committed `perception_detector` default is still `ground_truth`; flipping it to make the new model live by default is a pending user decision. Residual cross-name near-duplicates remain (~8% val / ~6% test share an exact dHash with train) — unaffected by AI.1.
11a. **New (Phase AI.1): the model still confuses animals with people** — 5 concrete, low-confidence (<0.7) examples captured live (zebras, dog, bird, horse, seagulls) — root cause: zero animal images exist anywhere in the 12,545-image training corpus, so the model has never seen a "not a person" negative for a non-human subject. Fixing this requires new indoor/animal-aware training data, not more epochs (training has converged).
11b. **New (Phase Demo.5/AI.1): 2 of the demo dataset's Safe images are visually mislabeled** (`937...jpg` shows an active wildfire+bystander; `H_00980...jpg` shows a smoke/steam plume) — both are pipeline "negatives" only because their training-annotation file happened to be empty, not because they're visually hazard-free. `H_00980` is confirmed, with live evidence, to be the recurring source of false "smoke" detections. Flagged, not yet removed.
12. Torch is now CUDA-enabled (2.12.1+cu130, RTX 3060 Ti) — training expected ~1–2 min/epoch; backend ONNX inference still runs on CPU by design (~25–450 ms/frame, fine at 1 s ticks)
13. `perception_detector` default remains "ground_truth"; "yolo" is opt-in until the real model lands
14. Dashboard: layout is tuned for ≥1400 px wide screens; camera video/stream source kinds are typed but intentionally unimplemented (~~box-label edge overflow~~ fixed in 8K with edge-aware labels)
15. ~~Camera imagery repeats within/across missions~~ — fixed in Phase 8K (mission-scoped no-repeat pool; committed default is now `seed: null` normal random mode with the per-mission effective seed logged; set an integer seed for deterministic missions). Library variety itself is still limited (only 2 `safe` images until D-Fire)
16. All V2 commits and tags (v2.0-phase-8c / -8f / -8i1 / -8j) exist locally only — nothing beyond v1.0.0 pushed to GitHub; Phase 8K is implemented but uncommitted
17. Backend (pre-existing, discovered during 8K.1 verification, deliberately NOT fixed yet): the mission restart path in `backend/api/routes.py` replaces `app.state.adapter` without stopping the old one (and `/mission/end` doesn't stop it either) — ending a mission mid-run and immediately restarting lets the old runner's frames interleave into the new mission until its BFS finishes; harmless under normal natural-end operation
18. ~~Recycle-boundary repetition~~ — fixed in Phase Demo.4: the same image can no longer appear immediately after its category's pool recycles (verified for 2-image and 4-image pools; single-image categories provably unaffected).
19. Demo Mode exists as an opt-in, fully isolated alternative image source (`assets/demo_dataset/`, 202 images: fire 41/smoke 30/fire_smoke 38/person 45/safe 48) switched on by one settings flag (`camera_demo_mode`, default `False`). Architecture A (Category → Scene) is now the sole, finally-decided dataset filesystem standard project-wide (Phase 10A.4/10B.1) — no Environment-first structure remains anywhere.

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
| 8G | Live AI Vision dashboard (MissionState.vision, image + boxes to operator) | Complete |
| 8H | Permanent simulation image library (assets/ master + export tool) | Complete |
| 8I.1 | Professional dashboard UX redesign (MissionCamera, EOC layout) | Complete |
| 8J | Scene-aware dataset split (leakage fix + dataset regeneration + verification) | Complete |
| 8K | Camera experience (no-repeat pool, random mode) + live camera monitor UI | Complete (uncommitted) |
| 9A/9B | Simulation Library dataset assessment + curation staging | Complete |
| 10A.1–10A.4 | Persist findings, dataset standard doc, folder build + reversal, architecture decision (Architecture A final) | Complete |
| 10B.1 | Migrate filesystem to Architecture A (sole standard) | Complete |
| Scene-Aware design | Architecture proposal only | Complete (design), **NOT implemented/approved** |
| Demo.1–Demo.6 | Demo dataset built, validated, Demo Mode switch added, recycle-boundary bug fixed, Safe expanded 2→48 | Complete |
| AI.1 | Retrained YOLO (60 ep, GPU) + full live validation | Complete — verdict **B) Demo Ready with Minor Issues** |
| **next** | **Build a high-quality Indoor Fire Dataset (see Next Session Plan) — do not start without instruction** | **NEXT** |
| — | Fire detection, SLAM/mapping, sensor fusion modules | Future |

Integration path (unchanged, requires zero frozen-module edits): a learned detector implements `BaseDetector` (`perception/base/detector.py`), loads an exported model from `ai/object_detection/models/exports/`, registers in `DetectorRegistry` alongside `ground_truth`, and is activated via `perception_detector` in `backend/config/settings.py`.

**Constraints that remain in Version 2:** no authentication, no analytics dashboards, no cloud infrastructure, no mobile optimization, and **"STOP after each phase, wait for user instruction" always applies.**

---

## THE EXACT NEXT TASK

> **Note:** Phases 8A–8J are complete and committed (tags `v2.0-phase-8c` / `v2.0-phase-8f` / `v2.0-phase-8i1` / `v2.0-phase-8j`). Phase 8K through Phase AI.1 (everything documented above — camera experience, Simulation Library curation, Architecture A finalization, the Scene-Aware design proposal, the full Demo.1–6 sequence, and the retrained model) are all complete and fully verified but **entirely uncommitted**. Do NOT redo any of this work. The first action of the next session should be deciding what (if anything) to check-point/commit before starting new work — nothing has been committed since `v2.0-phase-8j`.

**The next phase is not yet defined for implementation — wait for the user — but the recommended priority order is now fixed by AI.1's own conclusion.** Do NOT default back to "more training" or "D-Fire" as the next step; both were superseded by AI.1's finding that **training has converged and the bottleneck is now data quality**, specifically the total absence of indoor building imagery. See the **Next Session Plan** section immediately below for the exact 5-phase roadmap. Superseded/no-longer-primary items from earlier sessions: D-Fire merge (still valid for its 9,838 negatives, but does not address the indoor-scene gap AI.1 identified as the real priority); the "50-epoch run" (done — see Phase AI.1, now 60 epochs on the corrected split); 8I.2 UX follow-ups (still open, low priority: responsive breakpoints below ~1400 px, replay scrubbing controls).

Also pending user decisions: pushing all checkpoints to GitHub; whether to flip `perception_detector`'s default to `"yolo"` now that the new model is live-validated; whether to prune the 2 mislabeled Safe images (`937`, `H_00980`) and any animal photos from the demo Safe pool.

**How every demo in this session was run (repo files untouched):** the committed default is `perception_detector="ground_truth"`, `camera_demo_mode=False`; every live demo used a throwaway launcher overriding both in-process before starting uvicorn, and the new model is loaded purely via the existing "newest `.onnx` in `models/exports/`" auto-discovery — no code was ever changed to make any of this work. To make either change permanent, edit `backend/config/settings.py` deliberately.

---

## Next Session Plan (exact roadmap, in order)

**Phase 1 — Curate a realistic indoor-building dataset.** Source and/or select kitchens, offices, warehouses, hospitals, schools, shopping malls, hotels, corridors, electrical rooms, server rooms, basements, and stairwells. In the same pass: remove the remaining poor-quality demo images, replace the 2 visually-misleading "Safe" images (`937`, `H_00980`), and remove animal photos from the demo Safe pool (root cause of the animal→person misclassification found in AI.1).

**Phase 2 — Organize the new indoor images into the proper project categories**, following Architecture A (Category → Scene) exclusively — this is now the sole, finally-decided filesystem standard; do not reintroduce an Environment-first structure (see Phase 10A.4's decision).

**Phase 3 — Retrain the detector** using the improved indoor dataset, following the same GPU training pattern validated in Phase AI.1 (in-memory config overrides, new run directory, original checkpoints never touched).

**Phase 4 — Run a complete benchmark against the current model** (`firerescue-detector-20260705-064246`, the AI.1 result) — same methodology as AI.1: evaluate on the identical split, compare P/R/mAP50/mAP50-95 overall and per-class, confusion matrix, inference speed.

**Phase 5 — Perform a final end-to-end demo validation**, same rigor as Demo.3/AI.1's live testing: real backend, real WebSocket, multiple full missions, explicit check of whether the animal-misclassification and mislabeled-Safe-image issues are actually resolved (not just assumed fixed by the new data).

---

## Documentation Status

`docs/` (15 files): this file is the AUTHORITATIVE V2 context; `phase-8k-report.md` is the Phase 8K engineering report; `project-status.md` and `handoff-report.md` carry dated Version 2 sections (2026-07-03) on top of their preserved MVP content; the remaining docs (api-design, architecture, database, demo-guide, developer-guide, requirements, roadmap, simulation, system-overview, tech-stack, ui-design) reflect MVP v1.0.0 by design. `ai/README.md` documents the V2 AI workspace incl. the dataset workflow and integration. `assets/simulation_dataset/README.md` documents the master image library. `ai/object_detection/models/reports/training_report.md` documents the first training run. Root `README.md` covers the MVP only (does not yet mention `ai/` — intentional until V2 is pushed/released).

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
