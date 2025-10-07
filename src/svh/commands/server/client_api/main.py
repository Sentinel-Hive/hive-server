from __future__ import annotations
from contextlib import asynccontextmanager
from datetime import datetime
import os
from fastapi.middleware.cors import CORSMiddleware

from fastapi import FastAPI
from sqlalchemy import select, update as sa_update

from ...db.session import session_scope
from ...db.models import AuthToken

@asynccontextmanager
async def lifespan(app: FastAPI):
    # STARTUP: mark any active tokens revoked (restart requires fresh login),
    # then prune per-user to keep only the most recent revoked entry.
    with session_scope() as s:
        s.execute(
            sa_update(AuthToken)
            .where(AuthToken.revoked_at.is_(None))
            .values(revoked_at=datetime.utcnow())
        )
        user_ids = s.scalars(select(AuthToken.user_id_fk).distinct()).all()
        for uid in user_ids:
            # prune: keep only most recent revoked for each user
            ids = s.scalars(
                select(AuthToken.id)
                .where(AuthToken.user_id_fk == uid, AuthToken.revoked_at.is_not(None))
                .order_by(AuthToken.revoked_at.desc(), AuthToken.id.desc())
            ).all()
            if len(ids) > 1:
                from sqlalchemy import delete as sa_delete
                s.execute(sa_delete(AuthToken).where(AuthToken.id.in_(ids[1:])))
    yield
    # SHUTDOWN: best-effort revoke any remaining "active" rows (shouldn't be any)
    with session_scope() as s:
        s.execute(
            sa_update(AuthToken)
            .where(AuthToken.revoked_at.is_(None))
            .values(revoked_at=datetime.utcnow())
        )
        # no need to prune again here; next startup will handle it
        

app = FastAPI(title="SVH Client API", lifespan=lifespan)
DEV_CORS = os.getenv("SVH_DEV_CORS", "true").lower() in ("1", "true", "yes")

# CORS for local dev/testing with svh-web (http://localhost:1420) TEMPORARY-- later use Tauri HTTP plugin.
if DEV_CORS:
    app.add_middleware(
        CORSMiddleware,
        # Dev webview origin for Tauri/Vite
        allow_origins=["http://localhost:1420", "http://127.0.0.1:1420"],
        # Optional: allow packaged Tauri scheme in prod builds
        allow_origin_regex=r"tauri://.*",
        allow_credentials=True,   # harmless since you use Bearer tokens
        allow_methods=["*"],      # covers preflight + all verbs
        allow_headers=["*"],      # lets you send Authorization, etc.
    )

from .auth import router as auth_router
from .users import router as users_router
from .health import router as health_router

app.include_router(health_router, prefix="/health", tags=["health"])
app.include_router(users_router,  prefix="/users",  tags=["users"])
app.include_router(auth_router,   prefix="/auth",   tags=["auth"])
