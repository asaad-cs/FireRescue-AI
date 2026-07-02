"""
Data Source Interface — the hardware independence boundary.

Any data source (simulation, real drone, recorded replay) must implement
DataSource. The Mission Manager interacts only with this protocol;
it never knows whether the frames come from real hardware or a simulator.

To swap in a real drone:
  1. Create a class that inherits DataSource
  2. Implement start() and stop()
  3. Call on_frame_callback with each new Frame
  4. Pass the new class to MissionManager instead of the simulation

The callback signature:
    async def on_frame_callback(frame: Frame) -> None

start() must call on_frame_callback for each frame produced.
stop() must ensure no further callbacks are made after it returns.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Awaitable, Callable

from backend.models.frame import Frame

FrameCallback = Callable[[Frame], Awaitable[None]]


class DataSource(ABC):
    """Protocol for anything that produces Frames."""

    @abstractmethod
    async def start(self, mission_id: str, on_frame_callback: FrameCallback) -> None:
        """Begin producing frames; call on_frame_callback for each one."""

    @abstractmethod
    async def stop(self) -> None:
        """Stop producing frames. Must not call on_frame_callback after this."""
