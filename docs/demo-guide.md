# FireRescue AI — Demo Guide

**Version:** 1.0.0  
**Date:** 2026-07-01  
**Audience:** Demonstration presenters, evaluators, first-time users

---

## Before the Demo

### 1. Start both servers

**Terminal 1 — Backend:**
```bash
cd FireRescue-AI
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --ws websockets
```

**Terminal 2 — Frontend:**
```bash
cd FireRescue-AI/frontend
npm run dev
```

Open `http://localhost:5173`. The dashboard should appear within a few seconds and the mission begins automatically.

### 2. What you will see at startup

The green **MISSION ACTIVE** indicator appears in the navigation bar with a running timer. The Tactical Map (left panel) shows a 5×4 grid of zones. The drone marker (blue pulsing dot) starts in the top-left zone.

---

## Demo Walkthrough — Default Scenario (Warehouse Alpha)

### Phase 1: Mission start

The simulation starts automatically. No button press is needed for the first mission.

- **Navigation bar** shows: `MISSION ACTIVE` · elapsed timer · `PAUSE` and `END` buttons
- **Tactical Map** shows the 5×4 Warehouse Alpha grid with zone names
- **Drone marker** (top-right of the starting cell) pulses blue

**Talk track:**
> "The system has auto-started a search mission in a five-by-four warehouse grid. A virtual drone is exploring the building using a breadth-first search algorithm. The operator dashboard is receiving live updates over WebSocket — every second, the backend pushes a full mission state snapshot."

---

### Phase 2: Exploration in progress

As the simulation runs (one tick per second), the drone moves zone by zone.

**What to point out:**

- **Zone colours change** as the drone visits each zone. The colour encodes the hazard level detected by the perception engine:
  - Dark background — not yet explored
  - Amber — LOW hazard
  - Orange — MODERATE hazard
  - Red — HIGH or CRITICAL hazard
  - Green — NONE / safe

- **Alerts appear** in the right sidebar when the drone enters a hazardous zone. Emergency alerts (CRITICAL) pulse with a red border.

- **Victim signals appear** in the lower-right panel when the drone detects a survivor probability above the detection threshold (30%). Amber flag ≥ 60%, red flag ≥ 80%.

- **Activity feed** (below the map) logs each zone visit with its hazard level.

- **Mission Timeline** (bottom bar) shows event chips scrolling in chronological order.

- **Statistics row** (top of right sidebar) shows: explored percentage, elapsed time, alert count, victim signal count.

**Talk track:**
> "As the drone explores, the perception engine classifies each zone's hazard level based on temperature, CO concentration, and smoke density readings. Critical zones — like this loading dock — generate emergency alerts that the operator can acknowledge. Victim signals indicate zones with elevated survivor probability."

**Expected hazard events for Warehouse Alpha:**
- Loading Dock (`2_0_1`) — CRITICAL, triggers EMERGENCY alert
- Two additional HIGH/MODERATE zones trigger their own alerts
- Two victim signals: zones `0_2_1` and `3_1_1`

---

### Phase 3: Mission complete

After approximately 20 seconds (20 zones × 1 second each), the simulation finishes.

- Status indicator changes to **MISSION ENDED**
- The timer stops
- Navigation bar shows: `NEW MISSION` button · `REPLAY` button

**Talk track:**
> "The drone has explored every zone in the building. The mission is complete. The operator now has two options: start a fresh mission, or replay the recorded mission to review what happened."

---

### Phase 4: Mission replay

Click the amber **REPLAY** button.

The navigation bar switches to the **Replay Controls** panel:
- `REPLAY` label (amber)
- Frame counter: `1 / 20`
- Amber progress bar
- Speed buttons: `0.5×` `1×` `2×`
- `PAUSE` · `RESTART` · `EXIT`

The dashboard rewinds to the first frame and plays back through the recorded mission state history.

**Demonstrate:**
1. Click `2×` — playback doubles in speed
2. Click `PAUSE` — playback freezes at the current frame
3. Click `RESTART` — jumps back to frame 1
4. Click `EXIT` — returns to the final mission state with `NEW MISSION` and `REPLAY` buttons

**Talk track:**
> "Every MissionState broadcast during the mission was recorded on the backend by the MissionRecorder component. The frontend fetched nothing during replay — it plays back the history it built up locally, frame by frame, at configurable speed. This lets the operator review the full drone path and every hazard detection without re-running the simulation."

---

### Phase 5: New mission

Click **NEW MISSION**.

The backend creates a fresh simulation runner and mission ID. The drone restarts from zone 0. The replay history is cleared and recording begins again.

---

## Switching Scenarios

To demonstrate a different building, use the REST API before starting a new mission:

```bash
# Hospital (16 zones, boiler room fire)
curl -X POST http://localhost:8000/scenarios/hospital/activate

# Then click NEW MISSION in the dashboard, or:
curl -X POST http://localhost:8000/mission/start
```

Available scenario keys:

| Key | Building | Zones |
|---|---|---|
| `warehouse_alpha` | Industrial warehouse | 20 |
| `office_building` | Office building | 12 |
| `hospital` | Hospital wing | 16 |
| `shopping_mall` | Shopping mall | 15 |
| `school` | School building | 16 |

You can also query the current scenario list:
```bash
curl http://localhost:8000/scenarios
```

---

## Demonstrating Mission Control

While a mission is **ACTIVE**:

| Button | Action |
|---|---|
| `PAUSE` | Freezes the simulation. Drone stops. Timer stops. |
| `RESUME` | Resumes from where it left off. |
| `END` | Immediately ends the mission regardless of exploration progress. |

**To show pause/resume:**
1. Click `PAUSE` — status changes to `PAUSED`, timer freezes
2. Wait a moment
3. Click `RESUME` — mission continues from the same drone position

---

## Demonstrating WebSocket Resilience

1. Stop the backend (Ctrl+C in Terminal 1)
2. The **Connection Banner** appears at the top of the dashboard with a blinking reconnect indicator
3. Restart the backend
4. The banner disappears and the dashboard resumes showing live mission state

---

## What This Prototype Does Not Do

Be prepared to address these limitations:

- **No real hardware.** Everything is simulated. The drone movement and all sensor readings are synthetic.
- **No persistent storage.** Restarting the backend clears mission history.
- **No authentication.** The API and dashboard are open — this is a local research tool, not a deployed system.
- **No AI inference.** The perception engine uses ground-truth hazard maps from the scenario definition. There is no machine learning model.
- **One drone only.** The architecture supports a single drone per mission.

---

## Quick Reference — Key URLs

| Resource | URL |
|---|---|
| Dashboard | `http://localhost:5173` |
| API root | `http://localhost:8000` |
| Health check | `http://localhost:8000/health` |
| Scenario list | `http://localhost:8000/scenarios` |
| Recorded frames | `http://localhost:8000/replay/frames/count` |

---

## Timing Reference

At the default 1-second tick interval:

| Scenario | Zones | Approximate duration |
|---|---|---|
| Warehouse Alpha | 20 | ~20 seconds |
| Office Building | 12 | ~12 seconds |
| Hospital | 16 | ~16 seconds |
| Shopping Mall | 15 | ~15 seconds |
| School | 16 | ~16 seconds |

For a quicker demo, reduce `sim_tick_interval_seconds` to `0.25` in `backend/config/settings.py` and restart the backend. This runs through all 20 zones in about 5 seconds.
