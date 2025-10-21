from typing import Set, Dict, Any
from starlette.websockets import WebSocket

class WebsocketHub:
    def __init__(self) -> None:
        self.connections: Set[WebSocket] = set()

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.connections.add(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        self.connections.discard(websocket)

    async def broadcast(self, message: Dict[str, Any]) -> None:
        disconnected = []
        for websocket in list(self.connections):
            try:
                await websocket.send_json(message)
            except Exception:
                disconnected.append(websocket)

        for websocket in disconnected:
            self.disconnect(websocket)

# create one global instance that the whole app can use
websocket_hub = WebsocketHub()
