# src/svh/commands/db/seed.py
from __future__ import annotations
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from .session import session_scope
from .models import User
from .security import gen_userid, gen_password, hash_password

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
            created.append(_create_one(s, True))
        for _ in range(users):
            created.append(_create_one(s, False))
    return created

def _has_any_users(s: Session) -> bool:
    count = s.scalar(select(func.count()).select_from(User))
    return bool(count and count > 0)

def _create_one(s: Session, is_admin: bool) -> dict:
    uid = gen_userid()
    pwd = gen_password()
    salt_hex, pass_hash = hash_password(pwd)
    s.add(User(user_id=uid, is_admin=is_admin, salt_hex=salt_hex, pass_hash=pass_hash))
    # no commit here; session_scope handles commit
    return {"user_id": uid, "password": pwd, "is_admin": is_admin}

# Re-export the creator with a public name
create_user = _create_one
__all__ = ["seed_users", "create_user"]
