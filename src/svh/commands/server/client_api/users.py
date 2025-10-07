from __future__ import annotations
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import MetaData, Table, insert
from ...db.session import get_session
from ...db.security import gen_userid, gen_password, hash_password
from ...db.models import User

router = APIRouter()

class CreateUserOut(BaseModel):
    user_id: str
    password: str
    is_admin: bool

@router.post("/create", response_model=CreateUserOut)
def create_user(admin: bool = False):
    with get_session() as s:
        uid, pwd = _create_one(s, admin)
        return CreateUserOut(user_id=uid, password=pwd, is_admin=admin)

@router.post("/seed", response_model=list[CreateUserOut])
def seed_users(admins: int = 1, users: int = 5):
    if admins < 0 or users < 0:
        raise HTTPException(400, "Counts must be >= 0")
    out: list[CreateUserOut] = []
    with get_session() as s:
        for _ in range(admins):
            uid, pwd = _create_one(s, True)
            out.append(CreateUserOut(user_id=uid, password=pwd, is_admin=True))
        for _ in range(users):
            uid, pwd = _create_one(s, False)
            out.append(CreateUserOut(user_id=uid, password=pwd, is_admin=False))
    return out

class InsertRowIn(BaseModel):
    values: dict

@router.post("/insert/{table_name}")
def insert_row(table_name: str, body: InsertRowIn):
    # Generic insert: reflect and insert as-is
    from ...db.session import get_engine
    engine = get_engine()
    md = MetaData()
    try:
        tbl = Table(table_name, md, autoload_with=engine)
    except Exception:
        raise HTTPException(400, f"Unknown table: {table_name}")
    with engine.begin() as conn:
        conn.execute(insert(tbl).values(**body.values))
    return {"ok": True}

# --- helpers ---
def _create_one(s: Session, is_admin: bool):
    uid = gen_userid(); pwd = gen_password()
    salt_hex, pass_hash = hash_password(pwd)
    s.add(User(user_id=uid, is_admin=is_admin, salt_hex=salt_hex, pass_hash=pass_hash))
    s.flush()
    return uid, pwd
