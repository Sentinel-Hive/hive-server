from __future__ import annotations
import os
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy import MetaData, Table, insert
from .util import get_session_cm, require_admin
from ...db.seed import create_user as _create_user  # canonical creator
from ...db.session import get_engine

router = APIRouter()

# Toggle public registration (no token) for dev if desired
PUBLIC_SIGNUP = os.getenv("SVH_PUBLIC_SIGNUP", "false").lower() == "true"

class CreateUserOut(BaseModel):
    user_id: str
    password: str
    is_admin: bool

@router.post("/create", response_model=CreateUserOut)
def create_user(admin: bool = False, _: object = Depends(require_admin)):
    with get_session_cm() as s:
        uid, pwd, is_admin = _create_user(s, admin)
        return CreateUserOut(user_id=uid, password=pwd, is_admin=is_admin)

@router.post("/seed", response_model=list[CreateUserOut])
def seed_users(admins: int = 1, users: int = 5, _: object = Depends(require_admin)):
    if admins < 0 or users < 0:
        raise HTTPException(400, "Counts must be >= 0")
    out: list[CreateUserOut] = []
    with get_session_cm() as s:
        for _ in range(admins):
            uid, pwd, is_admin = _create_user(s, True)
            out.append(CreateUserOut(user_id=uid, password=pwd, is_admin=is_admin))
        for _ in range(users):
            uid, pwd, is_admin = _create_user(s, False)
            out.append(CreateUserOut(user_id=uid, password=pwd, is_admin=is_admin))
    return out

class InsertRowIn(BaseModel):
    values: dict

@router.post("/insert/{table_name}")
def insert_row(table_name: str, body: InsertRowIn, _: object = Depends(require_admin)):
    engine = get_engine()
    md = MetaData()
    try:
        tbl = Table(table_name, md, autoload_with=engine)
    except Exception:
        raise HTTPException(400, f"Unknown table: {table_name}")
    with engine.begin() as conn:
        conn.execute(insert(tbl).values(**body.values))
    return {"ok": True}

@router.post("/register", response_model=CreateUserOut)
def register_user():
    """Public sign-up (disabled by default). Set SVH_PUBLIC_SIGNUP=true to enable."""
    if not PUBLIC_SIGNUP:
        raise HTTPException(403, "Public signup is disabled")
    with get_session_cm() as s:
        uid, pwd, is_admin = _create_user(s, False)
        return CreateUserOut(user_id=uid, password=pwd, is_admin=is_admin)
