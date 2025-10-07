# src/svh/commands/db/db_template_utils.py
from __future__ import annotations
import json, shutil
from pathlib import Path
from typing import Any, Dict

BASE = Path(__file__).resolve().parent
CUSTOM_PATH  = BASE / "db_template.json"
DEFAULT_PATH = BASE / "db_template.default.json"

# Safe defaults for first run
DEFAULT_TEMPLATE: Dict[str, Any] = {
    "url": "sqlite:///./hive.sqlite",
    "use_existing": True,
}

def _ensure_files() -> None:
    if not DEFAULT_PATH.exists():
        DEFAULT_PATH.write_text(json.dumps(DEFAULT_TEMPLATE, indent=2))
    if not CUSTOM_PATH.exists():
        shutil.copyfile(DEFAULT_PATH, CUSTOM_PATH)

def load_db_template(use_custom: bool = True) -> Dict[str, Any]:
    _ensure_files()
    p = CUSTOM_PATH if use_custom else DEFAULT_PATH
    return json.loads(p.read_text(encoding="utf-8"))

def save_db_template(template_dict: Dict[str, Any]) -> None:
    _ensure_files()
    CUSTOM_PATH.write_text(json.dumps(template_dict, indent=2), encoding="utf-8")

def edit_db_template(edit_func) -> Dict[str, Any]:
    """Edit with a function that receives & returns a dict."""
    tpl = load_db_template(True)
    new_tpl = edit_func(dict(tpl)) or tpl
    save_db_template(new_tpl)
    return new_tpl

def patch_db_template(patch: Dict[str, Any]) -> Dict[str, Any]:
    """Convenience: merge a dict of key=value updates."""
    tpl = load_db_template(True)
    tpl.update(patch or {})
    save_db_template(tpl)
    return tpl

def reset_db_template() -> Dict[str, Any]:
    """Restore CUSTOM from DEFAULT."""
    _ensure_files()
    shutil.copyfile(DEFAULT_PATH, CUSTOM_PATH)
    return load_db_template(True)
