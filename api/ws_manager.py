"""
WebSocket Connection Manager — Persona Platform

Manages active WebSocket connections with:
  - Per-user connection limits (MAX_CONNECTIONS_PER_USER)
  - Per-persona broadcast
  - Connection statistics
"""

import logging
from collections import defaultdict
from fastapi import WebSocket

logger = logging.getLogger("persona_hub.ws_manager")


class ConnectionManager:
    """
    Thread-safe (asyncio-safe) WebSocket connection manager.

    active_connections: dict[persona_id, list[WebSocket]]
    connection_count:   dict[user_id, int]
    """

    MAX_CONNECTIONS_PER_USER = 5

    def __init__(self) -> None:
        # persona_id → list of live WebSocket objects
        self.active_connections: dict[str, list[WebSocket]] = defaultdict(list)
        # user_id → current connection count
        self.connection_count: dict[str, int] = defaultdict(int)

    async def connect(self, ws: WebSocket, user_id: str, persona_id: str) -> bool:
        """
        Register a new WebSocket.

        Returns True if the connection was accepted, False if the user already
        has MAX_CONNECTIONS_PER_USER active connections (caller should close ws).
        """
        current = self.connection_count[user_id]
        if current >= self.MAX_CONNECTIONS_PER_USER:
            logger.warning(
                "ws_connect_rejected user=%s persona=%s reason=limit_exceeded current=%d",
                user_id, persona_id, current,
            )
            return False

        self.active_connections[persona_id].append(ws)
        self.connection_count[user_id] += 1
        logger.info(
            "ws_connect user=%s persona=%s total_for_user=%d",
            user_id, persona_id, self.connection_count[user_id],
        )
        return True

    def disconnect(self, ws: WebSocket, user_id: str, persona_id: str) -> None:
        """Remove a WebSocket from the registry."""
        connections = self.active_connections.get(persona_id, [])
        if ws in connections:
            connections.remove(ws)
        if not connections:
            self.active_connections.pop(persona_id, None)

        count = self.connection_count.get(user_id, 0)
        if count > 0:
            self.connection_count[user_id] = count - 1
        if self.connection_count[user_id] == 0:
            self.connection_count.pop(user_id, None)

        logger.info(
            "ws_disconnect user=%s persona=%s remaining_for_user=%d",
            user_id, persona_id, self.connection_count.get(user_id, 0),
        )

    async def broadcast(self, persona_id: str, message: str) -> None:
        """Send *message* to all WebSocket connections for a given persona."""
        dead: list[WebSocket] = []
        for ws in list(self.active_connections.get(persona_id, [])):
            try:
                await ws.send_text(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.active_connections[persona_id].remove(ws)

    def get_stats(self) -> dict:
        """Return aggregate connection statistics."""
        per_persona = {pid: len(conns) for pid, conns in self.active_connections.items()}
        total = sum(per_persona.values())
        return {
            "total_connections": total,
            "per_persona": per_persona,
            "active_users": len(self.connection_count),
        }


# Module-level singleton — import and use from ws.py
manager = ConnectionManager()
