# src/svh/commands/db/seed.py
from __future__ import annotations
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from .session import session_scope
from .models import User
from .security import gen_userid, gen_password, hash_password

def _has_any_users(s: Session) -> bool:
    count = s.scalar(select(func.count()).select_from(User))
    return bool(count and count > 0)

# canonical creator: returns a tuple
def create_user(s: Session, is_admin: bool) -> tuple[str, str, bool]:
    uid = gen_userid()
    pwd = gen_password()
    salt_hex, pass_hash = hash_password(pwd)
    s.add(User(user_id=uid, is_admin=is_admin, salt_hex=salt_hex, pass_hash=pass_hash))
    # no commit here; session_scope handles commit
    return uid, pwd, is_admin

def seed_users(admins: int, users: int) -> list[dict]:
    """Seed the DB with N admins and M users on an empty users table.
       Returns a list of {user_id, password, is_admin} for created accounts.
    """
    if admins < 0 or users < 0:
        raise ValueError("admins/users must be >= 0")

    created: list[dict] = []
    with session_scope() as s:
        if _has_any_users(s):
            return created  # already initialized; do nothing
        for _ in range(admins):
            uid, pwd, a = create_user(s, True)
            created.append({"user_id": uid, "password": pwd, "is_admin": a})
        for _ in range(users):
            uid, pwd, a = create_user(s, False)
            created.append({"user_id": uid, "password": pwd, "is_admin": a})
    return created

def upsert_user(s: Session, user_id: str, password: str, is_admin: bool = True) -> dict:
    """
    Create or update a user with a fixed user_id/password.
    Returns: {user_id, password, is_admin, created: bool}
    """
    # lazy import to avoid circulars at module import time
    salt_hex, pass_hash = hash_password(password)
    user = s.scalar(select(User).where(User.user_id == user_id))
    created = False
    if user:
        user.is_admin = is_admin
        user.salt_hex = salt_hex
        user.pass_hash = pass_hash
    else:
        user = User(user_id=user_id, is_admin=is_admin, salt_hex=salt_hex, pass_hash=pass_hash)
        s.add(user)
        created = True
    return {"user_id": user_id, "password": password, "is_admin": is_admin, "created": created}

__all__ = ["seed_users", "create_user", "upsert_user"]

