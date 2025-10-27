from __future__ import annotations
from pathlib import Path
from typing import Tuple
import os, yaml

# ---------- locate config.yml ----------

def _resolve_cfg_path() -> Path:
    """
    Resolution order:
      1) SVH_CONFIG_YML env:
         - if file -> use it
         - if directory -> append 'config.yml'
      2) Package-local: <this_dir>/config/config.yml
      3) CWD fallback:  ./src/svh/commands/server/config/config.yml
    """
    # 1) explicit override
    env = os.getenv("SVH_CONFIG_YML")
    if env:
        p = Path(env).expanduser()
        if p.is_dir():
            p = p / "config.yml"
        return p.resolve()

    here = Path(__file__).resolve()

    # 2) package-local (your canonical location)
    pkg_local = here.parent / "config" / "config.yml"
    if pkg_local.is_file():
        return pkg_local

    # 3) CWD fallback for odd run contexts
    cwd_fallback = Path.cwd() / "src" / "svh" / "commands" / "server" / "config" / "config.yml"
    if cwd_fallback.is_file():
        return cwd_fallback.resolve()

    # default to package-local path even if missing (useful for debug prints)
    return pkg_local

CFG_PATH = _resolve_cfg_path()
_cache = {"mtime": 0.0, "cfg": None}

def _read_cfg() -> dict:
    """
    Read YAML config or return sane defaults if missing/invalid.
    """
    try:
        if CFG_PATH.exists() and CFG_PATH.is_file():
            text = CFG_PATH.read_text(encoding="utf-8")
            data = yaml.safe_load(text)
            if isinstance(data, dict):
                return data
    except Exception:
        pass
    # Defaults when no/invalid YAML:
    return {
        "server": {"host": "0.0.0.0", "client_port": 5167, "db_port": 5169},
        "database": {"url": "sqlite:///./hive.sqlite"},
    }

def _cfg() -> dict:
    try:
        m = CFG_PATH.stat().st_mtime if CFG_PATH.exists() else 0.0
    except Exception:
        m = 0.0
    if _cache["cfg"] is None or _cache["mtime"] != m:
        _cache["cfg"] = _read_cfg()
        _cache["mtime"] = m
    return _cache["cfg"]

# ---------- getters (unchanged below this line) ----------

def get_client_bind() -> Tuple[str, int]:
    s = _cfg().get("server", {})
    host = str(s.get("host", "0.0.0.0"))
    port = int(s.get("client_port", 5167))
    return host, port

def get_db_bind() -> Tuple[str, int]:
    s = _cfg().get("server", {})
    host = str(s.get("host", "0.0.0.0"))
    port = int(s.get("db_port", 5169))
    return host, port

def get_client_base() -> str:
    host, port = get_client_bind()
    loopback = "127.0.0.1" if host in ("0.0.0.0", "::") else host
    return f"http://{loopback}:{port}"

def get_db_api_base_for_client() -> str:
    host, port = get_db_bind()
    loopback = "127.0.0.1" if host in ("0.0.0.0", "::") else host
    return f"http://{loopback}:{port}"

def get_database_url() -> str:
    # If you already added absolute path normalization, keep it here.
    return str(_cfg().get("database", {}).get("url", "sqlite:///./hive.sqlite"))
