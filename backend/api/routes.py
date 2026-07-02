"""
REST API routes.

Stateless informational endpoints:
  GET /       — service info (name, version, status)
  GET /health — liveness check

Mission control endpoints (Phase 6B):
  POST /mission/start   — transition IDLE/PAUSED → ACTIVE
  POST /mission/pause   — transition ACTIVE → PAUSED
  POST /mission/resume  — transition PAUSED → ACTIVE
  POST /mission/end     — end the mission (any non-ENDED state)

Scenario endpoints (Phase 7B):
  GET  /scenarios                       — list all registered scenarios
  POST /scenarios/{key}/activate        — set active scenario for next mission

Mission control endpoints access app.state.manager (set by lifespan).
They return 409 Conflict on invalid state transitions.
"""
from __future__ import annotations

import asyncio
from typing import Any, Dict, List

from backend.models.mission_state import MissionState as MissionStateModel

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from backend.config.settings import settings
from backend.models.mission_state import MissionStatus
from simulation.scenario_registry import (
    SCENARIO_REGISTRY,
    list_scenarios,
    get_scenario,
)

router = APIRouter()


# ── Response models ────────────────────────────────────────────────────────────


class ServiceInfo(BaseModel):
    name: str
    version: str
    status: str


class HealthResponse(BaseModel):
    status: str


class MissionActionResponse(BaseModel):
    status: str
    mission_id: str


class ScenarioInfo(BaseModel):
    key: str
    display_name: str
    description: str
    zone_count: int


class ScenariosResponse(BaseModel):
    active: str
    scenarios: List[ScenarioInfo]


class ActivateScenarioResponse(BaseModel):
    activated: str


class ReplayFramesResponse(BaseModel):
    frames: List[MissionStateModel]
    count: int


# ── Informational ─────────────────────────────────────────────────────────────


@router.get("/", response_model=ServiceInfo)
async def root() -> ServiceInfo:
    """Return basic service metadata."""
    return ServiceInfo(
        name=settings.app_name,
        version=settings.version,
        status="running",
    )


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """Liveness check — returns 200 OK when the backend is up."""
    return HealthResponse(status="ok")


# ── Scenario registry ─────────────────────────────────────────────────────────


@router.get("/scenarios", response_model=ScenariosResponse)
async def list_scenarios_endpoint(request: Request) -> ScenariosResponse:
    """List all registered scenarios and report the currently active one."""
    active = getattr(request.app.state, "active_scenario_name", "warehouse_alpha")
    return ScenariosResponse(
        active=active,
        scenarios=[ScenarioInfo(**s) for s in list_scenarios()],
    )


@router.post("/scenarios/{scenario_key}/activate", response_model=ActivateScenarioResponse)
async def activate_scenario(
    scenario_key: str, request: Request
) -> ActivateScenarioResponse:
    """
    Set the scenario that will be used the next time a mission is started.

    Takes effect on the next NEW MISSION / restart. Does not affect a mission
    already in progress.
    """
    if scenario_key not in SCENARIO_REGISTRY:
        raise HTTPException(
            status_code=404,
            detail=f"Scenario '{scenario_key}' not found. "
                   f"Available: {list(SCENARIO_REGISTRY)}",
        )
    request.app.state.active_scenario_name = scenario_key
    return ActivateScenarioResponse(activated=scenario_key)


# ── Replay ────────────────────────────────────────────────────────────────────


@router.get("/replay/frames", response_model=ReplayFramesResponse)
async def get_replay_frames(request: Request) -> ReplayFramesResponse:
    """
    Return the full recorded MissionState history for the current/last mission.

    Frames are in chronological order (oldest first). The frontend uses this
    to drive deterministic replay without re-running the simulation.
    """
    recorder = request.app.state.recorder
    history = recorder.get_history()
    return ReplayFramesResponse(frames=history, count=len(history))


@router.get("/replay/frames/count")
async def get_replay_frame_count(request: Request) -> Dict[str, int]:
    """Return the number of recorded frames for the current/last mission."""
    return {"count": request.app.state.recorder.frame_count()}


# ── Mission control ───────────────────────────────────────────────────────────


def _mission_id(request: Request) -> str:
    """Return current mission_id, or empty string if no state exists."""
    manager = request.app.state.manager
    state = manager.get_state()
    return state.mission_id if state else ""


@router.post("/mission/start", response_model=MissionActionResponse)
async def start_mission(request: Request) -> MissionActionResponse:
    """Transition IDLE/PAUSED → ACTIVE. Creates a fresh simulation if ENDED."""
    manager = request.app.state.manager
    state = manager.get_state()

    if state is not None and state.status == MissionStatus.ENDED:
        # Previous mission completed — spin up a fresh simulation.
        # Picks the scenario that was last activated via POST /scenarios/{key}/activate.
        from simulation.runner import SimulationRunner
        from backend.ingestion.sim_adapter import SimAdapter
        from perception.detectors.ground_truth import GroundTruthDetector

        scenario_key = getattr(
            request.app.state, "active_scenario_name", "warehouse_alpha"
        )
        scenario = get_scenario(scenario_key)

        runner = SimulationRunner(
            scenario=scenario,
            tick_interval=settings.sim_tick_interval_seconds,
        )

        # Rebuild the GroundTruthDetector so hazard/victim maps match new scenario.
        registry = request.app.state.registry
        old_detector = registry.get("ground_truth")
        old_detector.shutdown()

        hazard_map = {zid: h.hazard_level for zid, h in scenario.hazard_zones.items()}
        victim_map = {v.zone_id: v.detection_probability for v in scenario.victims}
        new_detector = GroundTruthDetector(hazard_map=hazard_map, victim_map=victim_map)
        new_detector.initialize()
        registry.register("ground_truth", new_detector)
        request.app.state.gt_detector = new_detector
        request.app.state.scenario = scenario

        # Clear recorder so the new mission starts with a fresh history
        request.app.state.recorder.reset()

        manager.set_total_zone_count(runner.total_zones())
        mission_id = manager.create_mission()   # resets state to IDLE
        manager.start_mission()                 # IDLE → ACTIVE

        def on_complete() -> None:
            manager.end_mission()

        adapter = SimAdapter(runner=runner, on_complete=on_complete)
        request.app.state.adapter = adapter
        asyncio.create_task(
            adapter.start(mission_id=mission_id, on_frame_callback=manager.on_frame)
        )
        return MissionActionResponse(status="started", mission_id=_mission_id(request))

    try:
        manager.start_mission()
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    return MissionActionResponse(status="started", mission_id=_mission_id(request))


@router.post("/mission/pause", response_model=MissionActionResponse)
async def pause_mission(request: Request) -> MissionActionResponse:
    """Transition ACTIVE → PAUSED."""
    manager = request.app.state.manager
    try:
        manager.pause_mission()
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    return MissionActionResponse(status="paused", mission_id=_mission_id(request))


@router.post("/mission/resume", response_model=MissionActionResponse)
async def resume_mission(request: Request) -> MissionActionResponse:
    """Transition PAUSED → ACTIVE."""
    manager = request.app.state.manager
    try:
        manager.resume_mission()
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    return MissionActionResponse(status="resumed", mission_id=_mission_id(request))


@router.post("/mission/end", response_model=MissionActionResponse)
async def end_mission(request: Request) -> MissionActionResponse:
    """End the mission from any non-ENDED state."""
    manager = request.app.state.manager
    try:
        manager.end_mission()
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    return MissionActionResponse(status="ended", mission_id=_mission_id(request))
