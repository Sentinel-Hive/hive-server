from __future__ import annotations

import traceback
from datetime import datetime, timezone
import uuid
from typing import Optional, Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy import select

from svh import notify
from .hub import websocket_hub

# Use your existing DB session + models
from svh.commands.db.session import session_scope
from svh.commands.db.models import User, AuthToken

router = APIRouter()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _make_popup(text: str) -> dict:
    return {"type": "popup", "text": text}


def _make_alert(
    *,
    title: str,
    severity: str = "medium",
    source: str = "server",
    description: Optional[str] = None,
    tags: Optional[list[str]] = None,
) -> dict:
    return {
        "type": "alert",
        "id": str(uuid.uuid4()),
        "title": title,
        "severity": (severity or "medium").lower(),
        "source": source or "server",
        "timestamp": _now_iso(),
        "description": description,
        "tags": tags or [],
    }


def _resolve_token(token_str: Optional[str]) -> tuple[Optional[str], bool]:
    """
    Resolve a bearer token string to (user_id, is_admin).
    Returns (None, False) if invalid or revoked.
    """
    if not token_str:
        return (None, False)
    with session_scope() as s:
        row = s.execute(
            select(User, AuthToken)
            .join(AuthToken, AuthToken.user_id_fk == User.id)
            .where(AuthToken.token == token_str, AuthToken.revoked_at.is_(None))
        ).first()
        if not row:
            return (None, False)
        user, _token = row
        return (user.user_id, bool(user.is_admin))


@router.websocket("/websocket")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket entrypoint. Validates the query token, attaches metadata to the hub,
    then routes client messages by their 'type'.
    """
    token = websocket.query_params.get("token")
    notify.websocket(f"connect attempt: token={'present' if token else 'missing'}")

    try:
        # Validate token *before* accepting
        user_id, is_admin = _resolve_token(token)
        if not user_id:
            await websocket.close(code=4401)
            notify.websocket("rejected: invalid token")
            return

        await websocket.accept()
        await websocket_hub.connect(websocket, user_id=user_id, is_admin=is_admin)

        # Optional: confirm to connecting client
        await websocket.send_json(_make_popup("Connected to websocket"))

        while True:
            try:
                raw: Any = await websocket.receive_json()
                # notify.websocket(f"recv raw: {raw!r}")  # uncomment for debug spam

                # Fast-path dev helper: send alerts directly from Dev page
                if isinstance(raw, dict) and raw.get("type") == "dev_alert":
                    alert = _make_alert(
                        title=(raw.get("title") or "Test Alert").strip(),
                        severity=(raw.get("severity") or "medium"),
                        source=(raw.get("source") or "dev"),
                        description=raw.get("description"),
                        tags=raw.get("tags") or [],
                    )
                    await websocket_hub.broadcast(alert)
                    continue

                # Developer popup broadcast
                if isinstance(raw, dict) and raw.get("type") == "dev_popup":
                    text = (raw.get("text") or "").strip() or "Test popup"
                    await websocket_hub.broadcast(_make_popup(f"[Broadcast] {text}"))
                    continue

                # Unknown message type
                await websocket.send_json(
                    {"type": "error", "detail": "Unknown message type"}
                )

            except WebSocketDisconnect:
                # Client disconnected
                break
            except Exception as e:
                notify.error(f"exception in loop: {e!r}")
                traceback.print_exc()
                break

    except Exception as e:
        notify.error(f"top-level error: {e!r}")
        traceback.print_exc()
    finally:
        websocket_hub.disconnect(websocket)
        notify.websocket("connection closed")
