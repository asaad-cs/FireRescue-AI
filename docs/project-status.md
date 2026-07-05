# FireRescue AI — Project Status

**Version:** 1.0.0 (MVP, frozen) + Version 2 in progress  
**Date:** 2026-07-04 (MVP sections below reflect 2026-07-01)  
**Current Phase:** Version 2 — Phase AI.1 complete (model retrained on GPU + fully live-validated; verdict "Demo Ready with Minor Issues"). Everything from Phase 8K onward is uncommitted, awaiting checkpoint approval.  
**Overall Status:** Fully operational end to end, in both Production Mode and the new Demo Mode. 623 BE (+50 subtests) + 334 FE tests pass. 0 TypeScript errors.

---

## 0. Version 2 Status (2026-07-04)

The MVP below remains frozen and fully accurate. On top of it, Version 2
has delivered a complete AI vision loop:

| Phase | Deliverable | State |
|---|---|---|
| 8A/8B/8B.1 | AI workspace, YOLO training infrastructure, multi-model layout | Committed (`v2.0-phase-8c`) |
| 8C | Dataset engineering — 12,545 imgs / 32,783 boxes, validated clean | Committed (`v2.0-phase-8c`) |
| 8D | First trained model (yolov8n 5-epoch smoke test, val mAP50 0.509) + verified ONNX export | Committed (`v2.0-phase-8f`) |
| 8E | `YOLODetector` (ONNX Runtime) registered beside `ground_truth`; config-driven switching | Committed (`v2.0-phase-8f`) |
| 8F | Simulated drone camera — real photographs into `Frame.channels["rgb"]` per zone | Committed (`v2.0-phase-8f`) |
| 8G | Live AI Vision — analysed image + detections inside `MissionState.vision` | Committed (`v2.0-phase-8i1`) |
| 8H | Permanent image library `assets/simulation_dataset/` + export tool | Committed (`v2.0-phase-8i1`) |
| 8I.1 | EOC dashboard redesign — `MissionCamera` (video-ready), detection cards, ops panel | Committed (`v2.0-phase-8i1`) |
| 8J | Scene-aware dataset split — Roboflow-variant leakage fixed, dataset regenerated (8,783/2,515/1,247), 0-leakage verified, residual dHash overlap halved (16.9→8.0% val, 15.6→6.2% test) | Committed (`v2.0-phase-8j`) |
| 8K | Camera experience — mission-scoped no-repeat image pool, per-mission random mode (`seed: null`, logged effective seed) + MissionCamera redesigned as a live camera monitor (HUD, edge-aware labels, link states) | **Uncommitted** (see `docs/phase-8k-report.md`) |
| 9A | Dataset assessment (read-only) — training set is ~85% outdoor, near-zero building-interior imagery | Complete |
| 9B | Curation staging — found 58 residential + 18 indoor-training-facility real images, plus a 49-image toy-model trap | Complete |
| 9B promotion (10A.4) | 234 images promoted into `assets/simulation_dataset/_curation/{approved,manual_review,rejected}/` | Complete, **uncommitted** |
| 10A.1–10A.4 | Findings persisted; README dataset standard extended; Architecture-B folders built then reversed; **Architecture A decided as the sole final standard** | Complete |
| 10B.1 | Filesystem migrated to Architecture A only | Complete |
| Scene-aware design doc | Environment model, selection strategy, migration plan (chat-only) | Complete, **NOT implemented/approved** |
| Demo.1–Demo.3 | Isolated demo dataset built (156→202 imgs), validated, Demo Mode switch added (1 settings flag), live-verified end to end | Complete |
| Demo.4 | `ZoneImageProvider` recycle-boundary repetition bug fixed (12 lines, `provider.py`) | Complete |
| Demo.5–Demo.6 | Safe category expanded 2 → 48 images from existing repo assets only (raw unused COCO pool discovered) | Complete |
| AI.1 | Model retrained 60 epochs on GPU (RTX 3060 Ti); full old-vs-new comparison + 7-mission live validation | Complete — **B) Demo Ready with Minor Issues** |

Data flow now: Simulation → CameraSimAdapter (zone → real image) →
YOLODetector (ONNX) → DetectionResult → MissionState (incl. vision
payload) → redesigned dashboard. The frontend still receives ONLY
MissionState; REST/WebSocket contracts are unchanged; GroundTruthDetector
remains the committed default detector.

Full V2 detail, decisions, and next steps: `docs/session-context.md`
(authoritative) and `docs/handoff-report.md` §0.

---

## 1. What This Project Is

FireRescue AI is a personal research prototype — **not a commercial product, not a startup, not a production system**.

Goal: explore how a software-driven situational awareness system could assist firefighters operating inside burning buildings. A virtual drone explores a simulated building autonomously, a perception engine classifies hazards and detects victim signals, and an operator monitors a live tactical dashboard.

Everything runs in simulation. The architecture is explicitly hardware-agnostic; real drone sensor input can be wired in by replacing only the `SimAdapter` layer.

---

## 2. Architecture Overview

```
┌───────────────────────────────────────────────────────────────────────┐
│  Frontend Dashboard  (React 18 + TypeScript + Vite + Tailwind)        │
│  http://localhost:5173                                                 │
│                                                                        │
│  Zustand Store (4 slices) ← useWebSocket hook ← ws://localhost:8000   │
│  REST calls → /api/* → Vite proxy → http://localhost:8000             │
└────────────────────────────────────┬──────────────────────────────────┘
                                     │  WebSocket — full MissionState push
                                     │  REST — mission control + scenarios + replay
┌────────────────────────────────────▼──────────────────────────────────┐
│  Backend  (FastAPI + uvicorn)  http://localhost:8000                  │
│                                                                        │
│  Broadcaster ──┐                                                       │
│  MissionRecorder──┤← MissionManager ← Pipeline ← PerceptionEngine    │
│                │        ↑                                              │
│                │  SimAdapter → SimulationRunner (active scenario)      │
└────────────────┘──────────────────────────────────────────────────────┘
```

### The one unbreakable rule

**The frontend only ever receives `MissionState`.** It has no knowledge of `Frame`, `PerceptionResult`, `ZoneHistory`, or any internal backend type. All derived values are computed server-side.

---

## 3. Completed Phases

| Phase | Title | Description | Status |
|---|---|---|---|
| 0 | Project Foundation | Directory structure, `.gitignore`, documentation stubs | Complete |
| 1 | Architecture & Design | Full architectural blueprint in `docs/` | Complete |
| 2 | Simulation Engine | Building model, drone BFS, sensor emulation | Complete |
| 3 | Backend & Pipeline | FastAPI, MissionManager, Broadcaster, WebSocket | Complete |
| 4 | Full Integration | Auto-start mission, SimAdapter, end-to-end data flow | Complete |
| 5 | Perception Framework | GroundTruthDetector, DetectorRegistry, PerceptionEngine | Complete |
| 6A | Frontend Foundation | React, Zustand, WebSocket hook, dark theme, layout shell | Complete |
| 6B | Interactive Dashboard | All dashboard components, mission controls, alert panel | Complete |
| 7A | Visual Polish | Grid labels, pulsing animations, status indicators, statistics row | Complete |
| 7B | Multiple Scenarios | 5 building scenarios, scenario registry, activate endpoint | Complete |
| 7C | Mission Replay | MissionRecorder, replay slice, ReplayControls, useReplayEngine | Complete |
| — | MVP Documentation | README, developer guide, demo guide, project status | Complete |

---

## 4. Stable Modules

These modules are complete, fully tested, and frozen. Do not modify without clear justification.

### Backend

| Module | Path | Notes |
|---|---|---|
| Simulation engine | `simulation/` | All files — building, drone, sensors, scenarios, runner |
| Perception framework | `perception/` | All files — engine, hazard, victim, alerts, detector |
| MissionState models | `backend/models/` | Any change requires matching `types/mission.ts` update |
| Pipeline | `backend/pipeline/` | Validator, Enricher, Pipeline orchestrator |
| Mission manager | `backend/mission/manager.py` | Core state machine; never modify without full test coverage |
| Broadcaster | `backend/websocket/broadcaster.py` | WebSocket fan-out |
| DataSource interface | `backend/ingestion/interface.py` | Hardware independence boundary — must not change |

### Frontend

| Module | Path | Notes |
|---|---|---|
| Mission type definitions | `frontend/src/types/mission.ts` | Mirrors backend models exactly |
| Zustand store | `frontend/src/stores/missionStore.ts` | All four slices |
| WebSocket service | `frontend/src/services/websocket.ts` | Auto-reconnect logic |
| WebSocket hook | `frontend/src/hooks/useWebSocket.ts` | Lifecycle management |
| All test files | `frontend/src/**/__tests__/` | Do not weaken; only strengthen |

---

## 5. Current Module Inventory

### Backend test files (286 tests + 50 subtests)

| File | Tests | Covers |
|---|---|---|
| `backend/tests/test_models.py` | — | Pydantic models, enums, serialisation |
| `backend/tests/test_pipeline.py` | — | Validator, Enricher, Pipeline stages |
| `backend/tests/test_mission_manager.py` | — | State machine, Frame processing, notifications |
| `backend/tests/test_api.py` | — | REST endpoints, 409 transitions |
| `backend/tests/test_perception.py` | — | Hazard classifier, victim estimator, alert gen |
| `backend/tests/test_perception_engine.py` | — | PerceptionEngine orchestration |
| `backend/tests/test_scenarios_api.py` | 18 | Scenario list, activate, scenario switch on restart |
| `backend/tests/test_recorder.py` | 22 | MissionRecorder unit tests + replay API endpoints |
| `simulation/tests/test_building.py` | — | Zone connectivity, adjacency |
| `simulation/tests/test_drone.py` | — | BFS traversal, path completeness |
| `simulation/tests/test_runner.py` | — | Tick loop, completion callback |
| `simulation/tests/test_scenarios.py` | 28 + 50 subtests | All 5 scenarios, integrity, runner |
| `perception/tests/` (5 files) | — | Ground truth detector, registry, confidence |
| **Total** | **286 + 50 subtests** | Run: `python -m pytest` from project root |

### Frontend test files (295 tests)

| File | Tests | Covers |
|---|---|---|
| `stores/__tests__/missionStore.test.ts` | 55 | All 4 store slices including replay |
| `components/dashboard/__tests__/TacticalMap.test.tsx` | ~25 | Map grid, hazard colors, drone marker |
| `components/dashboard/__tests__/AlertPanel.test.tsx` | ~25 | Alert rendering, priority, acknowledgement |
| `components/dashboard/__tests__/DroneStatus.test.tsx` | ~20 | Drone state display, progress bars |
| `components/dashboard/__tests__/VictimSignals.test.tsx` | ~20 | Victim signal display, thresholds |
| `components/dashboard/__tests__/MissionTimeline.test.tsx` | ~20 | Timeline event chips |
| `components/dashboard/__tests__/MissionStatistics.test.tsx` | 10 | Stats row: explored%, elapsed, counts |
| `components/dashboard/__tests__/MissionControls.test.tsx` | ~40 | Button states, callbacks, REPLAY button |
| `components/dashboard/__tests__/ReplayControls.test.tsx` | 36 | Replay panel, speed, pause/resume/exit |
| `components/layout/__tests__/AppLayout.test.tsx` | ~20 | Layout shell, connection banner |
| `components/placeholders/__tests__/Placeholders.test.tsx` | ~15 | Placeholder stubs |
| `services/__tests__/api.test.ts` | 10 | REST client calls |
| `services/__tests__/websocket.test.ts` | ~25 | WebSocket service, reconnect, message parsing |
| `utils/__tests__/format.test.ts` | ~30 | All formatting helpers |

---

## 6. REST API — Current State

| Method | Endpoint | Description |
|---|---|---|
| GET | `/` | Service info |
| GET | `/health` | Liveness check |
| POST | `/mission/start` | IDLE/PAUSED → ACTIVE; restarts from ENDED |
| POST | `/mission/pause` | ACTIVE → PAUSED |
| POST | `/mission/resume` | PAUSED → ACTIVE |
| POST | `/mission/end` | Any → ENDED |
| GET | `/scenarios` | List all scenarios + active scenario key |
| POST | `/scenarios/{key}/activate` | Set active scenario for next mission |
| GET | `/replay/frames` | Full recorded MissionState history |
| GET | `/replay/frames/count` | Number of recorded frames |

**WebSocket:** `ws://localhost:8000/ws` — push-only, full `MissionState` JSON per state change

---

## 7. Simulation Scenarios

| Key | Display Name | Zones | Notable Hazard |
|---|---|---|---|
| `warehouse_alpha` | Warehouse Alpha | 20 (5×4) | Loading Dock — CRITICAL |
| `office_building` | Office Building | 12 (4×3) | Server Room — CRITICAL |
| `hospital` | Hospital | 16 (4×4) | Boiler Room — CRITICAL |
| `shopping_mall` | Shopping Mall | 15 (5×3) | Utility Room — CRITICAL |
| `school` | School | 16 (4×4) | Science Lab — CRITICAL |

Each scenario defines: zones, connections, hazard levels, victim positions, and start zone.

---

## 8. Known Limitations

### Functional limitations

1. **In-memory state only.** No database. Restarting the backend loses all mission history. The `docs/database.md` schema was designed but never implemented.

2. **No real-time sensor variation.** Sensor readings are deterministic functions of zone properties. Temperature, CO, and smoke are fixed values per zone; they do not change over time during a mission.

3. **One drone per mission.** The architecture supports one `SimulationRunner` instance per active mission. Multi-drone support would require significant MissionManager changes.

4. **No persistent alert acknowledgements.** Acknowledged alert IDs live in the Zustand `UISlice` and reset on page reload or mission restart.

5. **No scenario selection UI.** Scenario switching requires a direct API call (`POST /scenarios/{key}/activate`). There is no frontend picker.

6. **Ground-truth perception only.** `GroundTruthDetector` reads from static maps. No probabilistic inference, no ML, no false positives or false negatives.

### Technical limitations

7. **No authentication or access control.** The API and WebSocket are open. This is a local research tool only.

8. **Replay is client-side only.** The frontend records `MissionState` frames locally as the mission runs. If the page is reloaded mid-mission, recorded history is lost. The `GET /replay/frames` backend endpoint exists but is not used for frontend replay (the local in-memory history is used instead).

9. **Single WebSocket connection per tab.** Multiple browser tabs receive independent state from the same backend, but each tab's replay history is independent.

---

## 9. Technical Debt

| Item | Severity | Notes |
|---|---|---|
| No persistent storage | Medium | Planned in `docs/database.md`; not built. Mission data lost on backend restart. |
| Replay uses local client history, not backend endpoint | Low | `GET /replay/frames` exists but the frontend uses its in-memory history instead. The endpoint enables future server-driven replay. |
| `simulation/scenarios.py` grows linearly | Low | Each scenario is a function in one file. A directory-per-scenario structure would be cleaner at 10+ scenarios. |
| `docs/roadmap.md` phase numbering | Low | Original roadmap used Phases 0–7 with different meanings. Implementation followed a revised phase numbering. The old roadmap file is not updated. |
| `wsStatus` is a string union, not an enum | Very low | Consistent throughout; minor type safety improvement only. |

---

## 10. Architectural Constraints — Must Never Be Broken

1. **Frontend receives only `MissionState`.** Never expose `Frame`, `PerceptionResult`, `ZoneHistory`, or any internal backend type to the frontend.

2. **The DataSource interface is the hardware boundary.** `backend/ingestion/interface.py` is the only seam between the simulation (or future hardware) and the backend. Nothing upstream of this boundary should change when hardware is added.

3. **MissionManager is the single source of truth.** No component computes mission state independently. Everything derives from `manager.get_state()`.

4. **Dashboard components are pure UI.** They receive props from layout components. They do not read the Zustand store directly. This makes them testable without store mocking.

5. **Inline styles for dynamic CSS values.** Any CSS property derived from a runtime value (e.g. hazard level colour) must use `style={{}}` not a dynamic `className=`. Tailwind purges class names that do not appear as literal strings in source.

6. **Scenario instances are never cached.** `SCENARIO_REGISTRY` stores factory functions, not instances. Every `get_scenario(key)` call returns a fresh, independent `Scenario` object.

---

## 11. Version Roadmap

| Version | What it represents | Status |
|---|---|---|
| 0.1 – 0.5 | Phases 0–5: simulation, backend, perception, full integration | Complete |
| 0.6 | Phases 6A–6B: frontend foundation + interactive dashboard | Complete |
| 0.7 | Phases 7A–7C + docs: visual polish, scenarios, replay, documentation | **Current** |
| 0.8 | Persistent storage (SQLite), mission history endpoint | Not planned |
| 0.9 | Probabilistic perception detector with configurable noise | Not planned |
| 1.0 | Dynamic fire spread, hardware adapter stub | Not planned |

---

## 12. How to Run the Application

**Prerequisites:** Python 3.12+, Node.js 18+

```bash
# One-time setup
pip install -r requirements.txt
cd frontend && npm install && cd ..

# Terminal 1 — Backend
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --ws websockets

# Terminal 2 — Frontend
cd frontend && npm run dev
```

Open `http://localhost:5173`.

```bash
# Run all tests
python -m pytest                       # 286 backend tests + 50 subtests
cd frontend && npx vitest run          # 295 frontend tests
```

---

*Generated 2026-07-01. Reflects state after Phase 7C (Mission Replay) completion.*
