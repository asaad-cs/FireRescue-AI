"""
Application entry point.

Starts the FastAPI application, initialises all components inside the
lifespan context manager, and defines the WebSocket endpoint.

Phase 4 startup sequence:
  1. Instantiate Pipeline (Validator + Enricher + PerceptionEngine)
  2. Instantiate MissionManager with the Pipeline
  3. Instantiate Broadcaster; register it as a state-change listener
  4. Load default scenario → build SimulationRunner
  5. Tell MissionManager total zone count for accurate explored_pct
  6. Create + start mission
  7. Launch SimAdapter as a background task (drives the tick loop)

When the simulation completes (all zones explored), the runner calls
the on_complete callback which transitions mission to ENDED.

All components live in app.state for WebSocket handler access.
"""
from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect

from backend.api.routes import router
from backend.config.settings import settings
from backend.ingestion.camera_adapter import make_data_source
from backend.mission.manager import MissionManager
from backend.mission.recorder import MissionRecorder
from backend.pipeline.enricher import Enricher
from backend.pipeline.pipeline import Pipeline
from backend.pipeline.validator import Validator
from backend.websocket.broadcaster import Broadcaster
from backend.utils.logger import logger
from perception.detectors.ground_truth import GroundTruthDetector
from perception.detectors.yolo import YOLODetector, find_latest_model
from perception.engine import PerceptionEngine
from perception.registry.registry import DetectorRegistry
from simulation.runner import SimulationRunner
from simulation.scenarios import default_scenario
from simulation.scenario_registry import DEFAULT_SCENARIO_KEY


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("FireRescue AI backend starting up...")

    # ── Simulation setup (needed before detector init) ───────────────── #
    scenario = default_scenario()
    runner = SimulationRunner(
        scenario=scenario,
        tick_interval=settings.sim_tick_interval_seconds,
    )

    # ── Perception framework ──────────────────────────────────────────── #
    # Extract plain dicts from scenario — no simulation types cross the boundary
    hazard_map = {zid: hdef.hazard_level for zid, hdef in scenario.hazard_zones.items()}
    victim_map = {v.zone_id: v.detection_probability for v in scenario.victims}

    gt_detector = GroundTruthDetector(hazard_map=hazard_map, victim_map=victim_map)
    gt_detector.initialize()

    registry = DetectorRegistry()
    registry.register("ground_truth", gt_detector)

    # YOLO detector (Version 2). Always registered so switching is a
    # config-only change; degrades gracefully if no model is exported.
    project_root = Path(__file__).resolve().parents[1]
    yolo_model = (
        project_root / settings.yolo_model_path
        if settings.yolo_model_path
        else find_latest_model(project_root / settings.yolo_model_dir)
    )
    yolo_detector = YOLODetector(
        model_path=yolo_model or (project_root / settings.yolo_model_dir / "model.onnx"),
        confidence_threshold=settings.yolo_confidence_threshold,
        iou_threshold=settings.yolo_iou_threshold,
        image_size=settings.yolo_image_size,
    )
    yolo_detector.initialize()
    registry.register("yolo", yolo_detector)

    logger.info(
        "Detector registry ready | active='%s' | available=%s",
        settings.perception_detector,
        registry.available(),
    )

    # ── Processing pipeline ──────────────────────────────────────────── #
    validator = Validator()
    enricher = Enricher()
    engine = PerceptionEngine(registry=registry, active_detector=settings.perception_detector)
    pipeline = Pipeline(validator=validator, enricher=enricher, engine=engine)

    # ── Core components ──────────────────────────────────────────────── #
    manager = MissionManager(pipeline=pipeline)
    broadcaster = Broadcaster()
    recorder = MissionRecorder()
    manager.register_state_change(broadcaster.on_state_change)
    manager.register_state_change(recorder.on_state_change)

    logger.info(
        "Scenario loaded: '%s'  |  building: %s  |  zones: %d",
        scenario.name,
        runner.building.name,
        runner.total_zones(),
    )

    # Tell manager the total zone count so explored_pct uses the full map
    manager.set_total_zone_count(runner.total_zones())

    # ── Mission lifecycle ─────────────────────────────────────────────── #
    mission_id = manager.create_mission()
    manager.start_mission()

    def on_mission_complete() -> None:
        """Called by the SimRunner when all zones are explored."""
        manager.end_mission()
        logger.info(
            "Mission %s completed — all zones explored. Awaiting operator review.",
            mission_id,
        )

    # ── Wire data source (SimAdapter + simulated camera) and launch ──── #
    adapter = make_data_source(
        runner=runner, scenario=scenario, on_complete=on_mission_complete
    )
    sim_task = asyncio.create_task(
        adapter.start(mission_id=mission_id, on_frame_callback=manager.on_frame)
    )

    # ── Expose to WebSocket handler and routes ───────────────────────── #
    app.state.manager = manager
    app.state.broadcaster = broadcaster
    app.state.recorder = recorder
    app.state.adapter = adapter
    app.state.scenario = scenario
    app.state.registry = registry
    app.state.gt_detector = gt_detector
    app.state.active_scenario_name = DEFAULT_SCENARIO_KEY

    logger.info(
        "FireRescue AI backend ready  |  host=%s  port=%d  tick=%.1fs",
        settings.api_host,
        settings.api_port,
        settings.sim_tick_interval_seconds,
    )

    yield  # ── Application runs here ──────────────────────────────────── #

    logger.info("FireRescue AI backend shutting down...")
    await adapter.stop()
    sim_task.cancel()
    try:
        await sim_task
    except (asyncio.CancelledError, Exception):
        pass
    gt_detector.shutdown()
    yolo_detector.shutdown()
    logger.info("FireRescue AI backend stopped.")


app = FastAPI(
    title=settings.app_name,
    version=settings.version,
    lifespan=lifespan,
)

app.include_router(router)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    """Accept WebSocket connections and stream MissionState updates."""
    await websocket.accept()
    broadcaster: Broadcaster = websocket.app.state.broadcaster
    broadcaster.connect(websocket)
    logger.info("WebSocket client connected")

    # Push the current state immediately on connect so the client is up to date
    manager: MissionManager = websocket.app.state.manager
    state = manager.get_state()
    if state is not None:
        await broadcaster.broadcast(state)

    try:
        while True:
            # Server-only push; we only need to keep the connection alive
            await websocket.receive_text()
    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")
    finally:
        broadcaster.disconnect(websocket)


if __name__ == "__main__":
    uvicorn.run(
        "backend.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=False,       # reload breaks asyncio tasks in Phase 4
        log_level=settings.log_level.lower(),
    )
