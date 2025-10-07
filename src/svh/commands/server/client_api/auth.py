from __future__ import annotations
from datetime import datetime
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy import select, update as sa_update, delete as sa_delete

from .util import get_session_cm
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

def _prune_revoked_keep_latest(s, user_id_fk: int) -> None:
    """
    Keep only the most recent revoked token for this user; delete older revoked ones.
    """
    ids = s.scalars(
        select(AuthToken.id)
        .where(AuthToken.user_id_fk == user_id_fk, AuthToken.revoked_at.is_not(None))
        .order_by(AuthToken.revoked_at.desc(), AuthToken.id.desc())
    ).all()
    if len(ids) > 1:
        s.execute(sa_delete(AuthToken).where(AuthToken.id.in_(ids[1:])))

@router.post("/login", response_model=LoginOut)
def login(body: LoginIn):
    with get_session_cm() as s:
        user = s.scalar(select(User).where(User.user_id == body.user_id))
        if not user or not verify_password(body.password, user.salt_hex, user.pass_hash):
            raise HTTPException(401, "Invalid credentials")

        # Enforce single ACTIVE token: revoke any currently-active tokens for this user
        s.execute(
            sa_update(AuthToken)
            .where(AuthToken.user_id_fk == user.id, AuthToken.revoked_at.is_(None))
            .values(revoked_at=datetime.utcnow())
        )
        # After revoking, keep only the newest revoked entry (the one just revoked)
        _prune_revoked_keep_latest(s, user.id)

        # Issue brand-new active token
        token = make_token(user.user_id)
        s.add(AuthToken(user=user, token=token))
        cache.set(token, user.user_id, int(body.ttl or 3600))
        return LoginOut(token=token)

class LogoutIn(BaseModel):
    token: str | None = None

@router.post("/logout")
def logout(request: Request, body: LogoutIn | None = None):
    # Resolve token from body, header, or cookie
    token = (body.token if body and body.token else None)
    if not token:
        auth = request.headers.get("authorization") or ""
        if auth.lower().startswith("bearer "):
            token = auth.split(" ", 1)[1].strip()
    if not token:
        token = request.cookies.get("svh_token")
    if not token:
        raise HTTPException(400, "Token missing")

    with get_session_cm() as s:
        row = s.scalar(select(AuthToken).where(AuthToken.token == token))
        if row:
            # Mark this token revoked (logout time)
            if row.revoked_at is None:
                row.revoked_at = datetime.utcnow()
            # Keep only the most recent revoked for this user
            _prune_revoked_keep_latest(s, row.user_id_fk)

    cache.delete(token)
    resp = JSONResponse({"ok": True})
    resp.delete_cookie("svh_token")
    return resp

@router.get("/check")
def check(token: str):
    # ACTIVE only if present in in-memory cache (restart/log out → revoked)
    return {"status": "active"} if cache.get(token) else {"status": "revoked"}
