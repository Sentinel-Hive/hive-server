from __future__ import annotations
from contextlib import asynccontextmanager
import os
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, Request, UploadFile, File
from typing import List, Optional
import platform
from datetime import datetime
from svh import notify


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield

app = FastAPI(title="SVH Client API", lifespan=lifespan)
DEV_CORS = os.getenv("SVH_DEV_CORS", "true").lower() in ("1", "true", "yes")

# CORS for local dev/testing with svh-web (http://localhost:1420) TEMPORARY-- later use Tauri HTTP plugin.
if DEV_CORS:
    app.add_middleware(
        CORSMiddleware,
        # Dev webview origin for Tauri/Vite
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
        return {
            "status": "error",
            "detail": f"Unsupported Content-Type: {content_type}",
        }

    except Exception as e:
        notify.error(f"Error processing ingestion request: {e}")
        return {"status": "error", "detail": str(e)}
