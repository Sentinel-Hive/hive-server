from typing import Set
from fastapi import WebSocket
from svh import notify


class WebsocketHub:
    """Central hub to manage active websocket connections."""

    def __init__(self) -> None:
        self.connections: Set[WebSocket] = set()

    async def connect(self, websocket: WebSocket) -> None:
        """Add a websocket to the active connection list."""
        self.connections.add(websocket)
        notify.websocket(f"connected clients: {len(self.connections)}")

    def disconnect(self, websocket: WebSocket) -> None:
        """Remove a websocket from the active connection list."""
        if websocket in self.connections:
            self.connections.remove(websocket)
            notify.websocket(
                f"disconnected (remaining: {len(self.connections)})")

    async def send_to(self, websocket: WebSocket, message: dict) -> None:
        """Send a message to a single client."""
        try:
            await websocket.send_json(message)
        except Exception as e:
            notify.error(f"send_to error: {e}")
            self.disconnect(websocket)

    async def broadcast(self, message: dict) -> None:
        """Send a message to all connected clients."""
        if not self.connections:
            notify.websocket("broadcast: no clients connected")
            return

        dead_connections = []
        for ws in list(self.connections):
            try:
                await ws.send_json(message)
            except Exception as e:
                notify.error(f"broadcast error: {e}")
                dead_connections.append(ws)

        for ws in dead_connections:
            self.disconnect(ws)

        notify.websocket(
            f"broadcast complete to {len(self.connections)} client(s)")


# Global instance used by websocket routes
websocket_hub = WebsocketHub()
