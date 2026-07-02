# Technology Stack

Rationale for every planned technology in the FireRescue AI prototype.

---

## Selection Philosophy

Every technology choice in this project follows the same evaluation criteria:

1. **Does it solve the problem well enough for a prototype?**
2. **Is it widely understood, so another engineer can pick it up quickly?**
3. **Is it the simplest option that meets the requirement?**
4. **Does it avoid introducing unnecessary infrastructure or operational overhead?**

No technology was chosen to be impressive. Every choice was made to keep the prototype buildable, runnable, and demonstrable by a single developer on a local machine.

---

## Backend — Python

### Purpose
The primary programming language for the backend, AI module, and simulation engine.

### Benefits
- Dominant language in AI/ML; the AI module and backend share a runtime, eliminating serialization overhead
- Large, mature ecosystem for data processing, numerical computing, and web frameworks
- Readable syntax makes the prototype accessible to reviewers and collaborators
- Excellent async support via `asyncio`, which is required for concurrent WebSocket handling

### Alternatives Considered
- **Go** — faster runtime, but the AI/ML ecosystem is in Python. Splitting languages creates unnecessary complexity for a single-developer prototype.
- **Node.js** — strong WebSocket support, but the AI module would require a subprocess or remote call, adding complexity.
- **Rust** — highest performance, but development speed is much lower, which is not acceptable for a research prototype.

### Why Python
Python is the natural choice when a project includes both a web API and an AI module. A single language across backend, simulation, and AI eliminates the need for inter-process serialization and keeps the codebase cohesive.

### Status
Planned. Version: Python 3.11+.

---

## Backend Framework — FastAPI

### Purpose
HTTP REST API and WebSocket server for the backend.

### Benefits
- Native async/await support, required for handling WebSocket connections concurrently
- Automatic request/response validation via Pydantic models
- Built-in API documentation (Swagger UI) generated from type annotations — useful during development
- Lightweight: no ORM, no session management, no scaffolding the prototype does not need
- Widely used and well-documented

### Alternatives Considered
- **Flask** — simpler, but no native async or WebSocket support without extensions. Adding async later is harder.
- **Django** — too heavyweight. Includes ORM, admin panel, and middleware the prototype does not need.
- **Starlette (raw)** — FastAPI is built on Starlette; using it directly offers no advantage over FastAPI and loses the validation layer.
- **aiohttp** — viable, but FastAPI's developer experience (type hints, auto-docs) is significantly better.

### Why FastAPI
FastAPI provides everything the prototype backend needs — REST, WebSocket, async, and validation — with minimal boilerplate. Its type-annotation-driven approach keeps the API surface explicit and readable.

### Status
Planned.

---

## Frontend Framework — React with TypeScript

### Purpose
Operator-facing dashboard for real-time mission monitoring.

### Benefits
- Component model maps naturally to the dashboard's panels (map, alert panel, status bar, sensor feed)
- TypeScript provides static typing, which catches interface mismatches between the WebSocket message format and the frontend rendering logic
- Large ecosystem of visualization libraries (for floor plan rendering and sensor overlays)
- Widely known; any engineer familiar with modern frontend can read and extend the code

### Alternatives Considered
- **Plain HTML + JavaScript** — simpler to start, but quickly becomes unmanageable as real-time state updates across multiple panels. React's state model is appropriate here.
- **Vue.js** — similar capability to React, but React has broader familiarity and a larger component ecosystem.
- **Svelte** — smaller bundle, simpler syntax, but less familiar to most engineers and smaller ecosystem for the specific visualization components needed.
- **Next.js** — React framework with server-side rendering. SSR is not needed for a real-time WebSocket dashboard. Adds unnecessary complexity.

### Why React + TypeScript
The dashboard has multiple panels that update from a single WebSocket stream. React's unidirectional data flow and component model handle this pattern cleanly. TypeScript ensures the WebSocket message schema is enforced at the type level in the frontend.

### Status
Planned.

---

## Database — SQLite

### Purpose
Persistent storage for mission records, sensor event logs, and alert history.

### Benefits
- Zero infrastructure: a single file, no server process to start or manage
- Included in Python's standard library via the `sqlite3` module
- Sufficient for the data volumes of a single-machine prototype (one mission at a time, hundreds of events per minute)
- Easy to inspect: the database file can be opened directly with any SQLite client for debugging

### Alternatives Considered
- **PostgreSQL** — production-grade relational database. Requires a running server, setup, and connection management. The operational overhead is not justified for a local prototype.
- **MongoDB** — document store, useful for flexible schemas. The data model for this prototype is well-defined and relational; document storage adds no benefit.
- **InfluxDB / TimescaleDB** — purpose-built for time-series data. Appropriate if sensor data volumes were very high or if time-series queries were complex. For the MVP, SQLite with a timestamped events table is sufficient.
- **In-memory only** — avoids persistence entirely. Rejected because mission replay and post-mission review are requirements.

### Why SQLite
SQLite is the correct choice for a local prototype that needs persistence without infrastructure. It can be upgraded to PostgreSQL in the future by changing only the database adapter; no application logic changes are required.

### Status
Planned. Will be accessed via an ORM (SQLAlchemy) to allow future database replacement.

---

## ORM — SQLAlchemy

### Purpose
Database abstraction layer. Provides a Python interface to the database that is not tied to SQLite.

### Benefits
- Supports SQLite for MVP and PostgreSQL for future without changing query logic
- Handles connection management and session lifecycle
- Keeps raw SQL out of application code, which improves readability and safety

### Alternatives Considered
- **Raw SQL with sqlite3** — simpler for small projects, but ties the code to SQLite and mixes query strings into application logic.
- **Tortoise ORM** — async-native ORM, pairs well with FastAPI. Viable alternative; SQLAlchemy was chosen for broader familiarity.
- **Peewee** — lightweight ORM, simpler API than SQLAlchemy. Acceptable for MVP; SQLAlchemy chosen for broader adoption and PostgreSQL compatibility.

### Why SQLAlchemy
Provides the database independence the architecture requires, with a well-known API that future contributors will recognize.

### Status
Planned.

---

## Real-Time Communication — WebSocket (via FastAPI)

### Purpose
Push live mission state updates from the backend to the frontend dashboard.

### Benefits
- Persistent bidirectional connection: the backend can push data without the frontend polling
- Native support in FastAPI and modern browsers
- Low latency: updates arrive at the frontend within milliseconds of being sent
- No additional infrastructure required

### Alternatives Considered
- **HTTP polling** — the frontend requests the current state on a timer. Simple but inefficient and introduces latency proportional to the poll interval. Rejected.
- **Server-Sent Events (SSE)** — server-to-client only push, simpler than WebSocket. Viable for this use case. WebSocket chosen instead because it allows the frontend to also send commands (start/end mission) over the same connection in a future iteration.
- **MQTT** — lightweight publish/subscribe protocol designed for IoT and sensor networks. Appropriate if the system scaled to many drones or external subscribers. Adds a broker (e.g., Mosquitto) as infrastructure dependency. Over-engineered for a single-client prototype.
- **Redis Pub/Sub** — useful for fan-out to multiple backend workers. Not needed when the backend is a single process.

### Why WebSocket
WebSocket through FastAPI requires no additional infrastructure and meets the latency requirement. It is the simplest option that supports real-time push from backend to frontend.

### Status
Planned.

---

## Perception Engine — Python (rule-based for MVP)

### Purpose
Hazard classification and victim probability estimation inside the `perception/` module. Called by the Processing Pipeline after each Frame is enriched.

### Benefits
- Python-native: runs in the same process as the backend, no inter-process overhead
- For MVP, threshold-based rules are sufficient to demonstrate the concept end-to-end
- The engine's interface (`process(frame, zone_history) → PerceptionResult`) is independent of the implementation: rules can be replaced with a scikit-learn model or a neural network without touching the pipeline or Mission Manager
- scikit-learn provides a familiar API for classification models if a trained model is introduced in a later phase

### Alternatives Considered
- **PyTorch / TensorFlow** — appropriate for deep learning models. Not needed for MVP; the hazard classification problem is simple enough for rule-based logic. Adding a neural network framework increases dependency overhead without improving the demonstration.
- **External AI API (OpenAI, etc.)** — requires network access, latency, and API costs. The system is designed to run offline. Rejected.
- **ONNX Runtime** — useful for running pre-trained models from any framework. A future option if a trained model is imported from another tool.

### Why rule-based for MVP
The MVP's goal is to demonstrate the full data pipeline — Frame → Pipeline → Perception → MissionState → Dashboard — not to produce a state-of-the-art model. Threshold rules implement the `engine.process()` interface today. Upgrading to a trained model later changes only the internals of `perception/`, not the surrounding architecture.

### Status
Planned. Initial implementation will use threshold-based rules. Model training is a future enhancement.

---

## Version Control — Git

### Purpose
Source control for the entire project.

### Benefits
- Standard. No justification required.
- Local repository; no remote required for early development.

### Status
Planned. To be initialized at the start of Phase 2.

---

## Summary Table

| Layer | Technology | Status |
|---|---|---|
| Language | Python 3.11+ | Planned |
| Backend framework | FastAPI | Planned |
| Frontend framework | React + TypeScript | Planned |
| Database | SQLite | Planned (MVP) |
| ORM | SQLAlchemy | Planned |
| Real-time | WebSocket (FastAPI) | Planned |
| Perception Engine | Rule-based / scikit-learn | Planned |
| Version control | Git | Planned |
| PostgreSQL | PostgreSQL | Future (optional upgrade) |
| Message broker | MQTT / Redis | Future (optional, multi-drone) |
