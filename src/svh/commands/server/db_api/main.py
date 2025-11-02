from __future__ import annotations

from fastapi import FastAPI
import platform

from .auth import router as auth_router
from .users import router as users_router


app = FastAPI(title="SVH DB API")


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
