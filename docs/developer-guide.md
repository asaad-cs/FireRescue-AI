# FireRescue AI — Developer Guide

**Version:** 1.0.0  
**Date:** 2026-07-01  
**Reflects:** MVP v1.0 — all phases complete and locked

---

## 1. Prerequisites

| Tool | Minimum version | Notes |
|---|---|---|
| Python | 3.12 | Backend + simulation + perception |
| Node.js | 18.x | Frontend toolchain |
| npm | 9.x | Bundled with Node 18 |

No database, no message broker, no Docker required for local development.

---

## 2. First-time Setup

```bash
# 1. Install Python dependencies (from project root)
pip install -r requirements.txt

# 2. Install frontend dependencies
cd frontend
npm install
cd ..
```

---

## 3. Starting the Application

Open two terminal windows.

**Terminal 1 — Backend:**
```bash
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --ws websockets
```

**Terminal 2 — Frontend:**
```bash
cd frontend
npm run dev
```

Open `http://localhost:5173`. The simulation starts automatically.

---

## 4. Running Tests

```bash
# All backend tests (from project root)
python -m pytest

# Specific modules
python -m pytest backend/tests/
python -m pytest simulation/tests/
python -m pytest perception/tests/

# All frontend tests (from frontend/)
npx vitest run

# Watch mode during development
npx vitest

# TypeScript check
npx tsc --noEmit
```

**Current counts:** 286 backend tests (+ 50 subtests) · 295 frontend tests · 0 TypeScript errors

---

## 5. Backend Architecture

### Entry point

`backend/main.py` contains the FastAPI `lifespan` context manager that wires the entire system:

```
lifespan():
  1. Build scenario (default: Warehouse Alpha)
  2. Initialise GroundTruthDetector with scenario's hazard/victim maps
  3. Build Pipeline (Validator → Enricher → PerceptionEngine)
  4. Instantiate MissionManager with the Pipeline
  5. Instantiate Broadcaster → register as state-change listener
  6. Instantiate MissionRecorder → register as state-change listener
  7. Build SimulationRunner for the scenario
  8. Create + start the mission
  9. Launch SimAdapter as an asyncio task
  10. Expose all components via app.state.*
```

### MissionManager state machine

```
IDLE ──start──► ACTIVE ──pause──► PAUSED ──resume──► ACTIVE
                   │                  │
                   └────end───────────┘
                              │
                            ENDED ──start──► new IDLE → ACTIVE
```

`start_mission()` from ENDED creates a fresh `SimulationRunner` for the currently active scenario, resets the `MissionRecorder`, rebuilds the `GroundTruthDetector`, and launches a new `SimAdapter` task.

### State-change listener pattern

Any component that needs to react to every `MissionState` update implements:

```python
def on_state_change(self, state: MissionState) -> None: ...
```

and registers via:

```python
manager.register_state_change(my_listener.on_state_change)
```

`Broadcaster` and `MissionRecorder` both use this pattern. No polling. No shared mutable state between listeners.

### Pipeline stages

```
Frame (raw sensor data + drone pose)
  │
  ▼ Validator    — checks schema validity + mission context
  │
  ▼ Enricher     — resolves (x, y, floor) → zone_id, zone_label via scenario graph
  │
  ▼ PerceptionEngine → GroundTruthDetector
  │               — returns HazardLevel, victim probability, new alerts
  ▼
MissionState updated
```

### MissionRecorder

`backend/mission/recorder.py` — records a `model_copy(deep=True)` of every `MissionState` broadcast. Called on the same asyncio event loop as the manager, so no locking is needed. Exposes:

- `on_state_change(state)` — append snapshot
- `get_history()` — return list copy
- `frame_count()` — length
- `reset()` — clear on new mission

### Replay API endpoints

| Endpoint | Purpose |
|---|---|
| `GET /replay/frames` | Full recorded history as `List[MissionState]` |
| `GET /replay/frames/count` | Number of recorded frames |

These endpoints are read-only. Replay playback itself is entirely client-driven.

---

## 6. Simulation Module

### Scenario registry

`simulation/scenario_registry.py` holds a `Dict[str, Callable[[], Scenario]]`. Factory functions are called on demand — never cached — so each call returns a fresh, independent `Scenario` instance.

```python
from simulation.scenario_registry import get_scenario, list_scenarios

scenario = get_scenario("hospital")   # fresh instance every call
meta = list_scenarios()               # list of dicts with key, display_name, zone_count
```

### Adding a new scenario

1. Add a building factory function to `simulation/environment.py` (follow the pattern of `build_warehouse_alpha()`)
2. Add a scenario factory function to `simulation/scenarios.py` (defines hazards, victims, start zone)
3. Register it in `SCENARIO_REGISTRY` in `simulation/scenario_registry.py`
4. Add metadata to `SCENARIO_METADATA` in the same file
5. Add tests to `simulation/tests/test_scenarios.py`

The rest of the system picks it up automatically.

### Drone exploration

`simulation/drone.py` — BFS from the start zone, visiting every zone exactly once. The BFS order is deterministic given a fixed adjacency graph, so the same scenario always produces the same `Frame` sequence. One `SimulationRunner` instance per mission; replaced on restart.

---

## 7. Perception Module

### GroundTruthDetector

`perception/detectors/ground_truth.py` reads static maps injected at construction time:

```python
hazard_map: Dict[zone_id, HazardLevel]
victim_map: Dict[zone_id, detection_probability]
```

These maps are built from the scenario at startup (and on scenario switch). The detector does no ML inference — it returns ground-truth values from the scenario definition.

### Adding a new detector

1. Create `perception/detectors/my_detector.py` subclassing `BaseDetector`
2. Implement `initialize()`, `process(frame, zone_history) → PerceptionResult`, `shutdown()`
3. Register it at startup: `registry.register("my_detector", MyDetector(...))`
4. Set `perception_detector = "my_detector"` in `Settings`

---

## 8. Frontend Architecture

### Zustand store slices

`frontend/src/stores/missionStore.ts` is one store with four logical slices:

| Slice | Key state | Key actions |
|---|---|---|
| **Connection** | `wsStatus`, `reconnectAttempts` | `setWsStatus`, `incrementReconnectAttempts` |
| **Mission** | `missionState`, `lastUpdatedAt` | `setMissionState`, `clearMissionState` |
| **UI** | `isSidebarCollapsed`, `acknowledgedAlertIds` | `toggleSidebar`, `acknowledgeAlert` |
| **Replay** | `isReplaying`, `replayHistory`, `replayIndex`, `replaySpeed` | `startReplay`, `stepReplay`, `exitReplay` |

`setMissionState` has three behaviours:
- **New mission** (`prev.missionState === null` or different `mission_id`): resets all replay state, starts fresh `replayHistory`
- **Live update** (same `mission_id`, not replaying): appends frame to `replayHistory`
- **During replay** (same `mission_id`, `isReplaying = true`): no-op (WebSocket updates are ignored while replay is driving `missionState`)

### Replay engine

`frontend/src/hooks/useReplayEngine.ts` — mounted once in `AppLayout`. Sets a `setInterval` that calls `stepReplay()` at the interval appropriate for the current speed:

| Speed | Interval |
|---|---|
| 0.5× | 2000 ms |
| 1× | 1000 ms |
| 2× | 500 ms |

The interval is torn down and rebuilt whenever `isReplaying`, `replayPaused`, or `replaySpeed` changes.

### Component rules

1. **Dashboard components receive only props** — they do not read the Zustand store directly. This keeps them testable without store mocking.
2. **Layout components** (`TopNavigation`, `RightSidebar`, etc.) read the store and pass props down.
3. **Inline styles for dynamic values** — any CSS property derived from runtime data (e.g. hazard level colour) must use `style={{}}` not a dynamic `className=`. Tailwind purges classes that do not appear as literal strings in source.
4. **`ReplayControls`** reads the store directly — it is a pure control surface with no props and no data display.

### Vite proxy

`frontend/vite.config.ts` proxies `/api` and `/ws` to `http://localhost:8000`:

```ts
proxy: {
  '/api': 'http://localhost:8000',
  '/ws':  { target: 'ws://localhost:8000', ws: true }
}
```

All API calls and the WebSocket URL use the relative `/api/` and `/ws` prefix.

---

## 9. REST API Reference

All endpoints respond with JSON. Error responses use standard HTTP status codes.

### Mission control

```
POST /mission/start    IDLE/PAUSED → ACTIVE; restarts simulation from ENDED
POST /mission/pause    ACTIVE → PAUSED             409 if not ACTIVE
POST /mission/resume   PAUSED → ACTIVE             409 if not PAUSED
POST /mission/end      Any non-ENDED → ENDED       409 if already ENDED
```

Response shape (all mission endpoints):
```json
{ "status": "started", "mission_id": "abc12345-..." }
```

### Scenario management

```
GET  /scenarios                  → { "active": "warehouse_alpha", "scenarios": [...] }
POST /scenarios/{key}/activate   → { "activated": "hospital" }   404 if unknown key
```

Activating a scenario takes effect on the **next** `POST /mission/start`. It does not interrupt a running mission.

### Replay

```
GET /replay/frames        → { "frames": [...MissionState], "count": N }
GET /replay/frames/count  → { "count": N }
```

### WebSocket

**URL:** `ws://localhost:8000/ws`  
**Direction:** server → client only  
**Message:** full `MissionState` as UTF-8 JSON on every state change  
**On connect:** server immediately pushes the current state

---

## 10. Configuration

All tuneable settings live in `backend/config/settings.py`:

```python
class Settings:
    app_name: str = "FireRescue AI"
    version:  str = "1.0.0"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    sim_tick_interval_seconds: float = 1.0    # seconds per simulation tick
    max_zone_history: int = 20                # frames of zone history for perception
    perception_detector: str = "ground_truth"
    broadcast_interval_seconds: float = 3.0   # not used in current implementation
    frame_timeout_seconds: float = 5.0
```

No environment variables are needed for local development. For a faster demo, reduce `sim_tick_interval_seconds` to `0.25`.

---

## 11. Adding a Feature — Checklist

For any backend change:
- [ ] Add or update a Pydantic model in `backend/models/` if the data shape changes
- [ ] Add the route in `backend/api/routes.py`
- [ ] If the change affects `MissionState`, update `frontend/src/types/mission.ts` to match exactly
- [ ] Write tests in `backend/tests/`

For any frontend change:
- [ ] Dashboard component changes: update the component and its `__tests__/` file
- [ ] Store changes: update `missionStore.ts` and `stores/__tests__/missionStore.test.ts`
- [ ] New hook: add to `hooks/` with a matching test if testable

Do not modify:
- `simulation/` — stable, frozen
- `perception/` — stable, frozen
- `backend/models/mission_state.py` — any change requires matching `types/mission.ts` update
- `backend/mission/manager.py` — core state machine; changes risk breaking all downstream

---

## 12. File Naming Conventions

| Layer | Convention | Example |
|---|---|---|
| Python modules | `snake_case.py` | `mission_state.py` |
| Python tests | `test_<module>.py` | `test_recorder.py` |
| React components | `PascalCase.tsx` | `ReplayControls.tsx` |
| React hooks | `camelCase.ts` with `use` prefix | `useReplayEngine.ts` |
| React test files | `<Component>.test.tsx` | `ReplayControls.test.tsx` |
| Store test files | `<store>.test.ts` | `missionStore.test.ts` |
