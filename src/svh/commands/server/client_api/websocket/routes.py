from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import Optional
from .hub import websocket_hub
from .schema import ClientMessage, Echo, ServerMessage
from pydantic import ValidationError
from svh import notify

router = APIRouter()


async def verify_websocket_token(token: Optional[str]) -> bool:
    return True  # TEMP while testing; wire real auth later


@router.websocket("/websocket")
async def websocket_endpoint(websocket: WebSocket):
    token = websocket.query_params.get("token")
    notify.websocket(
        f"connect attempt: token={'present' if token else 'none'}")

    await websocket_hub.connect(websocket)
    notify.websocket("connected")

    # Welcome immediately so you can see it on connect
    await websocket.send_json(ServerMessage(text="Connected to websocket").model_dump())

    try:
        while True:
            raw = await websocket.receive_json()
            notify.websocket(f"recv: {raw!r}")

            try:
                msg = ClientMessage.model_validate(raw)
            except ValidationError as ve:
                await websocket.send_json({
                    "type": "error",
                    "detail": "Invalid client message",
                    "errors": ve.errors(),
                })
                continue

            if msg.type == "hello":
                await websocket.send_json(ServerMessage(text="Welcome!").model_dump())
            elif msg.type == "dev_popup":
                await websocket.send_json(ServerMessage(text=msg.text).model_dump())
            else:
                await websocket.send_json(Echo(payload=raw).model_dump())

    except WebSocketDisconnect as e:
        notify.websocket(
            f"disconnected (code={getattr(e, 'code', 'unknown')})")
        websocket_hub.disconnect(websocket)
