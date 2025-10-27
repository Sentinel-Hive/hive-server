from __future__ import annotations

import os
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import Body, FastAPI, Header, HTTPException, Request, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware

from svh import notify

# Routers from client_api
from .websocket.routes import router as websocket_router
from .websocket.hub import websocket_hub
from .health import router as health_router
from .users import router as users_router
from .auth import router as auth_router

# Optional: your pydantic alert models (we will not rely on them strictly for 'audience')
from .alerts_schema import AlertIn, AlertOut  # if present


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(title="SVH Client API", lifespan=lifespan)
DEV_CORS = os.getenv("SVH_DEV_CORS", "true").lower() in ("1", "true", "yes")

# CORS for local dev/testing with svh-web (http://localhost:1420)
if DEV_CORS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:1420", "http://127.0.0.1:1420"],
        allow_origin_regex=r"tauri://.*",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


from .auth import router as auth_router
from .users import router as users_router
from .health import router as health_router
from .data import router as data_router

app.include_router(health_router, prefix="/health", tags=["health"])
app.include_router(users_router,  prefix="/users",  tags=["users"])
app.include_router(auth_router,   prefix="/auth",   tags=["auth"])
app.include_router(data_router,   tags=["data"])
app.include_router(websocket_router, tags=["websocket"])



@app.post("/ingest")
async def ingest(request: Request, files: Optional[List[UploadFile]] = File(None)):
    try:
        if files:
            count = len(files)
            notify.server(f"Received {count} file(s) via multipart/form-data")
            return {"status": "received", "files_received": count}

        content_type = request.headers.get("content-type", "")
        if "application/json" in content_type:
            data = await request.json()
            count = len(data.get("files", [])) if isinstance(data, dict) else 0
            notify.server(f"Received {count} file(s) via JSON payload")
            return {"status": "received", "files_received": count}

        notify.error(f"Unsupported Content-Type: {content_type}")
        return {"status": "error", "detail": f"Unsupported Content-Type: {content_type}"}
    except Exception as e:
        notify.error(f"Error processing ingestion request: {e}")
        return {"status": "error", "detail": str(e)}


@app.post("/notify")
async def notify_popup(body: dict = Body(...), x_notify_key: str | None = Header(default=None)):
    """
    Broadcast a simple popup to clients.
    Body:
      {
        "text": "message",
        "audience": "all" | "admins"   # optional, default "all"
      }
    """
    # Optional protection via notify key (keeps behavior consistent with alerts)
    required = os.getenv("SVH_NOTIFY_KEY")
    if required and x_notify_key != required:
        raise HTTPException(status_code=403, detail="Forbidden")

    text = str(body.get("text", "")).strip()
    if not text:
        raise HTTPException(status_code=400, detail="`text` is required")

    audience = (body.get("audience") or "all").lower()
    if audience not in {"all", "admins"}:
        raise HTTPException(
            status_code=400, detail="Invalid `audience` (use 'all' or 'admins')")

    payload = {"type": "popup", "text": text}

    if audience == "admins":
        await websocket_hub.broadcast_admins(payload)
    else:
        await websocket_hub.broadcast(payload)

    return {"ok": True}


@app.post("/alerts/notify")
async def alerts_notify(
    # accept raw dict so we can handle optional 'audience'
    body: dict = Body(...),
    x_notify_key: str | None = Header(default=None),
):
    """
    Broadcast a structured alert to clients.
    Body shape (minimal):
      {
        "title": "Alert title",
        "severity": "critical|high|medium|low",   # default "medium"
        "source": "server",                        # default "server"
        "description": "optional",
        "tags": ["optional","list"],
        "audience": "all" | "admins"               # default "all"
      }
    """

    # Optional protection via notify key
    required = os.getenv("SVH_NOTIFY_KEY")
    if required and x_notify_key != required:
        raise HTTPException(status_code=403, detail="Forbidden")

    title = (body.get("title") or "").strip()
    if not title:
        raise HTTPException(status_code=400, detail="`title` is required")

    severity = (body.get("severity") or "medium").lower()
    if severity not in {"critical", "high", "medium", "low"}:
        raise HTTPException(status_code=400, detail="Invalid `severity`")

    audience = (body.get("audience") or "all").lower()
    if audience not in {"all", "admins"}:
        raise HTTPException(
            status_code=400, detail="Invalid `audience` (use 'all' or 'admins')")

    alert = {
        "type": "alert",
        "id": str(uuid.uuid4()),
        "title": title,
        "severity": severity,
        "source": (body.get("source") or "server"),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "description": body.get("description"),
        "tags": body.get("tags") or [],
    }

    # Route to the right audience
    if audience == "admins":
        await websocket_hub.broadcast_admins(alert)
    else:
        await websocket_hub.broadcast(alert)

    return {"ok": True, "id": alert["id"], "timestamp": alert["timestamp"]}
