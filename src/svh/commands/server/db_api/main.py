from __future__ import annotations
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI
from sqlalchemy import select, update as sa_update, delete as sa_delete
from ...db.session import session_scope
from ...db.models import AuthToken
import platform

@asynccontextmanager
async def lifespan(app: FastAPI):
    # On startup: mark all active tokens revoked; then prune to keep only latest revoked per user
    with session_scope() as s:
        s.execute(sa_update(AuthToken).where(AuthToken.revoked_at.is_(None)).values(revoked_at=datetime.utcnow()))
        user_ids = s.scalars(select(AuthToken.user_id_fk).distinct()).all()
        for uid in user_ids:
            ids = s.scalars(
                select(AuthToken.id)
                .where(AuthToken.user_id_fk == uid, AuthToken.revoked_at.is_not(None))
                .order_by(AuthToken.revoked_at.desc(), AuthToken.id.desc())
            ).all()
            if len(ids) > 1:
                s.execute(sa_delete(AuthToken).where(AuthToken.id.in_(ids[1:])))
    yield

app = FastAPI(title="SVH DB API", lifespan=lifespan)

@app.get("/health")
def health():
    return {"service": "DB_HANDLER", "status": "ok"}


@app.get("/metadata")
def metadata():
    return {
        "service": "DB_HANDLER",
        "version": "0.1.0",
        "python": platform.python_version(),
    }

from .auth import router as auth_router
from .users import router as users_router
app.include_router(auth_router, prefix="/auth", tags=["auth"])
app.include_router(users_router, prefix="/users", tags=["users"])