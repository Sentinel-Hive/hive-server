import traceback
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import TypeAdapter, ValidationError
from .hub import websocket_hub
from .schema import ClientMessage, PopupMessage, ErrorMessage
from svh import notify  # ← use your colored logger

router = APIRouter()

client_msg_adapter = TypeAdapter(ClientMessage)


@router.websocket("/websocket")
async def websocket_endpoint(websocket: WebSocket):
    token = websocket.query_params.get("token")
    notify.websocket(
        f"connect attempt: token={'present' if token else 'missing'}")

    try:
        await websocket.accept()
        await websocket_hub.connect(websocket)
        notify.websocket("connected OK")

        # Confirm to the connecting client
        await websocket.send_json(
            PopupMessage(
                type="popup", text="Connected to websocket").model_dump()
        )

        while True:
            try:
                raw = await websocket.receive_json()
                notify.websocket(f"recv raw: {raw!r}")

                try:
                    msg = client_msg_adapter.validate_python(raw)
                    notify.websocket(f"validated msg: {msg}")

                    if msg.type == "hello":
                        # Respond only to this websocket
                        await websocket.send_json(
                            PopupMessage(
                                type="popup", text=f"Hello {msg.client}!"
                            ).model_dump()
                        )

                    elif msg.type == "dev_popup":
                        # Broadcast to all connected clients
                        await websocket_hub.broadcast(
                            PopupMessage(
                                type="popup", text=f"[Broadcast] {msg.text}"
                            ).model_dump()
                        )

                    else:
                        await websocket.send_json(
                            PopupMessage(
                                type="popup",
                                text=f"Unknown message type: {msg.type}",
                            ).model_dump()
                        )

                except ValidationError as ve:
                    notify.error(f"validation error: {ve}")
                    await websocket.send_json(
                        ErrorMessage(type="error", detail=str(ve)).model_dump()
                    )

            except WebSocketDisconnect:
                notify.websocket("disconnect during receive")
                break
            except Exception as e:
                notify.error(f"exception in loop: {e}")
                traceback.print_exc()
                break

    except Exception as e:
        notify.error(f"top-level error: {e}")
        traceback.print_exc()
    finally:
        websocket_hub.disconnect(websocket)
        notify.websocket("connection closed")
