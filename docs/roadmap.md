# FireRescue AI — Roadmap

**Version:** 1.0.0  
**Date:** 2026-07-01  
**Status:** MVP v1.0 complete. All phases through 7C are done and locked.

---

## Phase Completion Summary

| Phase | Title | Status | Locked |
|---|---|---|---|
| 0 | Project Foundation | Complete | Yes |
| 1 | Architecture & Design | Complete | Yes |
| 2 | Simulation Engine | Complete | Yes |
| 3 | Backend & Pipeline | Complete | Yes |
| 4 | Full Integration | Complete | Yes |
| 5 | Perception Framework | Complete | Yes |
| 6A | Frontend Foundation | Complete | Yes |
| 6B | Interactive Dashboard | Complete | Yes |
| 7A | Visual Polish | Complete | Yes |
| 7B | Multiple Scenarios | Complete | Yes |
| 7C | Mission Replay | Complete | Yes |
| — | MVP Documentation | Complete | Yes |

---

## Phase 0 — Project Foundation

**Status: Complete · Locked**

Established the project directory structure, `.gitignore` for Python and Node, and documentation stub files in `docs/`. No application code.

---

## Phase 1 — Architecture & Design

**Status: Complete · Locked**

Produced the complete architectural blueprint:

- `docs/system-overview.md` — project purpose, workflow, architecture diagram
- `docs/architecture.md` — module hierarchy and communication model
- `docs/requirements.md` — functional and non-functional requirements
- `docs/tech-stack.md` — technology rationale per layer
- `docs/api-design.md` — message flow and communication philosophy
- `docs/database.md` — data entities (schema designed, not implemented)
- `docs/simulation.md` — simulation design and hardware transition path
- `docs/ui-design.md` — operator dashboard UX design and wireframes

---

## Phase 2 — Simulation Engine

**Status: Complete · Locked**

Built the simulation layer that generates synthetic sensor data:

- `simulation/environment.py` — Building, Floor, Zone models
- `simulation/drone.py` — BFS zone exploration; deterministic, one-shot per mission
- `simulation/sensors.py` — Environmental channel generation (temperature, CO, smoke)
- `simulation/scenarios.py` — Scenario factory functions (5 scenarios)
- `simulation/runner.py` — Async tick loop

---

## Phase 3 — Backend & Pipeline

**Status: Complete · Locked**

Built the backend application:

- `backend/main.py` — FastAPI entry point, lifespan wiring, WebSocket endpoint
- `backend/ingestion/interface.py` — DataSource protocol (hardware independence boundary)
- `backend/ingestion/sim_adapter.py` — Adapts SimulationRunner to DataSource interface
- `backend/pipeline/pipeline.py` — Orchestrates: Validate → Enrich → Perceive
- `backend/pipeline/validator.py` — Frame schema + mission context validation
- `backend/pipeline/enricher.py` — Resolves drone pose to zone_id + zone_label
- `backend/mission/manager.py` — Mission state machine, Frame processing, listener registry
- `backend/websocket/broadcaster.py` — Fans MissionState JSON to all WebSocket clients
- `backend/api/routes.py` — REST endpoints
- `backend/config/settings.py` — All tuneable values

---

## Phase 4 — Full Integration

**Status: Complete · Locked**

Wired all components end-to-end with auto-start on backend launch:

- Mission starts automatically when the backend starts
- `SimAdapter` drives the tick loop via `asyncio.create_task()`
- `on_complete` callback transitions mission to ENDED when all zones explored
- `POST /mission/start` from ENDED creates a fresh `SimulationRunner`
- WebSocket pushes live `MissionState` to all connected clients

---

## Phase 5 — Perception Framework

**Status: Complete · Locked**

Built the modular perception system:

- `perception/engine.py` — Orchestrator: `process(Frame, ZoneHistory) → PerceptionResult`
- `perception/hazard.py` — HazardLevel classifier (NONE/LOW/MODERATE/HIGH/CRITICAL)
- `perception/victim.py` — Victim signal probability estimator
- `perception/alerts.py` — Alert generator with deduplication
- `perception/base/detector.py` — BaseDetector abstract class
- `perception/registry/registry.py` — Detector registry (name → detector instance)
- `perception/detectors/ground_truth.py` — Reads static hazard/victim maps from scenario

---

## Phase 6A — Frontend Foundation

**Status: Complete · Locked**

Established the React application:

- React 18 + TypeScript 5.5 + Vite 5.4 + Tailwind CSS 3.4 + Zustand 4.5
- Dark operational theme (custom colour tokens in `tailwind.config.ts`)
- `frontend/src/types/mission.ts` — TypeScript interfaces mirroring backend Pydantic models
- `frontend/src/stores/missionStore.ts` — Zustand store
- `frontend/src/services/websocket.ts` — WebSocket service with auto-reconnect
- `frontend/src/hooks/useWebSocket.ts` — WebSocket lifecycle hook
- `frontend/src/services/api.ts` — REST client (mission control calls)
- Layout shell: AppLayout, TopNavigation, MainWorkspace, RightSidebar, BottomTimeline

---

## Phase 6B — Interactive Dashboard

**Status: Complete · Locked**

Built all data-driven dashboard components:

- `TacticalMap` — 5×4 CSS Grid, zone hazard colours, drone position, victim signal flags
- `AlertPanel` — Alert list with priority sorting and acknowledgement
- `DroneStatus` — Drone coordinates, heading, sensor readings with progress bars
- `VictimSignals` — Per-zone victim signal list with probability indicators
- `MissionControls` — Status dot, elapsed timer, state-appropriate action buttons
- `MissionTimeline` — Horizontal scrollable event chip bar
- `ActivityFeed` — Compact chronological log with hazard-coloured rows
- `ConnectionBanner` — Full-width WebSocket status banner with reconnect button

---

## Phase 7A — Visual Polish

**Status: Complete · Locked**

UX refinements with no architectural changes:

- CSS keyframe animations: `emergency-pulse`, `status-active-glow`, `reconnect-blink`, `drone-ping`, `fade-in-up`, `slide-in-right`
- `MissionStatistics` — Compact 4-stat row at top of right sidebar (explored%, elapsed, alert count, victim count)
- TacticalMap A–E column + 1–4 row grid labels; pulsing drone ping animation
- TopNavigation red accent icon + "Research Prototype" badge
- AlertPanel emergency pulse on unacknowledged EMERGENCY items
- Progress bars thickened from `h-1` to `h-2` in DroneStatus and VictimSignals

---

## Phase 7B — Multiple Scenarios

**Status: Complete · Locked**

Generalised simulation engine to support 5 named building scenarios:

- `simulation/scenario_registry.py` — Registry with factory functions (never cached)
- 4 new building factory functions in `simulation/environment.py`
- `GET /scenarios` — Lists all scenarios with metadata and active key
- `POST /scenarios/{key}/activate` — Sets scenario for next mission
- GroundTruthDetector rebuilt on scenario switch to match new hazard/victim maps
- 5 scenarios: `warehouse_alpha` (20 zones), `office_building` (12), `hospital` (16), `shopping_mall` (15), `school` (16)

---

## Phase 7C — Mission Replay

**Status: Complete · Locked**

Implemented complete mission replay system:

- `backend/mission/recorder.py` — `MissionRecorder` records deep copy of every MissionState
- `GET /replay/frames` and `GET /replay/frames/count` endpoints
- `ReplaySlice` in Zustand store: `isReplaying`, `replayHistory`, `replayIndex`, `replaySpeed`, `finalMissionState`
- `setMissionState` now records frames, detects mission boundaries, and blocks WS updates during replay
- `frontend/src/hooks/useReplayEngine.ts` — `setInterval`-driven tick engine (0.5×/1×/2×)
- `frontend/src/components/dashboard/ReplayControls.tsx` — Full replay control UI
- REPLAY button in `MissionControls` for ENDED state
- `TopNavigation` switches between `MissionControls` and `ReplayControls` based on `isReplaying`

---

## MVP Documentation

**Status: Complete · Locked**

- `README.md` — Full rewrite: overview, architecture, module structure, installation, API reference, demo workflow, roadmap
- `docs/developer-guide.md` — Architecture deep dive, setup, test commands, adding scenarios/detectors, feature checklist
- `docs/demo-guide.md` — Step-by-step demo walkthrough, scenario switching, quick reference
- `docs/project-status.md` — Phase status, stable modules, known limitations, technical debt, version roadmap

---

## Version 2 — Future Work (Not Planned)

The following represents potential directions for a second development cycle. None are scheduled.

### Hardware Integration
- Replace `SimAdapter` with a real drone hardware adapter implementing `DataSource`
- No other code changes required — the interface boundary is already in place

### Advanced Perception
- Probabilistic detector with configurable false-positive / false-negative rates
- Time-series hazard modelling (zone hazard levels change as fire spreads)
- Multiple concurrent detectors with weighted voting

### Persistent Storage
- SQLite / PostgreSQL mission store (schema already designed in `docs/database.md`)
- Mission history endpoint and replay from server-side history
- Alert persistence across page reloads

### Dynamic Simulation
- Fire spread logic: hazard levels propagate to adjacent zones over time
- Structural collapse simulation (zones become inaccessible)
- Multi-drone support (MissionManager coordination layer)

### Interface Enhancements
- Scenario selection UI (currently API-only)
- Floor plan import from real building layouts
- Real-time sensor noise modelling
