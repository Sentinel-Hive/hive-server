import traceback
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import TypeAdapter, ValidationError
from .hub import websocket_hub
from .schema import ClientMessage, PopupMessage, ErrorMessage
from svh import notify
from datetime import datetime, timezone
import uuid


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

                # ---- short-circuit dev_alert (not part of ClientMessage union) ----
                if isinstance(raw, dict) and raw.get("type") == "dev_alert":
                    alert = {
                        "type": "alert",
                        "id": str(uuid.uuid4()),
                        "title": (raw.get("title") or "Test Alert").strip(),
                        # critical|high|medium|low
                        "severity": (raw.get("severity") or "medium").lower(),
                        "source": raw.get("source") or "dev",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "description": raw.get("description"),
                        "tags": raw.get("tags") or [],
                    }
                    await websocket_hub.broadcast(alert)
                    notify.websocket("broadcasted alert from dev_alert")
                    continue
                # -------------------------------------------------------------------

                # Existing validation for hello/dev_popup, unchanged
                try:
                    msg = client_msg_adapter.validate_python(raw)
                    notify.websocket(f"validated msg: {msg}")

                    if msg.type == "hello":
                        await websocket.send_json(
                            PopupMessage(
                                type="popup", text=f"Hello {msg.client}!").model_dump()
                        )

                    elif msg.type == "dev_popup":
                        await websocket_hub.broadcast(
                            PopupMessage(
                                type="popup", text=f"[Broadcast] {msg.text}").model_dump()
                        )

                    else:
                        await websocket.send_json(
                            PopupMessage(
                                type="popup", text=f"Unknown message type: {msg.type}").model_dump()
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
