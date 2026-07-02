"""
SimAdapter — DataSource implementation backed by the SimulationRunner.

This is the hardware independence boundary from the simulation side.
The Mission Manager calls DataSource.start() and DataSource.stop().
It never knows whether the source is a simulation or real hardware.

SimAdapter wraps the SimulationRunner and translates the DataSource
protocol to the runner's async run() / stop() interface.

The tick loop runs as a background asyncio.Task started in start().
stop() signals the runner to exit and waits for the task to finish.
"""
from __future__ import annotations

import asyncio
from typing import Callable, Optional

from backend.ingestion.interface import DataSource, FrameCallback
from backend.utils.logger import logger
from simulation.runner import SimulationRunner

OnCompleteCallback = Callable[[], None]


class SimAdapter(DataSource):
    """DataSource implementation that drives the SimulationRunner."""

    def __init__(
        self,
        runner: SimulationRunner,
        on_complete: Optional[OnCompleteCallback] = None,
    ) -> None:
        self._runner = runner
        self._on_complete = on_complete
        self._task: Optional[asyncio.Task] = None

    async def start(self, mission_id: str, on_frame_callback: FrameCallback) -> None:
        """Launch the simulation tick loop as a background task."""
        logger.info("SimAdapter.start | mission_id=%s", mission_id)
        self._task = asyncio.create_task(
            self._runner.run(
                mission_id=mission_id,
                on_frame=on_frame_callback,
                on_complete=self._on_complete,
            )
        )

    async def stop(self) -> None:
        """Stop the simulation and wait for the tick loop to exit."""
        logger.info("SimAdapter.stop | stopping simulation runner")
        self._runner.stop()
        if self._task and not self._task.done():
            try:
                await asyncio.wait_for(self._task, timeout=5.0)
            except (asyncio.CancelledError, asyncio.TimeoutError):
                self._task.cancel()
        logger.info("SimAdapter.stop | done")
