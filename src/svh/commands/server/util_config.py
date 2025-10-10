from __future__ import annotations
from pathlib import Path
from typing import Tuple
import os, yaml

# ---------- locate config.yml robustly ----------

def _resolve_cfg_path() -> Path:
    """
    Resolution order:
      1) SVH_CONFIG_YML environment variable:
         - if points to a file -> use it
         - if points to a directory -> append 'config.yml'
      2) Repo-standard path: <repo_root>/server/config/config.yml
      3) Legacy fallback:     <repo_root>/server/config.yml
      4) CWD fallbacks:       ./server/config/config.yml, then ./server/config.yml
    """
    # 1) Explicit env override
    env = os.getenv("SVH_CONFIG_YML")
    if env:
        p = Path(env).expanduser()
        if p.is_dir():
            p = p / "config.yml"
        return p.resolve()

    # Helper: guess repo root from this file location (…/src/svh/commands/server/util_config.py)
    here = Path(__file__).resolve()
    # repo_root ≈ here.parents[4]  (…/src/ -> parent -> repo root)
    # Defensive: check a couple of parent depths to be safe across layouts.
    candidates_root = []
    for depth in (4, 5):
        try:
            candidates_root.append(here.parents[depth])
        except IndexError:
            pass

    candidates: list[Path] = []
    for root in candidates_root:
        candidates += [
            root / "server" / "config" / "config.yml",  # new location
            root / "server" / "config.yml",             # legacy
        ]
    # also try from current working directory (dev runs)
    cwd = Path.cwd()
    candidates += [
        cwd / "server" / "config" / "config.yml",
        cwd / "server" / "config.yml",
    ]

    for p in candidates:
        if p.is_file():
            return p.resolve()

    # default to where it *should* be, even if missing
    return (candidates_root[0] / "server" / "config" / "config.yml") if candidates_root else (cwd / "server" / "config" / "config.yml")

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
        "server": {"host": "0.0.0.0", "client_port": 8000, "db_port": 8001},
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
    port = int(s.get("client_port", 8000))
    return host, port

def get_db_bind() -> Tuple[str, int]:
    s = _cfg().get("server", {})
    host = str(s.get("host", "0.0.0.0"))
    port = int(s.get("db_port", 8001))
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
