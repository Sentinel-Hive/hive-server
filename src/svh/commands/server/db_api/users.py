from __future__ import annotations
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import MetaData, Table, insert
from sqlalchemy.orm import Session

from ...db.session import session_scope, get_engine
from ...db.seed import create_user as _create_user, seed_users as _seed_users  # tuple-returning creator

router = APIRouter()

class CreateUserOut(BaseModel):
    user_id: str
    password: str
    is_admin: bool

@router.post("/create", response_model=CreateUserOut)
def create_user(admin: bool = False):
    """Create a single user (admin or non-admin)."""
    with session_scope() as s:  # type: Session
        uid, pwd, is_admin = _create_user(s, admin)
        return CreateUserOut(user_id=uid, password=pwd, is_admin=is_admin)

@router.post("/seed", response_model=list[CreateUserOut])
def seed(admins: int = 1, users: int = 5):
    """Seed initial users only if table is empty."""
    if admins < 0 or users < 0:
        raise HTTPException(400, "Counts must be >= 0")
    created = _seed_users(admins=admins, users=users)  # returns list[dict]
    # Normalize to CreateUserOut
    return [CreateUserOut(**row) for row in created]

class InsertRowIn(BaseModel):
    values: dict

@router.post("/insert/{table_name}")
def insert_row(table_name: str, body: InsertRowIn):
    """Generic insert helper (admin-only at client API level)."""
    engine = get_engine()
    md = MetaData()
    try:
        tbl = Table(table_name, md, autoload_with=engine)
    except Exception:
        raise HTTPException(400, f"Unknown table: {table_name}")
    with engine.begin() as conn:
        conn.execute(insert(tbl).values(**body.values))
    return {"ok": True}
