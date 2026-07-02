# FireRescue AI

A simulation-first research prototype that provides real-time situational awareness for firefighters operating inside dangerous buildings. A virtual drone explores a building autonomously, sensors detect hazards and victim signals, and an operator monitors a live tactical dashboard.

**Version: 1.0.0 — MVP complete. All phases locked.**

---

## Overview

FireRescue AI explores how an AI-assisted situational awareness system could support first responders in high-risk, low-visibility environments. The system runs entirely in software simulation — no hardware is required — while being architecturally designed to accept real drone sensor input by replacing a single adapter layer.

This is a personal research and engineering project. It is not a commercial product and is not intended for deployment in real emergency operations.

---

## Architecture

```
┌───────────────────────────────────────────────────────────────────────┐
│  Operator Dashboard  (React 18 + TypeScript + Vite + Tailwind)        │
│  http://localhost:5173                                                 │
│                                                                        │
│  Zustand Store ← useWebSocket hook ← ws://localhost:8000/ws           │
│  REST calls → /api/* (Vite proxy) → http://localhost:8000             │
└───────────────────────────────────┬───────────────────────────────────┘
                                    │  WebSocket — MissionState push
                                    │  REST — mission control
┌───────────────────────────────────▼───────────────────────────────────┐
│  Backend  (FastAPI + uvicorn)  http://localhost:8000                  │
│                                                                        │
│  Broadcaster ──┐                                                       │
│  Recorder ─────┤← MissionManager ← Pipeline ← PerceptionEngine       │
│                │        ↑                                              │
│                │   SimAdapter → SimulationRunner (active scenario)     │
└────────────────┘───────────────────────────────────────────────────────┘
```

### Data flow — one simulation tick

1. `SimulationRunner` moves the drone to the next zone, generates a `Frame` (pose + sensor channels)
2. `SimAdapter` delivers the `Frame` to `MissionManager.on_frame()`
3. `MissionManager` sends the `Frame` through the `Pipeline`: Validate → Enrich → `PerceptionEngine`
4. `PerceptionEngine` returns a `PerceptionResult` (hazard level, victim probability, any new alerts)
5. `MissionManager` merges the result into `MissionState` and notifies all registered listeners
6. `Broadcaster` fans the full `MissionState` as JSON to all connected WebSocket clients
7. `Recorder` stores a deep copy of the `MissionState` for later replay
8. The frontend `useWebSocket` hook receives the message, calls `setMissionState()` in Zustand
9. React components re-render with the updated state

### The one architectural invariant

**The frontend only ever receives `MissionState`.** It has no knowledge of `Frame`, `PerceptionResult`, `ZoneHistory`, or any internal backend type. All derived values — alert counts, explored percentage, victim signal count — are computed server-side and included in `MissionState`.

---

## Module Structure

```
FireRescue-AI/
│
├── backend/                         FastAPI application
│   ├── main.py                      App entry point, lifespan, WebSocket endpoint
│   ├── api/routes.py                REST endpoints (mission control, scenarios, replay)
│   ├── config/settings.py           All tuneable values (tick rate, ports, etc.)
│   ├── mission/
│   │   ├── manager.py               Mission state machine, Frame processing
│   │   └── recorder.py              Records every MissionState snapshot for replay
│   ├── models/
│   │   ├── mission_state.py         MissionState + sub-models + enums (Pydantic)
│   │   ├── alert.py                 Alert model
│   │   └── frame.py                 Frame model (internal; never sent to frontend)
│   ├── pipeline/
│   │   ├── pipeline.py              Orchestrates: Validator → Enricher → PerceptionEngine
│   │   ├── validator.py             Frame schema + mission context validation
│   │   └── enricher.py              Resolves drone pose (x, y, floor) → zone_id + label
│   ├── ingestion/
│   │   ├── interface.py             DataSource protocol — the hardware independence boundary
│   │   └── sim_adapter.py           Adapts SimulationRunner to the DataSource interface
│   ├── websocket/broadcaster.py     Fans MissionState JSON to all WebSocket clients
│   ├── utils/logger.py              Structured logger
│   └── tests/                       141 tests + 20 subtests (pytest)
│
├── simulation/                      Simulation engine
│   ├── environment.py               Building, Floor, Zone models
│   ├── drone.py                     BFS zone exploration logic
│   ├── sensors.py                   Environmental channel generation (temp, CO, smoke)
│   ├── scenarios.py                 Five named scenario factory functions
│   ├── scenario_registry.py         Registry of all available scenarios + metadata
│   ├── runner.py                    Async tick loop (one-shot, new instance per mission)
│   └── tests/                       84 tests + 30 subtests (included in the 286 total)
│
├── perception/                      Perception framework
│   ├── engine.py                    Orchestrator: process(Frame, ZoneHistory) → PerceptionResult
│   ├── hazard.py                    HazardLevel classifier (NONE/LOW/MODERATE/HIGH/CRITICAL)
│   ├── victim.py                    Victim signal probability estimator
│   ├── alerts.py                    Alert generator with deduplication
│   ├── types.py                     ZoneHistory type
│   ├── base/detector.py             BaseDetector abstract class
│   ├── results/detection.py         PerceptionResult type
│   ├── registry/registry.py         Detector registry (name → detector instance)
│   ├── detectors/ground_truth.py    Reads static hazard/victim maps from the active scenario
│   └── tests/                       61 tests (included in the 286 total)
│
├── frontend/                        Operator dashboard
│   ├── src/
│   │   ├── types/mission.ts         TypeScript interfaces mirroring backend Pydantic models
│   │   ├── stores/missionStore.ts   Zustand store (connection + mission + ui + replay slices)
│   │   ├── services/
│   │   │   ├── websocket.ts         WebSocket service with auto-reconnect
│   │   │   └── api.ts               REST client (mission control calls)
│   │   ├── hooks/
│   │   │   ├── useWebSocket.ts      WebSocket lifecycle hook
│   │   │   └── useReplayEngine.ts   Interval-driven replay tick engine
│   │   ├── utils/format.ts          Display helpers (elapsed, percentage, truncation)
│   │   ├── components/
│   │   │   ├── layout/              AppLayout, TopNavigation, MainWorkspace,
│   │   │   │                        RightSidebar, BottomTimeline
│   │   │   ├── dashboard/           TacticalMap, AlertPanel, DroneStatus, VictimSignals,
│   │   │   │                        MissionTimeline, ActivityFeed, MissionControls,
│   │   │   │                        MissionStatistics, ReplayControls, ConnectionBanner
│   │   │   └── placeholders/        ConnectionIndicator (in use); archived stubs
│   │   └── pages/Dashboard.tsx      Single page — renders AppLayout
│   └── package.json / vite.config.ts / tailwind.config.ts / tsconfig.json
│
├── docs/                            Architecture and operational documentation
├── requirements.txt                 Python dependencies
└── README.md
```

---

## Tech Stack

| Layer | Technology | Version |
|---|---|---|
| Backend | Python + FastAPI + uvicorn | Python 3.12, FastAPI 0.111 |
| Frontend | React + TypeScript + Vite | React 18, TS 5.5, Vite 5.4 |
| Styling | Tailwind CSS | 3.4 |
| State management | Zustand | 4.5 |
| Backend tests | pytest | 8.x |
| Frontend tests | Vitest + Testing Library | Vitest 2.x |
| Data validation | Pydantic | v2 |

---

## Simulation Scenarios

Five building scenarios are available. The default on startup is **Warehouse Alpha**.

| Scenario | Zones | Description |
|---|---|---|
| `warehouse_alpha` | 20 (5×4) | Industrial warehouse with loading dock fire — default |
| `office_building` | 12 (4×3) | Multi-floor office with server room fire |
| `hospital` | 16 (4×4) | Hospital wing with boiler room fire |
| `shopping_mall` | 15 (5×3) | Multi-level mall with utility room fire |
| `school` | 16 (4×4) | School building with science lab fire |

Switch scenarios via the REST API before starting a new mission:

```bash
curl -X POST http://localhost:8000/scenarios/hospital/activate
curl -X POST http://localhost:8000/mission/start
```

---

## Installation

**Prerequisites:** Python 3.12+, Node.js 18+

```bash
# Clone and enter the project
git clone <repo-url>
cd FireRescue-AI

# Backend dependencies
pip install -r requirements.txt

# Frontend dependencies
cd frontend && npm install && cd ..
```

---

## Running the Backend

```bash
# From the project root
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --ws websockets
```

The simulation starts automatically. The drone explores the Warehouse Alpha scenario (20 zones) in approximately 20 seconds at the default 1-second tick rate.

**Configurable settings** (`backend/config/settings.py`):

| Setting | Default | Description |
|---|---|---|
| `api_port` | `8000` | Backend HTTP port |
| `sim_tick_interval_seconds` | `1.0` | Seconds between simulation ticks |
| `max_zone_history` | `20` | Recent frames kept per zone for perception |
| `perception_detector` | `"ground_truth"` | Active detector name |

---

## Running the Frontend

```bash
# From the frontend/ directory
npm run dev
```

Open `http://localhost:5173` in a browser. The frontend proxies `/api/*` and `/ws` to `http://localhost:8000` automatically.

---

## Running Tests

```bash
# Backend — from the project root
python -m pytest

# Frontend — from the frontend/ directory
npx vitest run

# TypeScript type check
cd frontend && npx tsc --noEmit
```

**Test counts:** 286 backend tests (+ 50 subtests) · 295 frontend tests

---

## REST API

| Method | Path | Description |
|---|---|---|
| GET | `/` | Service info (`name`, `version`, `status`) |
| GET | `/health` | Liveness check |
| POST | `/mission/start` | IDLE/PAUSED → ACTIVE; restarts from ENDED with fresh simulation |
| POST | `/mission/pause` | ACTIVE → PAUSED |
| POST | `/mission/resume` | PAUSED → ACTIVE |
| POST | `/mission/end` | Any → ENDED |
| GET | `/scenarios` | List all scenarios + active scenario key |
| POST | `/scenarios/{key}/activate` | Set active scenario for next mission |
| GET | `/replay/frames` | Full recorded MissionState history for current/last mission |
| GET | `/replay/frames/count` | Number of recorded frames |

**WebSocket:** `ws://localhost:8000/ws`
Push-only (server → client). Payload: full `MissionState` JSON on every state change. Current state is pushed immediately on connect.

---

## Demo Workflow

1. Start the backend and frontend (see above)
2. The dashboard connects automatically and the mission begins
3. Watch the drone marker move across the **Tactical Map** as it explores zones
4. Hazard colors appear on zones as the drone visits them (grey → amber → orange → red)
5. **Alerts** appear in the right sidebar as the drone enters hazardous zones
6. **Victim signals** populate as the drone detects survivor probability
7. When the mission completes (all zones explored), click **NEW MISSION** to restart
8. Or click **REPLAY** to step through the recorded mission at 0.5×, 1×, or 2× speed
9. To try a different building, call `POST /scenarios/{key}/activate` then **NEW MISSION**

---

## Screenshots

> Add screenshots here after a live demo session.

Suggested captures:
- Dashboard at mission start (drone at first zone)
- Dashboard mid-mission (several zones explored, alerts visible)
- Dashboard at mission end (all zones explored, ENDED state)
- Replay controls visible in the navigation bar

---

## Roadmap

| Phase | Title | Status |
|---|---|---|
| 0 | Project Foundation | Complete |
| 1 | Architecture & Design | Complete |
| 2 | Simulation Engine | Complete |
| 3 | Backend & Pipeline | Complete |
| 4 | Full Integration | Complete |
| 5 | Perception Framework | Complete |
| 6A | Frontend Foundation | Complete |
| 6B | Interactive Dashboard | Complete |
| 7A | Visual Polish | Complete |
| 7B | Multiple Scenarios | Complete |
| 7C | Mission Replay | Complete |
| — | MVP Documentation | Complete |

---

## Future Work

The system is architecture-ready for these extensions. None are planned.

**Persistent storage** — Store missions, frames, and alerts in SQLite so history survives backend restarts. The schema is designed in `docs/database.md`.

**Hardware adapter** — Replace `SimAdapter` with a real drone sensor adapter. Nothing upstream changes — the `DataSource` protocol in `backend/ingestion/interface.py` is the only seam.

**Probabilistic detector** — Replace `GroundTruthDetector` with a detector that has configurable false-positive / false-negative rates to simulate real sensor uncertainty.

**Dynamic fire spread** — Add fire propagation logic to `SimulationRunner` so hazard levels evolve during a mission rather than being fixed per zone.

---

## Notes

This project is built for research, portfolio, and demonstration purposes. It is not a commercial product, not a startup, and not intended for deployment in real emergency operations.
