"""
Broadcaster — one-way pipe from Mission Manager to all WebSocket clients.

The broadcaster maintains the set of connected WebSocket clients.
When the Mission Manager changes state, it calls broadcast(state).
Each connected client receives the full MissionState serialized as JSON.

Clients that have disconnected are silently removed on next broadcast.

Design: the broadcaster is a passive recipient of state updates.
It does not poll the Mission Manager; the Mission Manager pushes to it.
This enforces the one-way data flow: Manager → Broadcaster → Clients.
"""
from __future__ import annotations

import asyncio
from typing import Set

from fastapi import WebSocket

from backend.models.mission_state import MissionState
from backend.utils.logger import logger


class Broadcaster:
    """Manages connected WebSocket clients and fans out state updates."""

    def __init__(self) -> None:
        self._clients: Set[WebSocket] = set()

    def connect(self, websocket: WebSocket) -> None:
        self._clients.add(websocket)
        logger.info(
            "Broadcaster.connect | clients=%d", len(self._clients)
        )

    def disconnect(self, websocket: WebSocket) -> None:
        self._clients.discard(websocket)
        logger.info(
            "Broadcaster.disconnect | clients=%d", len(self._clients)
        )

    async def broadcast(self, state: MissionState) -> None:
        """Push the current MissionState to all connected clients."""
        if not self._clients:
            return

        payload = state.model_dump(mode="json")
        # Convert datetime objects to ISO strings for JSON compatibility
        import json
        from datetime import datetime

        def _serialize(obj):
            if isinstance(obj, datetime):
                return obj.isoformat()
            raise TypeError(f"Not serializable: {type(obj)}")

        message = json.dumps(payload, default=_serialize)

        dead: Set[WebSocket] = set()
        for client in list(self._clients):
            try:
                await client.send_text(message)
            except Exception:  # noqa: BLE001
                dead.add(client)

        for client in dead:
            self._clients.discard(client)
            logger.warning("Broadcaster.broadcast | removed dead client")

        logger.debug(
            "Broadcaster.broadcast | sent to %d client(s)", len(self._clients)
        )

    def on_state_change(self, state: MissionState) -> None:
        """
        Synchronous adapter called by MissionManager._notify().
        Schedules the async broadcast on the running event loop.
        """
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.ensure_future(self.broadcast(state))
        except RuntimeError:
            pass  # no event loop — broadcast skipped (e.g., during unit tests)
