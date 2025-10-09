from __future__ import annotations
import json, os, urllib.request, urllib.error, urllib.parse
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from .util import require_admin

DB_API_BASE = os.getenv("SVH_DB_API_BASE", "http://127.0.0.1:8001")

router = APIRouter()

def _db_post(path: str, payload: dict | None = None) -> dict:
    url = urllib.parse.urljoin(DB_API_BASE, path)
    data = None if payload is None else json.dumps(payload).encode("utf-8")
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

class CreateUserOut(BaseModel):
    user_id: str
    password: str
    is_admin: bool

class InsertRowIn(BaseModel):
    values: dict


@router.post("/create", response_model=CreateUserOut)
def create_user(admin: bool = False, _: object = Depends(require_admin)):
        out = _db_post("/users/create" + (f"?admin=true" if admin else ""))
        return CreateUserOut(**out)

@router.post("/seed", response_model=list[CreateUserOut])
def seed_users(admins: int = 1, users: int = 5, _: object = Depends(require_admin)):
    out = _db_post(f"/users/seed?admins={admins}&users={users}")
    return [CreateUserOut(**row) for row in out]

class InsertRowIn(BaseModel):
    values: dict

@router.post("/insert/{table_name}")
def insert_row(table_name: str, body: InsertRowIn, _: object = Depends(require_admin)):
    out = _db_post(f"/users/insert/{urllib.parse.quote(table_name)}", {"values": body.values})
    return out
