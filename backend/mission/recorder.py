"""
MissionRecorder — records every MissionState snapshot for replay.

Registered alongside the Broadcaster as a state-change listener so every
update that gets pushed over WebSocket is also stored in sequence.

Callers
-------
  main.py   registers the recorder via manager.register_state_change()
  routes.py calls recorder.reset() before a new mission starts
            calls recorder.get_history() to serve GET /replay/frames
"""
from __future__ import annotations

from typing import List

from backend.models.mission_state import MissionState


class MissionRecorder:
    """
    Records a deep copy of every MissionState as it changes.

    Thread safety: the recorder is driven entirely from the single asyncio
    event loop that runs MissionManager callbacks, so no locking is needed.
    """

    def __init__(self) -> None:
        self._history: List[MissionState] = []

    # ── Listener interface (matches Broadcaster.on_state_change signature) ──── #

    def on_state_change(self, state: MissionState) -> None:
        """Append an independent deep copy to the recorded history."""
        self._history.append(state.model_copy(deep=True))

    # ── Public read interface ─────────────────────────────────────────────── #

    def get_history(self) -> List[MissionState]:
        """Return a shallow list copy of the recorded history."""
        return list(self._history)

    def frame_count(self) -> int:
        """Number of snapshots recorded so far."""
        return len(self._history)

    def reset(self) -> None:
        """Clear history. Call before starting a new mission."""
        self._history.clear()
