"""
CameraSimAdapter — DataSource decorator that adds a simulated camera.

Wraps any DataSource (in practice SimAdapter) and attaches an RGB
image to every frame it delivers: the drone now "sees" a photograph
of what its current zone contains instead of the system relying on
perfect environmental knowledge. Detectors that ignore the "rgb"
channel (GroundTruthDetector) are unaffected; YOLODetector runs real
inference on it.

This follows the documented hardware-independence boundary: a new
DataSource implementation, composed around the existing one, wired up
where adapters were already constructed (backend/main.py and the
mission-restart path in backend/api/routes.py) via make_data_source().
Nothing else in the system knows the camera exists — Frame stays the
only contract.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from backend.config.settings import settings
from backend.ingestion.interface import DataSource, FrameCallback
from backend.ingestion.sim_adapter import SimAdapter, OnCompleteCallback
from backend.models.frame import Frame
from backend.utils.logger import logger
from simulation.camera.provider import (
    CameraConfigError,
    ZoneCategoryResolver,
    ZoneImageProvider,
    load_camera_config,
)
from simulation.runner import SimulationRunner
from simulation.scenarios import Scenario

_PROJECT_ROOT = Path(__file__).resolve().parents[2]


class CameraSimAdapter(DataSource):
    """DataSource decorator that populates Frame.channels["rgb"].

    Only the "rgb" channel is added; every other Frame field passes
    through untouched. When the provider has no usable image for a
    zone, the frame is delivered exactly as the wrapped source
    produced it.
    """

    def __init__(self, source: DataSource, provider: ZoneImageProvider) -> None:
        """
        Args:
            source: The DataSource being decorated (e.g. SimAdapter).
            provider: Zone image provider supplying the camera imagery.
        """
        self._source = source
        self._provider = provider

    async def start(self, mission_id: str, on_frame_callback: FrameCallback) -> None:
        """Start the wrapped source, attaching imagery to each frame."""

        async def deliver_with_camera(frame: Frame) -> None:
            # Same zone-id convention the enricher and detectors use.
            zone_id = f"{frame.pose.x}_{frame.pose.y}_{frame.pose.floor}"
            image = self._provider.image_for_zone(zone_id)
            if image is not None:
                frame.channels["rgb"] = image
            await on_frame_callback(frame)

        await self._source.start(mission_id, deliver_with_camera)

    async def stop(self) -> None:
        """Stop the wrapped source."""
        await self._source.stop()


def make_data_source(
    runner: SimulationRunner,
    scenario: Scenario,
    on_complete: Optional[OnCompleteCallback] = None,
) -> DataSource:
    """Build the mission's DataSource: SimAdapter, plus the simulated
    camera when it is enabled and configured.

    Used by backend startup and by the mission-restart path so both
    construct adapters identically (the camera's zone→category mapping
    is rebuilt from each new scenario's ground truth).

    Never raises: any camera configuration problem is logged and the
    plain SimAdapter is returned, preserving MVP behaviour.

    Args:
        runner: Simulation runner for the active scenario.
        scenario: The active scenario (source of hazard/victim maps).
        on_complete: Callback fired when the simulation finishes.

    Returns:
        A ready-to-start DataSource.
    """
    adapter: DataSource = SimAdapter(runner=runner, on_complete=on_complete)
    if not settings.camera_enabled:
        logger.info("Camera | disabled by settings — frames carry no rgb channel")
        return adapter

    config_path = _PROJECT_ROOT / settings.camera_config_path
    try:
        config = load_camera_config(config_path)
    except CameraConfigError as exc:
        logger.warning("Camera | disabled | %s", exc)
        return adapter
    except ImportError as exc:
        logger.warning("Camera | disabled | missing dependency: %s", exc)
        return adapter

    hazard_levels = {
        zone_id: hdef.hazard_level.value
        for zone_id, hdef in scenario.hazard_zones.items()
    }
    victim_zones = {victim.zone_id for victim in scenario.victims}
    resolver = ZoneCategoryResolver(
        config=config, hazard_levels=hazard_levels, victim_zones=victim_zones
    )
    image_root = Path(config.image_root)
    if not image_root.is_absolute():
        image_root = _PROJECT_ROOT / image_root
    provider = ZoneImageProvider(
        config=config, resolver=resolver, image_root=image_root
    )
    logger.info(
        "Camera | enabled | root=%s randomize=%s seed=%d",
        image_root,
        config.randomize,
        config.seed,
    )
    return CameraSimAdapter(source=adapter, provider=provider)
