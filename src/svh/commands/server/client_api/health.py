from __future__ import annotations
from fastapi import APIRouter
import os, pathlib, urllib.request, urllib.error
from svh.commands.server.util_config import (
    get_db_api_base_for_client, get_db_bind, get_client_bind, _resolve_cfg_path
)

router = APIRouter()

@router.get("/ready")
def ready():
    return {"ok": True}

@router.get("/db")
def db_health():
    base = get_db_api_base_for_client()
    url = base + "/openapi.json"  # cheap GET on the DB API
    try:
        with urllib.request.urlopen(url, timeout=2) as r:
            return {"ok": True, "db_base": base, "status": r.status}
    except urllib.error.URLError as e:
        return {"ok": False, "db_base": base, "error": str(e)}

@router.get("/debug")
def debug():
    cfg_path = _resolve_cfg_path()
    exists = cfg_path.exists() and cfg_path.is_file()
    chost, cport = get_client_bind()
    dhost, dport = get_db_bind()
    return {
        "cwd": os.getcwd(),
        "cfg_path": str(cfg_path),
        "cfg_exists": exists,
        "client_bind": f"{chost}:{cport}",
        "db_bind": f"{dhost}:{dport}",
        "db_base_for_client": get_db_api_base_for_client(),
        "SVH_DB_API_BASE": os.getenv("SVH_DB_API_BASE"),
        "SVH_CONFIG_YML": os.getenv("SVH_CONFIG_YML"),
    }