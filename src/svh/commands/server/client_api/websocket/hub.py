from __future__ import annotations
from typing import Callable, List
from dataclasses import dataclass

from fastapi import WebSocket
from svh import notify


@dataclass
class Connection:
    ws: WebSocket
    user_id: str
    is_admin: bool = False


class WebsocketHub:
    """
    Central hub to manage active websocket connections, along with
    per-connection metadata such as user_id and is_admin.
    """

    def __init__(self) -> None:
        self._conns: List[Connection] = []

    async def connect(self, websocket: WebSocket, user_id: str, is_admin: bool) -> None:
        """
        Add a websocket to the active connection list with its metadata.
        Call this *after* websocket.accept() succeeds.
        """
        self._conns.append(Connection(ws=websocket, user_id=user_id, is_admin=is_admin))
        notify.websocket(f"connected (clients={len(self._conns)}, admin={is_admin})")

    def disconnect(self, websocket: WebSocket) -> None:
        """
        Remove a websocket from the active connection list.
        """
        before = len(self._conns)
        self._conns = [c for c in self._conns if c.ws is not websocket]
        after = len(self._conns)
        if before != after:
            notify.websocket(f"disconnected (clients={after})")

    async def send_to(self, websocket: WebSocket, message: dict) -> None:
        """
        Send a message to a single client.
        """
        try:
            await websocket.send_json(message)
        except Exception as e:
            notify.websocket(f"send_to error: {e!r}")
            self.disconnect(websocket)

    async def broadcast(self, message: dict) -> None:
        """
        Send a message to all connected clients.
        """
        await self._broadcast_filtered(lambda _c: True, message)

    async def broadcast_admins(self, message: dict) -> None:
        """
        Send a message only to admin clients.
        """
        await self._broadcast_filtered(lambda c: c.is_admin, message)

    async def broadcast_users(self, user_ids: list[str], message: dict) -> None:
        """
        Send a message only to specific user_ids.
        """
        target = set(user_ids or [])
        await self._broadcast_filtered(lambda c: c.user_id in target, message)

    async def broadcast_where(
        self, predicate: Callable[[Connection], bool], message: dict
    ) -> None:
        """
        Generic filter-based broadcast.
        """
        await self._broadcast_filtered(predicate, message)

    async def _broadcast_filtered(
        self, predicate: Callable[[Connection], bool], message: dict
    ) -> None:
        """
        Internal helper: send JSON to all connections matching predicate.
        Drop any dead connections.
        """
        if not self._conns:
            notify.websocket("broadcast: no clients connected")
            return

        dead: List[Connection] = []
        sent = 0
        for conn in list(self._conns):
            if not predicate(conn):
                continue
            try:
                await conn.ws.send_json(message)
                sent += 1
            except Exception as e:
                notify.websocket(f"broadcast error: {e!r}")
                dead.append(conn)

        # prune dead
        if dead:
            for d in dead:
                self.disconnect(d.ws)

        notify.websocket(f"broadcast complete to {sent} client(s)")


# Global instance used by websocket routes
websocket_hub = WebsocketHub()
