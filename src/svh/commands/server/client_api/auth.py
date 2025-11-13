from __future__ import annotations
from typing import Optional
import json, urllib.request, urllib.error
from fastapi import APIRouter, HTTPException, Request, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from svh.commands.server.util_config import get_db_api_base_for_client
from .util import current_user
from svh import notify

from ...db.token import cache
from ...db.models import User


router = APIRouter()


class LoginIn(BaseModel):
    user_id: str
    password: str
    ttl: int | None = 3600  # seconds


class LoginOut(BaseModel):
    token: str
    user_id: str
    is_admin: bool


def _db_post(path: str, payload: dict) -> dict:
    url = get_db_api_base_for_client() + path
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req) as r:
            raw = r.read().decode("utf-8")
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        try:
            msg = e.read().decode("utf-8")
        except Exception:
            msg = e.reason
        raise HTTPException(e.code, msg)
    except urllib.error.URLError as e:
        raise HTTPException(502, f"DB API unavailable: {e}")


@router.post("/login", response_model=LoginOut)
def login(body: LoginIn):
    res = _db_post(
        "/auth/login",
        {"user_id": body.user_id, "password": body.password, "ttl": body.ttl or 3600},
    )

    token: Optional[str] = res.get("token")
    user_id: Optional[str] = res.get("user_id")
    is_admin: Optional[bool] = res.get("is_admin")

    if not token or not user_id:
        raise HTTPException(502, "Bad response from DB API")
    else:
        notify.server(f"{user_id} logged in with {body.ttl}s TTL")

    cache.set(token, user_id, int(body.ttl or 3600))

    return LoginOut(token=token, user_id=user_id, is_admin=bool(is_admin))


class LogoutIn(BaseModel):
    user_id: str
    token: str | None = None


@router.post("/logout")
def logout(request: Request, body: LogoutIn | None = None):
    # Resolve token from body, header, or cookie
    user_id = body.user_id if body and body.user_id else None
    token = body.token if body and body.token else None
    if not token:
        auth = request.headers.get("authorization") or ""
        if auth.lower().startswith("bearer "):
            token = auth.split(" ", 1)[1].strip()
    if not token:
        token = request.cookies.get("svh_token")
    if not token:
        raise HTTPException(400, "Token missing")

    # Tell DB API to mark it revoked & prune; then drop from cache
    try:
        _db_post("/auth/logout", {"token": token})
    except HTTPException:
        # even if DB fails, we still clear local cache so user is logged out here
        pass

    cache.delete(token)
    resp = JSONResponse({"ok": True})

    notify.server(f"{user_id} with token:'{token}' logged out.")

    resp.delete_cookie("svh_token")
    return resp


@router.get("/check")
def check(token: str):
    # ACTIVE only if present in in-memory cache (restart/log out → revoked)
    return {"status": "active"} if cache.get(token) else {"status": "revoked"}


@router.get("/whoami")
def whoami(user: User = Depends(current_user)):
    return {"user_id": user.user_id, "is_admin": user.is_admin}


class RefreshOut(BaseModel):
    token: str
    expires_in: int


@router.post("/refresh", response_model=RefreshOut)
def refresh_token(user: User = Depends(current_user), request: Request = None):
    """
    Refresh an existing authentication token.
    Validates the current token and issues a new one with fresh TTL.
    """
    # Get the current token from request
    token = None
    if request:
        auth = request.headers.get("authorization") or ""
        if auth.lower().startswith("bearer "):
            token = auth.split(" ", 1)[1].strip()
        if not token:
            token = request.cookies.get("svh_token")

    if not token:
        raise HTTPException(401, "Token missing for refresh")

    # Verify the current token is still valid in cache
    cached_user_id = cache.get(token)
    if not cached_user_id or cached_user_id != user.user_id:
        raise HTTPException(401, "Invalid or expired token")

    # Generate new token with fresh TTL (default 1 hour)
    new_ttl = 3600  # 1 hour

    # Request new token from DB API
    try:
        res = _db_post(
            "/auth/login",
            {"user_id": user.user_id, "password": "", "ttl": new_ttl, "refresh": True},
        )
        new_token = res.get("token")

        if not new_token:
            # Fallback: generate token locally if DB doesn't support refresh
            from ...db.token import make_token
            new_token = make_token(user.user_id, new_ttl)

    except Exception as e:
        # Fallback to local token generation
        notify.server(f"Token refresh DB API error (using fallback): {e}")
        from ...db.token import make_token
        new_token = make_token(user.user_id, new_ttl)

    # Invalidate old token and cache new one
    cache.delete(token)
    cache.set(new_token, user.user_id, new_ttl)

    notify.server(f"{user.user_id} refreshed token (TTL: {new_ttl}s)")

    return RefreshOut(token=new_token, expires_in=new_ttl)
