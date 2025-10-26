from __future__ import annotations
from datetime import datetime
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, update as sa_update, delete as sa_delete

from ...db.session import session_scope
from ...db.models import User, AuthToken
from ...db.security import verify_password
from ...db.token import make_token

router = APIRouter()

class LoginIn(BaseModel):
    user_id: str
    password: str
    ttl: int | None = 3600  # kept for compatibility; cache TTL is enforced by client API

class LoginOut(BaseModel):
    token: str
    user_id: str
    is_admin: bool

@router.post("/login", response_model=LoginOut)
def login(body: LoginIn):
    with session_scope() as s:
        user = s.scalar(select(User).where(User.user_id == body.user_id))
        if not user or not verify_password(body.password, user.salt_hex, user.pass_hash):
            raise HTTPException(401, "Invalid credentials")

        # Issue a new active token row. Do not revoke existing tokens here
        # to avoid accidental logout of other active sessions (for example
        # when the frontend refreshes and re-authenticates). Token revocation
        # is still performed on explicit logout via /auth/logout.
        token = make_token(user.user_id)
        s.add(AuthToken(user=user, token=token))
        return LoginOut(token=token, user_id=user.user_id, is_admin=bool(user.is_admin))

class LogoutIn(BaseModel):
    token: str

@router.post("/logout")
def logout(body: LogoutIn):
    with session_scope() as s:
        row = s.scalar(select(AuthToken).where(AuthToken.token == body.token))
        if not row:
            # idempotent: ok even if nothing to revoke
            return {"ok": True}
        if row.revoked_at is None:
            row.revoked_at = datetime.utcnow()
        # prune: keep only most-recent revoked for this user
        ids = s.scalars(
            select(AuthToken.id)
            .where(AuthToken.user_id_fk == row.user_id_fk, AuthToken.revoked_at.is_not(None))
            .order_by(AuthToken.revoked_at.desc(), AuthToken.id.desc())
        ).all()
        if len(ids) > 1:
            s.execute(sa_delete(AuthToken).where(AuthToken.id.in_(ids[1:])))
    return {"ok": True}
