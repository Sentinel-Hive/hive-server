from __future__ import annotations
from datetime import datetime
import json, os, urllib.request, urllib.error
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from .util import get_session_cm

from ...db.token import cache

DB_API_BASE = os.getenv("SVH_DB_API_BASE", "http://127.0.0.1:8001")

router = APIRouter()

class LoginIn(BaseModel):
    user_id: str
    password: str
    ttl: int | None = 3600  # seconds

class LoginOut(BaseModel):
    token: str

def _db_post(path: str, payload: dict) -> dict:
    url = DB_API_BASE + path
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
    out = _db_post("/auth/login", {"user_id": body.user_id, "password": body.password, "ttl": body.ttl or 3600})
    token = out.get("token")
    user_id = out.get("user_id")
    if not token or not user_id:
        raise HTTPException(502, "Bad response from DB API")
    cache.set(token, user_id, int(body.ttl or 3600))
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

    # Tell DB API to mark it revoked & prune; then drop from cache
    try:
        _db_post("/auth/logout", {"token": token})
    except HTTPException:
        # even if DB fails, we still clear local cache so user is logged out here
        pass
    
    cache.delete(token)
    resp = JSONResponse({"ok": True})
    resp.delete_cookie("svh_token")
    return resp

@router.get("/check")
def check(token: str):
    # ACTIVE only if present in in-memory cache (restart/log out → revoked)
    return {"status": "active"} if cache.get(token) else {"status": "revoked"}
