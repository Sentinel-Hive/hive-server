from __future__ import annotations
from contextlib import contextmanager
from fastapi import Depends, Request, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select
from ...db.session import session_scope, create_all
from ...db.models import User
from ...db.token import cache  # <-- check cache ONLY

@contextmanager
def get_session_cm():
    """Context manager for imperative code paths."""
    create_all()
    with session_scope() as s:
        yield s

def get_db():
    """FastAPI dependency (must be a generator that yields)."""
    create_all()
    with session_scope() as s:
        yield s

def _token_from_request(req: Request) -> str | None:
    # Prefer Authorization: Bearer <token>
    auth = req.headers.get("authorization") or ""
    if auth.lower().startswith("bearer "):
        return auth.split(" ", 1)[1].strip()
    # Optional cookie fallback
    tok = req.cookies.get("svh_token")
    return tok or None

def current_user(req: Request, db: Session = Depends(get_db)) -> User:
    """
    Require that the token is present in the in-memory cache.
    If the server restarts (cache cleared) or the user logs out,
    the token is not in cache => 401 (must login again).
    """
    token = _token_from_request(req)
    if not token:
        raise HTTPException(401, "Not authenticated")
    user_id = cache.get(token)
    if not user_id:
        # cache miss => token is not active
        raise HTTPException(401, "Session expired; please login again")
    user = db.scalar(select(User).where(User.user_id == user_id))
    if not user:
        raise HTTPException(401, "Account not found")
    return user

def require_admin(user: User = Depends(current_user)) -> User:
    if not user.is_admin:
        raise HTTPException(403, "Admin only")
    return user
