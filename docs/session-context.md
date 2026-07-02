# FireRescue AI — Future Session Context

> Paste this document at the start of any new AI session to provide complete project context without reading the repository.

---

## What Is FireRescue AI?

FireRescue AI is a personal software research prototype — NOT a commercial product, NOT a startup, NOT a production system. It explores how an AI-assisted situational awareness system could support firefighters operating inside burning buildings.

A virtual drone explores a simulated building using breadth-first search, sensors detect hazards and victim signals, and an operator monitors a live tactical dashboard. Everything runs in software simulation. The architecture is explicitly hardware-agnostic: real sensor input can be wired in by replacing a single adapter class.

**Version:** 1.0.0 (MVP complete, all phases locked)  
**Stack:** Python 3.12 + FastAPI (backend) · React 18 + TypeScript + Vite + Tailwind + Zustand (frontend)

---

## Project Goals

1. Build a clean, well-tested simulation-first software foundation
2. Demonstrate real-time situational awareness with a live operator dashboard
3. Keep the architecture hardware-agnostic so real drone sensors can be added later
4. Serve as a research, portfolio, and demonstration artifact

---

## Complete Software Architecture

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

---

## Every Completed Phase

| Phase | Title | Key Deliverables |
|---|---|---|
| 0 | Project Foundation | Directory structure, .gitignore, doc stubs |
| 1 | Architecture & Design | 8 design documents in docs/ |
| 2 | Simulation Engine | `environment.py`, `drone.py` (BFS), `sensors.py`, `scenarios.py`, `runner.py` |
| 3 | Backend & Pipeline | FastAPI app, MissionManager, Pipeline (Validate→Enrich), Broadcaster, REST API |
| 4 | Full Integration | Auto-start mission, SimAdapter asyncio task, restart from ENDED |
| 5 | Perception Framework | GroundTruthDetector, DetectorRegistry, PerceptionEngine, hazard/victim/alerts |
| 6A | Frontend Foundation | React 18, Zustand, WebSocket service + hook, dark theme, layout shell |
| 6B | Interactive Dashboard | TacticalMap, AlertPanel, DroneStatus, VictimSignals, MissionControls, MissionTimeline, ActivityFeed, ConnectionBanner |
| 7A | Visual Polish | CSS animations, grid labels, MissionStatistics row, TopNavigation badge |
| 7B | Multiple Scenarios | 5 building scenarios, scenario registry, GET/POST /scenarios endpoints, detector rebuild on switch |
| 7C | Mission Replay | MissionRecorder, ReplaySlice in Zustand, useReplayEngine hook, ReplayControls component |
| — | MVP Docs | README, developer-guide.md, demo-guide.md, project-status.md, roadmap.md, handoff-report.md |

---

## Major Architectural Decisions That Must Never Be Broken

**1. Frontend receives only `MissionState`**  
Never expose `Frame`, `PerceptionResult`, `ZoneHistory`, or any internal backend type to the frontend.

**2. DataSource interface is the hardware boundary**  
`backend/ingestion/interface.py` is the only seam between simulation (or future hardware) and the backend. Nothing upstream changes when hardware is added.

**3. MissionManager is the single source of truth**  
No component independently computes mission state. Everything derives from `manager.get_state()`.

**4. Dashboard components are pure UI**  
Dashboard components receive props from layout components. They do not read the Zustand store directly. This makes them testable without store mocking.

**5. Inline styles for dynamic CSS values**  
Any CSS property derived from a runtime value (e.g. hazard level colour) must use `style={{}}`, not a dynamic `className=`. Tailwind purges dynamic class names.

**6. Scenario instances are never cached**  
`SCENARIO_REGISTRY` stores factory functions, not instances. Every `get_scenario(key)` call returns a fresh, independent `Scenario` object.

**7. State-change listener pattern**  
Components that need to react to every `MissionState` update implement `on_state_change(state: MissionState)` and register via `manager.register_state_change()`. No polling, no shared mutable state between listeners.

---

## Stable Modules — Do Not Modify Without Reason

These are frozen at MVP v1.0:

- `simulation/` — all files (building, drone, sensors, scenarios, registry, runner)
- `perception/` — all files (engine, hazard, victim, alerts, detector, registry)
- `backend/models/` — Pydantic models (any change requires matching `types/mission.ts` update)
- `backend/pipeline/` — all files
- `backend/mission/manager.py` — core state machine
- `backend/mission/recorder.py` — MissionRecorder
- `backend/websocket/broadcaster.py`
- `backend/ingestion/` — both files (the hardware boundary)
- `frontend/src/types/mission.ts` — mirrors backend models exactly
- `frontend/src/stores/missionStore.ts` — all four slices
- `frontend/src/services/websocket.ts`
- `frontend/src/hooks/useWebSocket.ts`
- `frontend/src/hooks/useReplayEngine.ts`
- All test files

---

## Current API Surface

### REST (http://localhost:8000)

```
GET  /                          Service info
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

### WebSocket (ws://localhost:8000/ws)

Push-only. Full `MissionState` JSON on every state change. Current state pushed immediately on connect.

---

## Simulation Scenarios

Five building scenarios available. Default: Warehouse Alpha.

| Key | Zones | Notable hazard |
|---|---|---|
| `warehouse_alpha` | 20 (5×4) | Loading Dock — CRITICAL |
| `office_building` | 12 (4×3) | Server Room — CRITICAL |
| `hospital` | 16 (4×4) | Boiler Room — CRITICAL |
| `shopping_mall` | 15 (5×3) | Utility Room — CRITICAL |
| `school` | 16 (4×4) | Science Lab — CRITICAL |

---

## Mission Replay System

- `MissionRecorder` (backend) deep-copies every `MissionState` into `_history`
- Frontend `setMissionState` appends frames to `replayHistory` in the Zustand store
- On mission end: REPLAY button appears in `MissionControls`
- Click REPLAY → `startReplay()` → `isReplaying = true`, `missionState` rewinds to frame 0
- `useReplayEngine` fires `stepReplay()` at 0.5×/1×/2× speed via `setInterval`
- `ReplayControls` replaces `MissionControls` in the nav bar
- EXIT → restores `finalMissionState`, replay state cleared
- WS messages for the same `mission_id` are ignored during replay

---

## Test Counts (MVP v1.0)

```
Backend:    286 tests  +  50 subtests  (python -m pytest)
Frontend:   295 tests                  (npx vitest run)
TypeScript: 0 errors                   (npx tsc --noEmit)
```

---

## Known Limitations at MVP v1.0

1. No database — in-memory state only; backend restart clears history
2. No scenario selection UI — switching requires a REST API call
3. Deterministic sensor data — fixed values per zone, no real-time variation
4. Ground-truth perception only — no false positives, no ML inference
5. One drone per mission
6. No persistent alert acknowledgements — reset on page reload
7. No authentication — local research tool only
8. Client-side replay history — page reload during mission loses recorded frames

---

## What Version 2 Will Focus On

Version 2 is not planned. When started, the recommended focus is:

1. **Persistent storage (SQLite)** — Schema in `docs/database.md`. Enables mission history and server-side replay. Lowest risk.
2. **Probabilistic perception** — Replace `GroundTruthDetector` with a configurable-noise detector to model real sensor uncertainty.
3. **Dynamic fire spread** — Hazard levels propagate to adjacent zones over time.
4. **Hardware adapter** — Implement a real adapter satisfying `backend/ingestion/interface.py`. Only new code needed; nothing upstream changes.
5. **Scenario selection UI** — Frontend picker for the 5 (or more) scenarios.

**Constraints that remain in Version 2:**
- No authentication
- No analytics dashboards (bar charts, pie charts, BI widgets)
- No cloud infrastructure
- No mobile optimization
- "STOP after each phase, wait for user instruction" still applies

---

## How to Start the Application

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
python -m pytest               # Backend: 286 + 50
cd frontend && npx vitest run  # Frontend: 295
```
