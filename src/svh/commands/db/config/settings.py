# src/svh/commands/db/config/settings.py
from __future__ import annotations
import os
from dataclasses import dataclass

@dataclass(frozen=True)
class DBSettings:
    # Template JSON file path (can be a packaged default)
    template_path: str = os.getenv("SVH_DB_TEMPLATE", "db.template.json")
    # Default DB URL (SQLite file by default)
    url: str = os.getenv("SVH_DB_URL", "sqlite:///./hive.sqlite")
    # Dev flags (used by server for CORS, etc.)
    dev_cors: bool = os.getenv("SVH_DEV_CORS", "true").lower() in ("1","true","yes")
    #Dataset folder path (default)
    datasets_folder: str = os.getenv("SVH_DATASETS_FOLDER", "datasets")

def get_settings() -> DBSettings:
    return DBSettings()
