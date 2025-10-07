from __future__ import annotations
from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel
from sqlalchemy import select
from datetime import datetime
from .util import get_session
from ...db.models import User, AuthToken
from ...db.security import verify_password
from ...db.token import make_token, cache

router = APIRouter()

class LoginIn(BaseModel):
    user_id: str
    password: str
    ttl: int | None = 3600  # seconds

class LoginOut(BaseModel):
    token: str

@router.post("/login", response_model=LoginOut)
def login(body: LoginIn):
    with get_session() as s:
        user = s.scalar(select(User).where(User.user_id == body.user_id))
        if not user or not verify_password(body.password, user.salt_hex, user.pass_hash):
            raise HTTPException(401, "Invalid credentials")
        token = make_token(user.user_id)
        s.add(AuthToken(user=user, token=token))
        s.flush()
        cache.set(token, user.user_id, int(body.ttl or 3600))
        return LoginOut(token=token)

class LogoutIn(BaseModel):
    token: str

@router.post("/logout")
def logout(body: LogoutIn):
    from sqlalchemy import select
    with get_session() as s:
        row = s.scalar(select(AuthToken).where(AuthToken.token == body.token))
        if row and not row.revoked_at:
            row.revoked_at = datetime.utcnow()
    cache.delete(body.token)
    return {"ok": True}

@router.get("/check")
def check(token: str):
    if cache.get(token):
        return {"status": "active", "source": "cache"}
    with get_session() as s:
        from sqlalchemy import select
        row = s.scalar(select(AuthToken).where(AuthToken.token == token))
        return {"status": "active", "source": "db"} if (row and not row.revoked_at) else {"status": "revoked"}
