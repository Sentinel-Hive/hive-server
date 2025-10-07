from __future__ import annotations
import json
from pathlib import Path
from typing import Any, Dict

BASE = Path(__file__).resolve().parent
DEFAULT_PATH = BASE / "db_template.default.json"
CUSTOM_PATH  = BASE / "db_template.json"

DEFAULT_TEMPLATE = {
    "url": "sqlite:///./hive.sqlite",
    "use_existing": True
}

def _ensure_files():
    if not DEFAULT_PATH.exists():
        DEFAULT_PATH.write_text(json.dumps(DEFAULT_TEMPLATE, indent=2))
    if not CUSTOM_PATH.exists():
        CUSTOM_PATH.write_text(DEFAULT_PATH.read_text())

def load(use_custom: bool = True) -> Dict[str, Any]:
    _ensure_files()
    return json.loads((CUSTOM_PATH if use_custom else DEFAULT_PATH).read_text())

def edit(patch: Dict[str, Any]) -> Dict[str, Any]:
    cfg = load(True)
    cfg.update(patch)
    CUSTOM_PATH.write_text(json.dumps(cfg, indent=2))
    return cfg

def reset() -> Dict[str, Any]:
    _ensure_files()
    CUSTOM_PATH.write_text(DEFAULT_PATH.read_text())
    return load(True)