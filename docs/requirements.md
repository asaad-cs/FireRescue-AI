# Requirements

Functional and non-functional requirements for the FireRescue AI MVP prototype.

---

## Functional Requirements

These define what the system must be able to do.

### Mission Management

| ID | Requirement |
|---|---|
| FR-01 | The operator can start a new mission |
| FR-02 | The operator can end an active mission |
| FR-03 | The system records a start timestamp when a mission begins |
| FR-04 | The system records an end timestamp when a mission ends |
| FR-05 | Only one mission can be active at a time |
| FR-06 | A completed mission's Frame log can be reviewed after it ends |

### Data Ingestion

| ID | Requirement |
|---|---|
| FR-07 | The system receives continuous Frames from the active data source |
| FR-08 | Each Frame includes a drone pose (x, y, floor) and an environmental channel (temperature, CO level, smoke density) with a UTC timestamp |
| FR-09 | The system persists every incoming Frame to the data store |
| FR-10 | The system handles a gap or pause in Frame delivery without crashing |

### Processing Pipeline

| ID | Requirement |
|---|---|
| FR-11 | Every Frame passes through the pipeline before reaching the Perception Engine |
| FR-12 | The pipeline validates that a Frame is well-formed and belongs to the active mission; malformed Frames are rejected and logged |
| FR-13 | The pipeline resolves the drone's grid coordinates to a zone_id before passing the Frame to the Perception Engine |

### Perception

| ID | Requirement |
|---|---|
| FR-14 | The Perception Engine classifies a hazard level for the current zone on every Frame |
| FR-15 | Hazard levels use a discrete scale: CLEAR, LOW, MODERATE, HIGH, CRITICAL |
| FR-16 | The Perception Engine maintains a victim presence probability estimate per zone |
| FR-17 | Victim estimates are updated each time the drone passes through or near a zone |
| FR-18 | The Perception Engine generates an alert when a zone reaches HIGH or CRITICAL hazard level |
| FR-19 | The Perception Engine generates an alert when victim probability in a zone exceeds a defined threshold |

### Alerting

| ID | Requirement |
|---|---|
| FR-20 | Alerts are timestamped and associated with a zone |
| FR-21 | Alerts are persisted to the data store |
| FR-22 | Alerts are included in the MissionState pushed to the frontend in real time |
| FR-23 | The same alert is not re-generated if conditions remain the same (de-duplication per zone per mission) |

### Mission State and Dashboard

| ID | Requirement |
|---|---|
| FR-24 | The Mission Manager assembles and owns a MissionState object that is the single source of truth for the dashboard |
| FR-25 | The dashboard receives only MissionState; it has no direct access to Frames, PerceptionResults, or zone analysis details |
| FR-26 | The dashboard displays the building floor plan |
| FR-27 | The dashboard shows the drone's current position on the floor plan |
| FR-28 | The dashboard colors each zone according to its current hazard level from MissionState |
| FR-29 | The dashboard shows current sensor readings from MissionState |
| FR-30 | The dashboard shows an alert panel listing all active alerts from MissionState |
| FR-31 | The dashboard updates in real time as new MissionState snapshots arrive (no manual refresh) |
| FR-32 | The dashboard shows mission status: active / ended, elapsed time |

### Simulation

| ID | Requirement |
|---|---|
| FR-33 | The simulation generates Frames at a configurable tick rate |
| FR-34 | The simulation moves a virtual drone through the building following a defined path |
| FR-35 | The simulation includes at least one preset fire/hazard scenario |
| FR-36 | The simulation produces Frames in the same format the backend expects from real hardware |

---

## Non-Functional Requirements

These define the constraints the system must operate within.

| ID | Requirement | Rationale |
|---|---|---|
| NFR-01 | **Modular** — each component has a single, clear responsibility | Enables independent development and replacement |
| NFR-02 | **Hardware-independent** — the backend never depends on a specific data source implementation | Allows simulation to be replaced by real hardware without changes to the pipeline, perception, or frontend |
| NFR-03 | **Real-time updates** — the frontend receives a new MissionState within 500 ms of a Frame being processed | Operational value requires low-latency awareness |
| NFR-04 | **Maintainable** — each module is readable and documented at the interface level | Research prototype must be demonstrable and extensible |
| NFR-05 | **Runnable locally** — the full stack runs on a single developer machine with no external dependencies | Prototype must work offline and without cloud infrastructure |
| NFR-06 | **Graceful degradation** — if the simulation stops sending Frames, the backend and frontend remain stable | Prevents demo failures from timing issues |
| NFR-07 | **Configurable** — tick rate, hazard thresholds, and scenario choice are configurable without code changes | Enables quick adjustments during demonstrations |
| NFR-08 | **No real-time OS constraints** — acceptable latency is hundreds of milliseconds, not microseconds | This is a software prototype, not an embedded system |

---

## Out of Scope

The following are explicitly not part of this prototype.

| Feature | Notes |
|---|---|
| Real drone hardware or firmware | No hardware available; see simulation design |
| Additional sensor modalities (thermal, RGB, LiDAR) | Frame schema supports them; MVP only implements environmental channel |
| Multi-user or role-based access | Single operator, no authentication |
| Multi-drone support | Single drone per mission for MVP |
| Cloud or distributed deployment | Local development only |
| Mobile or tablet interface | Desktop dashboard only |
| Natural language operator commands | Not required for MVP |
| Voice alerts or audio output | Not required for MVP |
| Integration with CAD/dispatch systems | Out of scope |
| Production security hardening | Prototype, not production |
| Regulatory compliance | Research prototype only |
| High-fidelity physics simulation | Simplified environmental emulation is sufficient |
| Real building floor plan import | Synthetic grid floor plan only |
