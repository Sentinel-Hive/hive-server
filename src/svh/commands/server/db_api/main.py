from __future__ import annotations
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI
from sqlalchemy import select, update as sa_update, delete as sa_delete
from sqlalchemy.exc import OperationalError
from ...db.session import session_scope
from ...db.models import AuthToken
import platform
from svh.commands.db.session import create_all, session_scope
from svh.commands.db.models import AuthToken

@asynccontextmanager
async def lifespan(app: FastAPI):
    create_all()

    try:
        with session_scope() as s:
            s.execute(
                sa_update(AuthToken)
                .where(AuthToken.revoked_at.is_(None))
                .values(revoked_at=datetime.utcnow())
            )
    except OperationalError:
        pass

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
from .data import router as data_router
app.include_router(auth_router, prefix="/auth", tags=["auth"])
app.include_router(users_router, prefix="/users", tags=["users"])
app.include_router(data_router, tags=["data"])