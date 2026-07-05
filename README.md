# FireRescue AI

A simulation-first research prototype that provides real-time situational awareness for firefighters operating inside dangerous buildings. A virtual drone explores a building autonomously, sensors detect hazards and victim signals, an onboard AI model detects fire/smoke/people in real photographs fed through a simulated camera, and an operator monitors a live tactical dashboard.

**Version: 2.0 (checkpoint) — MVP v1.0.0 frozen + a complete AI vision pipeline on top. Status: Demo Ready with Minor Issues.**

> **New to this repo? Start with [`docs/session-context.md`](docs/session-context.md).** It is written for a reader (human or AI agent) with zero prior context and is kept authoritative — architecture, current state, the latest model's metrics, every known issue, the exact next priority, a full setup guide, and instructions for anyone (agent or developer) continuing this work.

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
│                │   SimAdapter/CameraSimAdapter → SimulationRunner      │
└────────────────┘───────────────────────────────────────────────────────┘
```

### Runtime flow — one simulation tick

1. `SimulationRunner` moves the drone to the next zone, generates a `Frame` (pose + sensor channels), and — if the simulated camera is enabled — a real photograph is attached to `frame.channels["rgb"]` based on the zone's hazard category.
2. The active `DataSource` delivers the `Frame` to `MissionManager.on_frame()`.
3. `MissionManager` sends the `Frame` through the `Pipeline`: Validate → Enrich → `PerceptionEngine`.
4. `PerceptionEngine` runs whichever detector is configured (`ground_truth` or `yolo`) and returns a `PerceptionResult` (hazard level, victim probability, alerts, and — for `yolo` — an annotated-image vision payload).
5. `MissionManager` merges the result into `MissionState` and notifies all registered listeners.
6. `Broadcaster` fans the full `MissionState` as JSON to all connected WebSocket clients; `Recorder` stores a copy for replay.
7. The frontend receives the message, updates its Zustand store, and re-renders — including the live camera view if a vision payload is present.

### The one architectural invariant

**The frontend only ever receives `MissionState`.** It has no knowledge of `Frame`, `PerceptionResult`, `ZoneHistory`, or any internal backend type. All derived values are computed server-side and included in `MissionState`.

---

## AI pipeline

`ai/object_detection/` is an isolated workspace (nothing in it is imported by the MVP runtime) implementing an Ultralytics YOLO detector — classes `fire` / `smoke` / `person` — trained via `python -m ai.object_detection.training.train` and exported to ONNX for serving via `perception/detectors/yolo.py` (onnxruntime, never raises, degrades gracefully). Switching between the deterministic `ground_truth` detector (the committed default) and the trained `yolo` detector is a single config value: `settings.perception_detector`.

**Current model:** `firerescue-detector-20260705-064246` (YOLOv8n, 60 GPU epochs) — **mAP50 0.601 / mAP50-95 0.334**, up from a corrected baseline of mAP50 0.3997. See `docs/session-context.md` → "Latest Model" for the full metrics table, and → "Known Issues" for confirmed limitations (animal→person false positives, two mislabeled training negatives, near-absence of indoor-building imagery).

## Dataset architecture

The image library uses **Architecture A (Category → Scene)** — e.g. `fire/warehouse/`, `smoke/office/` — the sole, finally-decided filesystem standard for this project. Two separate libraries exist:
- `assets/simulation_dataset/` — the production master library (tracked in git), with a `_curation/` staging subtree for images under review.
- `assets/demo_dataset/` — an isolated, hand-curated set built specifically for reliable live demos, toggled on with one settings flag (`camera_demo_mode`).

The YOLO training dataset itself (12,545 images, scene-aware split to prevent train/val/test leakage) lives under `ai/object_detection/datasets/` and is gitignored — regenerate it with the `data_tools` pipeline (see Setup below).

---

## Module Structure

```
FireRescue-AI/
│
├── backend/                         FastAPI application
├── simulation/                      Simulation engine + simulated camera (simulation/camera/)
├── perception/                      Detection framework (ground_truth + yolo detectors)
├── frontend/                        Operator dashboard (React)
├── ai/                              AI/ML workspace (object_detection module implemented; others are placeholders)
├── assets/                          Image libraries (simulation_dataset = production, demo_dataset = demo)
├── docs/                            Documentation — session-context.md is authoritative
├── requirements.txt                 Backend Python dependencies
└── README.md
```

Full folder-by-folder breakdown: `docs/session-context.md` → "Folder structure".

---

## Tech Stack

| Layer | Technology | Version |
|---|---|---|
| Backend | Python + FastAPI + uvicorn | Python 3.12, FastAPI 0.111 |
| Frontend | React + TypeScript + Vite | React 18, TS 5.5, Vite 5.4 |
| Styling | Tailwind CSS | 3.4 |
| State management | Zustand | 4.5 |
| AI / object detection | Ultralytics YOLO + PyTorch + onnxruntime | YOLOv8n |
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

## Setup

**Prerequisites:** Python 3.12+, Node.js 18+

```bash
# Clone and enter the project
git clone https://github.com/asaad-cs/FireRescue-AI.git
cd FireRescue-AI

# Backend dependencies
pip install -r requirements.txt

# Frontend dependencies
cd frontend && npm install && cd ..

# Optional — only needed for YOLO training/inference
pip install -r ai/requirements.txt

# Rebuild the simulator's runtime image folder from the tracked master library
python -m ai.object_detection.data_tools.export_simulation_library
```

**Important:** trained model weights (`.onnx`/`.pt`) are gitignored and are **not** included in this repository. Running with `perception_detector = "yolo"` requires either retraining (see `docs/session-context.md` → "Setup Guide") or copying a model file in from elsewhere. The default detector, `ground_truth`, needs no model file at all.

### Running the Backend

```bash
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --ws websockets
```

The simulation starts automatically. The drone explores the Warehouse Alpha scenario (20 zones) in approximately 20 seconds at the default 1-second tick rate.

**Key configurable settings** (`backend/config/settings.py`):

| Setting | Default | Description |
|---|---|---|
| `api_port` | `8000` | Backend HTTP port |
| `sim_tick_interval_seconds` | `1.0` | Seconds between simulation ticks |
| `perception_detector` | `"ground_truth"` | Active detector — `"ground_truth"` or `"yolo"` |
| `camera_demo_mode` | `False` | `True` switches the simulated camera to the curated demo image set |

### Running the Frontend

```bash
cd frontend && npm run dev
```

Open `http://localhost:5173`. The frontend proxies `/api/*` and `/ws` to `http://localhost:8000` automatically.

### Running Tests

```bash
python -m pytest               # Backend: 623 tests + 50 subtests
cd frontend && npx vitest run  # Frontend: 334 tests
cd frontend && npx tsc --noEmit
```

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
7. The **live camera monitor** shows the real photograph the simulated camera selected for the current zone, with AI detection overlays if `perception_detector = "yolo"`
8. When the mission completes (all zones explored), click **NEW MISSION** to restart
9. Or click **REPLAY** to step through the recorded mission at 0.5×, 1×, or 2× speed
10. To try a different building, call `POST /scenarios/{key}/activate` then **NEW MISSION**
11. Set `camera_demo_mode = True` for a curated, non-repetitive, demo-safe image set (see `docs/session-context.md`)

---

## Current State, Known Issues, and Next Priority

The model has converged on the current dataset — **more training is not the next step.** The confirmed bottleneck is the near-total absence of indoor-building imagery (kitchens, offices, hospitals, malls, schools, corridors, electrical/server rooms, basements, stairwells) in the training corpus, along with two mislabeled training negatives and an animal→person misclassification issue caused by zero animal images existing in the corpus.

Full detail — completed phases, production vs. demo vs. experimental components, the full metrics table, every confirmed known issue, and the exact 5-phase next-priority plan (curate indoor fire → indoor smoke → indoor victims → indoor safe negatives → hard negatives, THEN retrain) — is documented in **`docs/session-context.md`**. Do not retrain the model without reading that plan first.

---

## Roadmap

| Phase | Title | Status |
|---|---|---|
| 0–7C | MVP (simulation, backend, perception, dashboard, scenarios, replay) | Complete, frozen |
| 8A–8K | AI workspace, YOLO training pipeline, simulated camera, live AI vision, EOC dashboard redesign, camera experience | Complete |
| 9A–10B.1 | Dataset gap analysis, curation staging, Architecture A finalized as the sole dataset standard | Complete |
| Demo.1–Demo.6 | Isolated demo dataset + Demo Mode + recycle-bug fix + Safe-category expansion | Complete |
| AI.1 | GPU retrain (60 epochs) + full live validation — verdict "Demo Ready with Minor Issues" | Complete |
| **Next** | **Curate a real indoor-building dataset (5 phases) before any further retraining** | **Not started** |

---

## Notes

This project is built for research, portfolio, and demonstration purposes. It is not a commercial product, not a startup, and not intended for deployment in real emergency operations.
