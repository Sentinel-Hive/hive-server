from __future__ import annotations
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import MetaData, Table, insert
from sqlalchemy.orm import Session

from ...db.session import session_scope, get_engine
from ...db.seed import create_user as _create_user, seed_users as _seed_users  # tuple-returning creator
from ...db.seed import upsert_user as _upsert_user
from ...db.security import gen_password
from ...db.models import User, AuthToken
from sqlalchemy import func, select
from datetime import datetime
from pydantic import BaseModel
from fastapi import HTTPException

router = APIRouter()

class CreateUserOut(BaseModel):
    user_id: str
    password: str
    is_admin: bool

@router.post("/create", response_model=CreateUserOut)
def create_user(admin: bool = False):
    """Create a single user (admin or non-admin)."""
    with session_scope() as s:
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


@router.post("/reset/{user_id}", response_model=CreateUserOut)
def reset_user(user_id: str, is_admin: bool = False):
    """Reset (or create) a user with a new generated password and return the cleartext password.
    This endpoint should be protected at the client API level (require admin)."""
    with session_scope() as s:
        pwd = gen_password()
        out = _upsert_user(s, user_id, pwd, is_admin)
        # upsert_user returns a dict with password equal to provided pwd
        return CreateUserOut(user_id=out["user_id"], password=out["password"], is_admin=out["is_admin"])


class UserLoginOut(BaseModel):
    id: int
    user_id: str
    is_admin: bool
    last_login: datetime | None


@router.get("/logins", response_model=list[UserLoginOut])
def list_user_logins():
    """Return all users with the most-recent token issued_at (or None)."""
    with session_scope() as s:
        stmt = (
            select(User.id, User.user_id, User.is_admin, func.max(AuthToken.issued_at).label("last_login"))
            .outerjoin(AuthToken, User.id == AuthToken.user_id_fk)
            .group_by(User.id, User.user_id, User.is_admin)
            .order_by(User.user_id)
        )
        res = s.execute(stmt).all()
        out = []
        for row in res:
            # row columns: id, user_id, is_admin, last_login
            out.append({"id": int(row[0]), "user_id": row[1], "is_admin": bool(row[2]), "last_login": row[3]})
        return out


class RenameIn(BaseModel):
    # old_user_id may be a username (str) or, if a client accidentally sends the numeric id,
    # accept int as well and resolve by primary key. This makes the endpoint more robust
    # to frontend mistakes (but the frontend should send the username string).
    old_user_id: int | str
    new_user_id: str


@router.post("/rename")
def rename_user(body: RenameIn):
    """Rename a user's user_id. Returns ok and new user_id."""
    with session_scope() as s:
        # find existing user. Allow lookup by numeric id if client mistakenly passed an int.
        u = None
        try:
            # If old_user_id is an int (or a numeric string), try lookup by primary key first.
            if isinstance(body.old_user_id, int):
                u = s.scalar(select(User).where(User.id == int(body.old_user_id)))
            elif isinstance(body.old_user_id, str) and body.old_user_id.isdigit():
                # numeric string: try id lookup
                u = s.scalar(select(User).where(User.id == int(body.old_user_id)))
        except Exception:
            # ignore and fall back to username lookup
            u = None

        if not u:
            # fallback: lookup by username (user_id)
            u = s.scalar(select(User).where(User.user_id == str(body.old_user_id)))
        if not u:
            raise HTTPException(404, "User not found")
        # check conflict
        exists = s.scalar(select(User).where(User.user_id == body.new_user_id))
        if exists:
            raise HTTPException(400, "new_user_id already in use")
        u.user_id = body.new_user_id
        # session_scope commits on exit
        return {"ok": True, "user_id": body.new_user_id}



@router.delete("/delete/{user_identifier}")
def delete_user(user_identifier: int | str):
    """Delete a user by username or numeric id. Prevent deleting the last admin account."""
    with session_scope() as s:
        u = None
        try:
            if isinstance(user_identifier, int):
                u = s.scalar(select(User).where(User.id == int(user_identifier)))
            elif isinstance(user_identifier, str) and user_identifier.isdigit():
                u = s.scalar(select(User).where(User.id == int(user_identifier)))
        except Exception:
            u = None

        if not u:
            u = s.scalar(select(User).where(User.user_id == str(user_identifier)))
        if not u:
            raise HTTPException(404, "User not found")

        # disallow deleting the last admin
        if getattr(u, "is_admin", False):
            admin_count = s.scalar(select(func.count()).select_from(User).where(User.is_admin == True))
            if admin_count is None:
                admin_count = 0
            if int(admin_count) <= 1:
                raise HTTPException(400, "Cannot delete the last admin user")

        # delete (AuthToken rows cascade via FK/ondelete and relationship cascade)
        s.delete(u)
        return {"ok": True, "deleted_user_id": u.user_id}
