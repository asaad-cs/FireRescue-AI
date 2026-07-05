# FireRescue AI — Handoff Report

**Date:** 2026-07-05 (§FREEZE — project freeze + GitHub migration, current) / 2026-07-05 (§0 — Version 2 session handoff, preserved) / 2026-07-01 (§1+ — MVP v1.0 handoff, preserved unchanged)
**Status:** Fully operational, in both Production Mode and Demo Mode. All tests pass (623 BE + 50 subtests, 334 FE, tsc 0). **The repository is frozen: everything through Phase AI.1 is committed at `0861ff0` on `main` and pushed to `origin/main`, along with all four previously local-only V2 checkpoint tags.**

---

## §FREEZE — Project Freeze & GitHub Migration (2026-07-05)

This section documents a **documentation-and-checkpoint session only**. No features were added, no model was retrained, no dataset was modified, no architecture changed, and no runtime behavior changed. The only code-adjacent change was two narrowly-scoped `.gitignore` entries (see below). Everything else was: verify → commit → push → document.

### What was verified before committing

- All work described in §0 below (Phases 8K through AI.1) was confirmed present on disk and matching its documentation: file counts for `assets/demo_dataset/` (fire 41, smoke 30, fire_smoke 39, person 45, safe 46 — ≈201 images, close to but not exactly the previously-cited 202, within normal narrative-vs-actual drift) and `assets/simulation_dataset/_curation/` (approved 14, manual_review 165, rejected 55 — exact match), the `camera_demo_mode` settings field and its conditional in `camera_adapter.py`, the `ZoneImageProvider` recycle-boundary fix in `provider.py`, and the `MissionCamera` live-monitor redesign in the frontend.
- Full backend suite: **623 passed + 50 subtests**. Full frontend suite: **334 passed**. TypeScript: **0 errors**. All run immediately before committing.
- Two stray, undocumented generated artifacts were found and excluded from the commit (not part of any phase above): a `runs/` directory at the repo root (Ultralytics validation output — PR curves, confusion matrices — that no documented script writes to) and `yolo26n.pt` (an auto-downloaded weight for a YOLO26 architecture never used by this project, which trains `yolov8n`). Both were left on disk, untouched, and excluded via new `.gitignore` entries (`/runs/`, `yolo26*.pt`) so they can't be accidentally staged later.

### What was committed and pushed

| Item | Value |
|---|---|
| Commit hash | `0861ff0` |
| Commit message | `Checkpoint: Demo-ready architecture + AI v2 baseline` |
| Files changed | 451 (437 additions, 14 modifications) |
| Branch | `main`, pushed to `origin/main` (`https://github.com/asaad-cs/FireRescue-AI`) |
| Push result | `c5edef9..0861ff0 main -> main` — success |
| Tags pushed | `v2.0-phase-8c`, `v2.0-phase-8f`, `v2.0-phase-8i1`, `v2.0-phase-8j` (previously local-only) |

### Post-push verification

- `git status` → clean
- `git rev-parse main` == `git rev-parse origin/main` (identical SHA)
- `main` tracks `origin/main` with zero ahead/behind
- `git branch -r --contains 0861ff0` confirms the commit is present on the remote
- `git ls-files` confirms no `datasets/{raw,processed,merged,external}/` or `models/{checkpoints,exports}/` content was committed (only `.gitkeep` placeholders, as intended) and confirms all load-bearing config/entry-point files are tracked

### Reproducibility caveat (reported, not fixed)

**Trained model weights are not in GitHub.** `ai/object_detection/models/{checkpoints,exports}/` have been gitignored since Phase 8B (a pre-existing convention, not changed this session) — cloning the repo alone gives you the full codebase, both image libraries (production + demo, both tracked), and the dataset-pipeline reports, but not a `.onnx`/`.pt` file to run the `yolo` detector. A new machine must either retrain from scratch (see `docs/session-context.md` → "Setup Guide") or receive the model file out-of-band. Committing large binary model files would be a real workflow/architecture decision outside this task's scope ("documentation updates only") — this is reported here per the task's explicit instruction to report rather than implement anything found missing.

### Remaining TODOs

See `docs/session-context.md` → "Migration Report" for the complete list (indoor-dataset curation Phases 1–5, the two mislabeled Safe images, the flagged kitchen-fire special case, 165 unadjudicated Manual Review images, D-Fire merge decision, default-detector-flip decision, npm audit Vite upgrade decision, the pre-existing restart-adapter bug). None were started or implemented this session.

### Confirmation

A new machine can `git clone https://github.com/asaad-cs/FireRescue-AI`, check out `main` at `0861ff0`, follow the Setup Guide in `docs/session-context.md`, and run the full simulation + backend + frontend + Demo Mode experience immediately — every required asset for that is tracked in git. The one gap is the trained YOLO model file itself (see caveat above).

---

## 0. Version 2 Session Handoff (2026-07-02 → 2026-07-03)

### What this session delivered (chronological)

1. **Phase 8C — Dataset engineering** → committed, tag `v2.0-phase-8c` (`09f9388`). data_tools pipeline (download/validate/merge/split/build/quality), sources registry, 12,545-image processed dataset validated clean, reports tracked in git. D-Fire remains a manual download (`ai/object_detection/docs/download_instructions.md`).
2. **Phase 8D — First training** → yolov8n 5-epoch CPU smoke test (~4h15m; survived two runner interruptions via Ultralytics resume). Val mAP50 0.509 / mAP50-95 0.270. ONNX export verified (11.7 MB, opset 20) at `ai/object_detection/models/exports/firerescue-detector-20260703-003931-best.onnx`; full report in `ai/object_detection/models/reports/training_report.md`.
3. **Phase 8E — Integration** → `perception/detectors/yolo.py` (`YOLODetector` on `AbstractDetector`, ONNX Runtime, letterbox → decode → conf filter → numpy NMS → class mapping; never raises, degrades to UNOBSERVED). Registered beside `ground_truth` in `backend/main.py`; switching via `settings.perception_detector` (default still `ground_truth`).
4. **Phase 8F — Simulated camera** → `simulation/camera/` provider (+`simulation_camera.yaml`), `CameraSimAdapter` DataSource decorator sets `Frame.channels["rgb"]`, shared `make_data_source()` used by startup AND mission restart. 8D+8E+8F committed together, tag `v2.0-phase-8f` (`68fcc6f`, current HEAD).
5. **Phase 8F verification run** → full app launched live; diagnosed and killed a stale pre-8F backend squatting port 8000; verified real end-to-end YOLO detections (victim 0.85; Loading Dock EMERGENCY).
6. **Camera randomization analysis** → documented that missions repeat imagery by design (fresh provider + fixed seed 42 per mission). Recommended (not yet implemented): optional `seed: null` entropy mode with logged effective seed.
7. **Phase 8G — Live AI Vision dashboard** *(uncommitted)* → detector packs the analysed JPEG + detections + timing into `DetectionResult.metadata`; engine passes it through; `MissionManager` lifts it into new optional `MissionState.vision`. Image rides inside MissionState → replay/history free, zero duplicate inference. Ground-truth mode shows a clean fallback.
8. **Phase 8H — Permanent image library** *(uncommitted)* → `assets/simulation_dataset/` master library (categories × scene sub-folders, 50 seeded images, README with curation/licensing rules); `simulation/camera/images/` is now a generated runtime folder rebuilt by `export_simulation_library.py`. Regeneration proven content-exact; runtime folder byte-identical (zero behavior change).
9. **Phase 8I.1 — Dashboard UX redesign** *(uncommitted, frontend-only)* → EOC layout. **Key design decision: `MissionCamera` is video-first** — a `CameraMediaSource` union (`image` | `video` | `stream`) renders through one `CameraMedia` switch, so future video/drone feeds require no UI redesign. Plus `DetectionCards`, `MissionOpsPanel`, enlarged glowing map, alert cards, polished timeline. All 295 original frontend tests pass unmodified; 8G's `AIVisionPanel` superseded/removed with all capabilities and tests ported.

### Architectural decisions made this session

- Vision imagery travels **inside MissionState** (base64 JPEG) rather than via a new endpoint — preserves the "frontend receives only MissionState" invariant and makes replay carry vision for free.
- `MissionCamera` media-source abstraction (video-ready by design, images-only today).
- Master image library (`assets/`) is the permanent source; the simulator's folder is generated. `assets/` intentionally NOT gitignored — user decides whether to track its images at commit time.
- Live demos override `perception_detector` to `"yolo"` in-process via an external launcher; committed default stays `ground_truth` for backward compatibility.
- Frozen-MVP seam edits stayed minimal and additive throughout (settings/main/routes/models/manager/engine — all user-authorized, all documented in `docs/session-context.md`).

### Verification status at handoff

- Backend 605 tests + 50 subtests · Frontend 319 tests · TypeScript 0 errors — all green against the final tree.
- Live run verified this session: real YOLO detections on the redesigned dashboard (screenshots in `C:\Users\Administrator\Desktop\firerescue-8g-screenshots\`).
- Dev services (backend with YOLO launcher + Vite) were left running for manual review; they are disposable — nothing is lost by stopping them or rebooting.

### Phase 8J — Scene-aware dataset split (2026-07-04, tag `v2.0-phase-8j`)

Fixed the dataset audit's finding 1 (near-duplicate split leakage).
`data_tools/split.py` now assigns whole scenes (Roboflow `.rf.<32-hex>`
suffix stripped from the file stem) stratified by dominant class
signature; `splits.json` records `method: "scene"`. Dataset regenerated
via the full pipeline (seed 42): 8,783/2,515/1,247 (70.0/20.0/9.9%),
validator CLEAN. Independently verified: 0 scene leakage across 9,956
scenes; class-share spread ≤ 0.56%; residual exact-dHash overlap with
train 16.9%→8.0% (val), 15.6%→6.2% (test) — remainder are cross-name
near-duplicates, deferred (dHash-cluster grouping or pruning). +4 split
tests (backend suite now 609 + 50 subtests). Phase 8D metrics (mAP50
0.509, old split) are no longer comparable. Reports:
`datasets/reports/split_fix_2026-07-04.md` + audit addendum. The full
system was launch-verified end-to-end after the fix (YOLO detector,
camera, live vision, WebSocket).

### Phase 8K — Camera experience + live camera monitor (2026-07-04, committed 2026-07-05 in `0861ff0` — see §FREEZE)

Implemented and fully verified the camera/UX phase (report:
`docs/phase-8k-report.md`): mission-scoped no-repeat image pool with
balanced recycling and sticky zone assignments; three selection modes
with `seed: null` (fresh logged entropy seed per mission) as the new
committed default; MissionCamera redesigned as a live camera monitor
(stage HUD, scanlines, frame fade-in, edge-aware detection labels,
LIVE/STALE/ACQUIRING SIGNAL/standby link states via new optional
`wsStatus`/`isStale` props, Targets+Link telemetry, contacts chip,
history detection dots). Suites: 619 BE (+50 subtests) / 334 FE / tsc 0;
all pre-8K tests pass unmodified. Live-verified end to end (two missions,
distinct effective seeds, fire 0.92 in Loading Dock over WebSocket),
then fully visually verified (screenshots in
`Desktop\firerescue-8k-screenshots\`). The **8K.1 fix pass** closed the
three UX issues that verification surfaced (mission-scoped history rail,
REPLAY badge + frozen history during replay, HUD bands that structurally
prevent HUD/label overlap — all frontend-only) and discovered a
pre-existing backend issue (restart path doesn't stop the old adapter —
deliberately NOT fixed, see report §7).
~~Awaiting user approval for the checkpoint commit~~ — **done 2026-07-05**: committed as part of the single bundled checkpoint `0861ff0` (see §FREEZE), not under a separate `v2.0-phase-8k` tag.

### Phase 9A/9B/10 — Simulation Library gap analysis + partial curation (2026-07-04/05, committed 2026-07-05 in `0861ff0` — see §FREEZE)

Full detail: `ai/object_detection/datasets/reports/phase9b_promotion_manifest_2026-07-05.md`.

**Completed:** Phase 9A read-only dataset assessment (training set is ~85%
outdoor, near-zero building-interior content); Phase 9B curation staging (an
exhaustive filename search — not just random sampling — found a previously-
missed real cluster: 58 residential house-fire images, 18 indoor training-
facility images, plus a 49-image toy/miniature-model trap that looks
convincing at a glance); Phase 9B promotion, roadmap step 10A.4 (234 unique
images copied from session scratch space into
`assets/simulation_dataset/_curation/{approved,manual_review,rejected}/` — 14
Approved, 165 Manual Review, 55 Rejected preserved; independently re-verified
afterward to have zero effect on the runtime pipeline); a design-existence
audit (Phase 10, confirmed no prior Simulation Library architecture doc
exists beyond `assets/simulation_dataset/README.md`); a separate architectural
review of the full Scenario→Camera→Frontend component chain and data flow;
and a Scene-Aware Simulation Architecture design document (chat-only, not
yet persisted as a repo file).

**Not done / pending:** roadmap steps 10A.2 (README target-count and
acceptance-rule sections), 10A.3 (new environment folders + promotion into
the live/exported library), and 10A.5 (sourcing-strategy decision) — none
executed. Manual adjudication of the 165 Manual Review images. A decision on
one flagged special case (a genuine kitchen-fire photo currently mis-tiered
as a "letterboxing example"). Scene-aware implementation itself — contingent
on approval of the design document.

**Deferred on purpose:** D-Fire download (Phase 9A found it would not close
the building-scene gap — safe to postpone independently); any new image
sourcing/searching (out of scope by explicit instruction throughout); making
the simulator scene-aware (deliberately withheld from the promotion step to
keep the runtime pipeline provably untouched).

`ZoneCategoryResolver` remains hazard-category only — the simulator is not
scene-aware today, and this pass did not change that.

### Phases 10A.2 → AI.1 — Architecture Finalization, Demo System, Model Retrain (2026-07-05, committed 2026-07-05 in `0861ff0` — see §FREEZE)

Full detail in `docs/session-context.md` (authoritative — every phase below has its
own dated subsection there). Summary in chronological order:

1. **10A.2** — `assets/simulation_dataset/README.md` extended additively (target
   counts, acceptance rules, curation workflow; 138 insertions, 0 deletions).
2. **10A.3** — built a proposed "Environment → Scene" folder structure (8 top-level
   dirs + 35 subfolders, all empty).
3. **10A.4** — architectural review found that structure would be silently
   mis-scanned by the (unmodified) export tool's default invocation. **Final
   decision: Architecture A (Category → Scene, the pre-existing Phase 8H shape)
   is the sole official standard** — no hybrid, no Environment-first structure.
4. **10B.1** — reversed 10A.3: removed all 43 empty directories (zero data loss,
   nothing had ever been committed). The 6 environments with no existing
   Architecture-A home (hospital/mall/school/residential/industrial/outdoor)
   remain an open, honestly-unresolved gap.
5. **Scene-Aware design document** — a full architecture proposal (environment
   model, selection-strategy fallback chain, migration plan) produced in chat.
   **Not implemented. Not approved.**
6. **Demo.1–Demo.3** — built `assets/demo_dataset/` (isolated from both the
   master library and `_curation/`), validated every image against the exact
   decode path the provider uses, added Demo Mode as **one** settings flag
   (`camera_demo_mode`, default `False`) plus a ~7-line conditional in
   `make_data_source()` — zero changes to selection logic, resolver, or config
   format. Live-verified end to end (real backend, real WebSocket, full
   mission lifecycle). Verdict at that point: Demo Ready (92%).
7. **Demo.4** — fixed a real gap found by a read-only investigation: on pool
   recycle, the image that had just closed a cycle could immediately reopen
   the next one. Fixed with one new dict (`_last_shown`) and ~12 lines total
   in `ZoneImageProvider._pick_unused()`; single-image categories provably
   unaffected. +4 tests, 623 total, zero regressions.
8. **Demo.5–Demo.6** — expanded the Safe category from 2 images to **48**,
   using only pre-existing repo assets: 1 new master-library image
   (`cleanroom.jfif`, extension-corrected on the copy only) plus 45 images
   mined from a previously-unexamined pool — the 2,307 raw COCO val2017
   images that were excluded from training for having no person. Also
   discovered and reported (not silently fixed): the original 2 "negative"
   Safe images are visually **not** safe (an active wildfire and a
   smoke/steam plume) — they were only "negative" by empty annotation.
9. **Phase AI.1** — retrained the YOLO model on GPU: 60 epochs (vs. the
   original 5, CPU), batch 32, cosine LR, patience 15; new run
   `firerescue-detector-20260705-064246`, original checkpoint untouched.
   True old-model baseline finally measured on the corrected split: mAP50
   0.3997 (not the previously-cited, leakage-inflated 0.509). New model:
   mAP50 0.601, mAP50-95 0.334, recall up across all 3 classes (smoke +0.124
   the largest gain). Live-validated across 7 real missions: 6/6 fire
   detections, 11/12 victim detections, zero crashes. Root-caused every
   remaining false positive with directly captured evidence: 5 are animal→
   person misclassifications (zebras/dog/bird/horse/seagulls, all
   low-confidence — the training corpus has zero animal images anywhere),
   2 are the same pre-existing mislabeled Safe images from Demo.5, 1 is a
   single low-light instance. **Verdict: B) Demo Ready with Minor Issues.**
   **Training has converged — more epochs will not help further; the
   bottleneck is now data quality, specifically indoor building imagery.**

### Pending work (next session, in recommended order)

1. ~~Checkpoint commit of 8G/8H/8I.1~~ — **done 2026-07-03**: commit `fe9fc19`, tag `v2.0-phase-8i1`, tests re-verified green immediately before committing; `assets/simulation_dataset/` images tracked per user decision.
2. ~~CUDA torch install~~ — **done 2026-07-03** (env-only, zero project edits): torch 2.12.1+cu130, `torch.cuda.is_available()` True, verified incl. YOLODetector ONNX inference; ai+yolo tests 270 passed.
3. **Dataset audit done 2026-07-03** — see `ai/object_detection/datasets/reports/dataset_audit_2026-07-03.md`. Key: near-duplicate split leakage (16.9% val / 15.6% test contaminated; metrics inflated), zero fire+person co-occurrence, 2 negatives. ~~Fix cluster-aware split~~ — **done 2026-07-04 (Phase 8J, see above)**; merge D-Fire BEFORE the 50-epoch run.
4. ~~Manual D-Fire download + pipeline re-run + 50-epoch training~~ — **superseded 2026-07-05 by Phase AI.1**: a 60-epoch GPU retrain happened on the scene-aware split without D-Fire (D-Fire was explicitly analyzed and deferred — it doesn't close the indoor-imagery gap that turned out to be the real bottleneck). Threshold calibration and the default-detector flip remain open, low-priority decisions.
5. ~~Optional: 8I.2 UX follow-ups; pushing checkpoints to GitHub~~ — **checkpoints pushed 2026-07-05** (commit `0861ff0`, see §FREEZE at the top of this file); 8I.2 UX follow-ups (responsiveness < 1400px, replay scrubbing) remain open and low-priority. **The actual next priority is NOT further training** — see `docs/session-context.md` → "Next Priority" for the required 5-phase indoor-building dataset curation plan.

---

# FireRescue AI — MVP v1.0 Handoff Report

**Version:** 1.0.0  
**Date:** 2026-07-01  
**Prepared by:** Session handoff  
**Status:** Complete. All systems verified. All tests pass. No open issues.

---

## 1. Project Version

**Version 1.0.0 — MVP Complete**

This is the first stable release of the FireRescue AI prototype. All planned MVP phases are done and locked. The codebase is frozen at this version pending deliberate decision to begin Version 2.

---

## 2. Completed Phase Summary

| Phase | Title | Objective | Status | Locked |
|---|---|---|---|---|
| 0 | Project Foundation | Directory structure, .gitignore, doc stubs | Complete | Yes |
| 1 | Architecture & Design | Full architectural blueprint in docs/ | Complete | Yes |
| 2 | Simulation Engine | Building model, drone BFS, sensor emulation | Complete | Yes |
| 3 | Backend & Pipeline | FastAPI, MissionManager, Broadcaster, WebSocket | Complete | Yes |
| 4 | Full Integration | Auto-start, SimAdapter, end-to-end data flow | Complete | Yes |
| 5 | Perception Framework | GroundTruthDetector, DetectorRegistry, PerceptionEngine | Complete | Yes |
| 6A | Frontend Foundation | React 18, Zustand, WebSocket hook, dark theme, layout | Complete | Yes |
| 6B | Interactive Dashboard | 8 dashboard components, mission controls, alert panel | Complete | Yes |
| 7A | Visual Polish | CSS animations, grid labels, MissionStatistics row | Complete | Yes |
| 7B | Multiple Scenarios | 5 building scenarios, scenario registry, activate API | Complete | Yes |
| 7C | Mission Replay | MissionRecorder, ReplaySlice, ReplayControls, useReplayEngine | Complete | Yes |
| — | MVP Documentation | README, developer-guide, demo-guide, project-status, roadmap | Complete | Yes |

---

## 3. Architecture Status

**Status: Stable. No changes since Phase 6A.**

```
Frontend (React 18 + TypeScript + Vite + Tailwind + Zustand)
  └── Zustand Store (4 slices: connection, mission, ui, replay)
        └── useWebSocket hook → ws://localhost:8000/ws
        └── REST calls → /api/* → Vite proxy → backend

Backend (FastAPI + uvicorn, port 8000)
  └── MissionManager (state machine + listener registry)
        ├── Broadcaster.on_state_change → WebSocket fan-out
        ├── MissionRecorder.on_state_change → deep-copy history
        └── Pipeline (Validate → Enrich → PerceptionEngine)
              └── SimAdapter → SimulationRunner (active scenario)
```

**The one invariant that must never break:** The frontend only ever receives `MissionState`. It has no knowledge of `Frame`, `PerceptionResult`, `ZoneHistory`, or any internal backend type.

---

## 4. Backend Status

**Status: Fully operational.**

- **Framework:** Python 3.12 + FastAPI + uvicorn, port 8000
- **Tests:** 286 passing + 50 subtests (pytest)
- **Endpoints:** 10 REST routes + 1 WebSocket endpoint
- **Configuration:** `backend/config/settings.py` — all tuneable values in one place
- **State machine:** IDLE → ACTIVE → PAUSED → ACTIVE → ENDED → (restart) → IDLE
- **Tick rate:** 1.0 second (configurable)
- **Startup:** Mission auto-starts with Warehouse Alpha on backend launch

### REST API

| Method | Path | Description |
|---|---|---|
| GET | `/` | Service info |
| GET | `/health` | Liveness check |
| POST | `/mission/start` | Start/restart mission |
| POST | `/mission/pause` | Pause active mission |
| POST | `/mission/resume` | Resume paused mission |
| POST | `/mission/end` | End mission immediately |
| GET | `/scenarios` | List scenarios + active key |
| POST | `/scenarios/{key}/activate` | Set scenario for next mission |
| GET | `/replay/frames` | Full recorded MissionState history |
| GET | `/replay/frames/count` | Frame count |

### WebSocket

- `ws://localhost:8000/ws`
- Push-only: full `MissionState` JSON on every state change
- Immediately pushes current state on new connection

---

## 5. Frontend Status

**Status: Fully operational.**

- **Framework:** React 18 + TypeScript 5.5 + Vite 5.4 + Tailwind CSS 3.4 + Zustand 4.5
- **Tests:** 295 passing (Vitest + Testing Library), 14 test files
- **TypeScript:** 0 errors (`npx tsc --noEmit`)
- **Build:** ~197 kB JS bundle, 68 modules

### Zustand Store Slices

| Slice | Key State | Key Actions |
|---|---|---|
| Connection | `wsStatus`, `reconnectAttempts` | `setWsStatus`, `incrementReconnectAttempts` |
| Mission | `missionState`, `lastUpdatedAt` | `setMissionState`, `clearMissionState` |
| UI | `isSidebarCollapsed`, `acknowledgedAlertIds` | `toggleSidebar`, `acknowledgeAlert` |
| Replay | `isReplaying`, `replayHistory`, `replayIndex`, `replaySpeed`, `finalMissionState` | `startReplay`, `stepReplay`, `exitReplay`, `restartReplay` |

### Dashboard Components

| Component | Purpose |
|---|---|
| `TacticalMap` | 5×4 CSS Grid, zone hazard colours, drone ping, victim flags |
| `AlertPanel` | Priority-sorted alerts with acknowledgement + emergency pulse |
| `DroneStatus` | Drone coordinates, heading, sensor readings |
| `VictimSignals` | Per-zone victim signal list with probability bars |
| `MissionControls` | Status dot, timer, action buttons, REPLAY button |
| `MissionTimeline` | Horizontal scrollable event chip bar |
| `ActivityFeed` | Compact chronological log |
| `ConnectionBanner` | WebSocket status banner with reconnect |
| `MissionStatistics` | 4-stat compact row: explored%, elapsed, alerts, signals |
| `ReplayControls` | REPLAY label, frame counter, progress bar, speed/pause/exit |

---

## 6. Simulation Status

**Status: Fully operational. Frozen.**

- **Scenarios:** 5 (Warehouse Alpha, Office Building, Hospital, Shopping Mall, School)
- **Exploration:** BFS — deterministic, completes in `N zones × tick_interval` seconds
- **Registry:** Factory functions, never cached — each call returns a fresh `Scenario` instance
- **Switching:** `POST /scenarios/{key}/activate` + `POST /mission/start`
- **Sensor data:** Deterministic per zone; not dynamically varying

| Scenario | Zones |
|---|---|
| `warehouse_alpha` | 20 |
| `office_building` | 12 |
| `hospital` | 16 |
| `shopping_mall` | 15 |
| `school` | 16 |

---

## 7. Perception Status

**Status: Fully operational. Frozen.**

- **Active detector:** `GroundTruthDetector` — reads static hazard/victim maps from scenario
- **Registry:** `DetectorRegistry` supports multiple named detectors; only `ground_truth` registered
- **HazardLevel:** NONE / LOW / MODERATE / HIGH / CRITICAL
- **Victim signals:** Displayed at ≥30% probability; amber ≥60%; red ≥80%
- **Alerts:** Deduplicated by (zone_id, hazard_level) pair
- **No ML inference:** Ground-truth values only. False positives/negatives not modelled.

---

## 8. Replay Status

**Status: Fully operational.**

### How it works

1. `MissionRecorder` registers as a state-change listener alongside `Broadcaster`
2. On every `MissionState` update, it appends a `model_copy(deep=True)` to `_history`
3. Frontend `setMissionState` appends to `replayHistory` on every live update
4. On mission end: `MissionControls` shows a REPLAY button
5. User clicks REPLAY → `startReplay()` → `isReplaying = true`, `replayIndex = 0`
6. `useReplayEngine` tick fires `stepReplay()` at 0.5×/1×/2× speed
7. `ReplayControls` replaces `MissionControls` in the nav bar
8. EXIT → restores `finalMissionState`, `isReplaying = false`

### Replay speed intervals

| Speed | Interval |
|---|---|
| 0.5× | 2000 ms / frame |
| 1× | 1000 ms / frame |
| 2× | 500 ms / frame |

---

## 9. Documentation Status

**Status: Complete. Accurate. Verified against implementation.**

| Document | Purpose | Status |
|---|---|---|
| `README.md` | Project overview, architecture, installation, API, demo, roadmap | Complete |
| `docs/developer-guide.md` | Architecture deep dive, setup, extending the system | Complete |
| `docs/demo-guide.md` | Step-by-step demonstration walkthrough | Complete |
| `docs/project-status.md` | Phase status, stable modules, limitations, debt | Complete |
| `docs/roadmap.md` | Phase-by-phase history + Version 2 future work | Complete |
| `docs/architecture.md` | Original architectural blueprint (Phase 1) | Preserved |
| `docs/api-design.md` | Communication design | Preserved |
| `docs/database.md` | Planned schema (not implemented) | Preserved |
| `docs/simulation.md` | Simulation design | Preserved |
| `docs/ui-design.md` | UX design and wireframes | Preserved |

---

## 10. Test Status

**All tests pass. No known failures.**

```
Backend:  286 tests passed  +  50 subtests passed  (pytest)
Frontend: 295 tests passed                          (Vitest)
TypeScript: 0 errors                                (tsc --noEmit)
Debug artifacts: 0                                  (grep verified)
```

### Backend test files

| File | Covers |
|---|---|
| `test_models.py` | Pydantic models, enums, serialisation |
| `test_pipeline.py` | Validator, Enricher, Pipeline stages |
| `test_mission_manager.py` | State machine, Frame processing, notifications |
| `test_api.py` | REST endpoints, 409 state transitions |
| `test_perception.py` | Hazard classifier, victim estimator, alert gen |
| `test_perception_engine.py` | PerceptionEngine orchestration |
| `test_scenarios_api.py` | Scenario list, activate, switch on restart |
| `test_recorder.py` | MissionRecorder unit + replay API endpoints |
| `simulation/tests/test_building.py` | Zone connectivity, adjacency symmetry |
| `simulation/tests/test_drone.py` | BFS traversal, path completeness |
| `simulation/tests/test_runner.py` | Tick loop, completion callback |
| `simulation/tests/test_scenarios.py` | All 5 scenarios, integrity, runner (+ 50 subtests) |
| `perception/tests/` (5 files) | Ground truth detector, registry, confidence, failure handling |

### Frontend test files (14 files)

`missionStore.test.ts` · `TacticalMap.test.tsx` · `AlertPanel.test.tsx` · `DroneStatus.test.tsx` · `VictimSignals.test.tsx` · `MissionTimeline.test.tsx` · `MissionStatistics.test.tsx` · `MissionControls.test.tsx` · `ReplayControls.test.tsx` · `AppLayout.test.tsx` · `Placeholders.test.tsx` · `api.test.ts` · `websocket.test.ts` · `format.test.ts`

---

## 11. Stable Modules — Do Not Modify

These modules are complete, fully tested, and frozen at MVP v1.0.

### Backend
- `simulation/` — all files
- `perception/` — all files
- `backend/models/` — any change requires matching `frontend/src/types/mission.ts` update
- `backend/pipeline/` — all files
- `backend/mission/manager.py`
- `backend/mission/recorder.py`
- `backend/websocket/broadcaster.py`
- `backend/ingestion/interface.py` ← hardware independence boundary
- `backend/ingestion/sim_adapter.py`

### Frontend
- `frontend/src/types/mission.ts` — mirrors backend models exactly
- `frontend/src/stores/missionStore.ts` — all four slices
- `frontend/src/services/websocket.ts`
- `frontend/src/hooks/useWebSocket.ts`
- `frontend/src/hooks/useReplayEngine.ts`
- All test files — only strengthen, never weaken

---

## 12. Known Limitations

1. **In-memory state only.** No database. Backend restart clears all history.
2. **No scenario selection UI.** Scenario switching requires direct API call.
3. **Deterministic sensor data.** Sensor readings are fixed per zone; no real-time variation.
4. **One drone per mission.** Multi-drone requires significant MissionManager changes.
5. **No persistent alert acknowledgements.** Reset on page reload or mission restart.
6. **No authentication.** Open API and WebSocket — local research tool only.
7. **Client-side replay history only.** Page reload during a mission loses recorded history.
8. **Ground-truth perception only.** No false positives, no ML, no probabilistic uncertainty.
9. **Single WebSocket per tab.** Each browser tab maintains independent state.

---

## 13. Technical Debt

| Item | Severity | Notes |
|---|---|---|
| No persistent storage | Medium | Schema in `docs/database.md`; never implemented |
| Replay uses client-side history | Low | `GET /replay/frames` backend endpoint exists but unused by frontend |
| `simulation/scenarios.py` grows linearly | Low | Would need a directory-per-scenario structure at 10+ scenarios |
| Original `docs/` files not retroactively updated | Very low | `docs/architecture.md`, `docs/api-design.md`, etc. reflect Phase 1 design intent, not final implementation details |

---

## 14. Recommended Next Milestone

**Version 2 — Theme: Real-World Readiness**

The MVP is software-complete but fully synthetic. The recommended focus for Version 2 is making the system ready for real hardware and real-world validation.

**Priority order:**

1. **Persistent storage (SQLite)** — Least risky, highest value. Enables mission history, server-side replay, and session continuity. Schema already designed in `docs/database.md`.

2. **Probabilistic perception detector** — Replace `GroundTruthDetector` with a detector that has configurable uncertainty (false positive/negative rates). Makes the system behave like real sensors and exercises the alert deduplication logic meaningfully.

3. **Dynamic fire spread** — Add propagation logic to `SimulationRunner` so hazard levels change during a mission. Produces varied, realistic sensor readings rather than fixed per-zone values.

4. **Hardware adapter** — Implement a real drone adapter satisfying `backend/ingestion/interface.py`. The boundary is already in place; the adapter is the only new code needed.

5. **Scenario selection UI** — Add a scenario picker to the frontend so operators can switch scenarios without API calls.

None of these require architecture changes. All extend the existing seams.
