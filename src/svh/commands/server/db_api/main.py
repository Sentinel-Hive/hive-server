from __future__ import annotations
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI
from sqlalchemy import update as sa_update
from sqlalchemy.exc import OperationalError
import platform
from svh.commands.db.session import create_all, session_scope
from svh.commands.db.models import AuthToken

from .auth import router as auth_router
from .users import router as users_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1) Ensure tables exist before anything else
    create_all()

    # 2) Best effort: revoke any non-revoked tokens from prior run
    try:
        with session_scope() as s:
            s.execute(
                sa_update(AuthToken)
                .where(AuthToken.revoked_at.is_(None))
                .values(revoked_at=datetime.utcnow())
            )
            # session_scope() handles commit
    except OperationalError:
        # If the table truly didn’t exist yet or any race, skip silently.
        # Next request has a fully created schema anyway.
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


app.include_router(auth_router, prefix="/auth", tags=["auth"])
app.include_router(users_router, prefix="/users", tags=["users"])
