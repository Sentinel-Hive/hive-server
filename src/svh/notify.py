import typer
from datetime import datetime
from pathlib import Path

# Determine project root relative to this file
PROJECT_ROOT = Path(__file__).parent.parent.parent.resolve()
LOG_DIR = PROJECT_ROOT / "log"
LOG_DIR.mkdir(exist_ok=True)

# Timestamped log file (one per server run)
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
LOG_FILE = LOG_DIR / f".svh_server_{timestamp}.log"

# Available colors that are accepted (ERROR will remain red)
_AVAILABLE_ACCENTS = {"green", "magenta", "blue", "red", "yellow", "cyan"}

# original default (used for reset)
_ORIGINAL_DEFAULT = "green"

# default accent used for non-error tags
_default_accent = _ORIGINAL_DEFAULT

# Persisted color storage (per-user)
import os, json
_CONFIG_DIR = os.path.join(os.path.expanduser("~"), ".config", "svh")
_ACCENT_FILE = os.path.join(_CONFIG_DIR, "accent.json")


def _make_tags(accent: str):
    # keep ERROR and INFO in sensible defaults, let accent control most tags
    return {
        "SERVER": typer.style("[SERVER]", fg=accent, bold=True),
        "FIREWALL": typer.style("[FIREWALL]", fg=accent, bold=True),
        "DATABASE": typer.style("[DATABASE]", fg=accent, bold=True),
        "ERROR": typer.style("[ERROR]", fg=typer.colors.RED, bold=True),
        "INFO": typer.style("[INFO]", fg=typer.colors.YELLOW, bold=True),
        "WEBSOCKET": typer.style("[WEBSOCKET]", fg=accent, bold=True),
    }

# initialize mutable tag variables
_tags = _make_tags(_default_accent)
SERVER_TAG = _tags["SERVER"]
FIREWALL_TAG = _tags["FIREWALL"]
DB_TAG = _tags["DATABASE"]
ERROR_TAG = _tags["ERROR"]
INFO_TAG = _tags["INFO"]
WEBSOCKET_TAG = _tags["WEBSOCKET"]


def _apply_accent(accent: str):
    """Apply accent to in-memory tag variables without writing persistence."""
    global SERVER_TAG, FIREWALL_TAG, DB_TAG, ERROR_TAG, INFO_TAG, WEBSOCKET_TAG, _tags, _default_accent
    _default_accent = accent
    _tags = _make_tags(accent)
    SERVER_TAG = _tags["SERVER"]
    FIREWALL_TAG = _tags["FIREWALL"]
    DB_TAG = _tags["DATABASE"]
    ERROR_TAG = _tags["ERROR"]
    INFO_TAG = _tags["INFO"]
    WEBSOCKET_TAG = _tags["WEBSOCKET"]


def set_accent_color(color: str) -> None:
    if not color:
        raise ValueError("Empty color")
    c = color.strip().lower()
    if c not in _AVAILABLE_ACCENTS:
        raise ValueError(f"Unsupported color: {color}. Supported: {', '.join(sorted(_AVAILABLE_ACCENTS))}")

    # apply in-memory
    _apply_accent(c)

    # persist choice
    try:
        os.makedirs(_CONFIG_DIR, exist_ok=True)
        with open(_ACCENT_FILE, "w", encoding="utf-8") as fh:
            json.dump({"color": c}, fh)
    except Exception:
        pass


def get_available_accent_colors():
    return sorted(_AVAILABLE_ACCENTS)


def _load_persisted_accent():
    try:
        if os.path.exists(_ACCENT_FILE):
            with open(_ACCENT_FILE, "r", encoding="utf-8") as fh:
                j = json.load(fh)
                c = (j.get("color") or "").strip().lower()
                if c in _AVAILABLE_ACCENTS:
                    _apply_accent(c)
    except Exception:
        pass


# attempt to load persisted accent on import
_load_persisted_accent()

def reset_accent_to_default() -> None:
    """
    Reset accent to the original default and remove any persisted accent selection.
    """
    try:
        _apply_accent(_ORIGINAL_DEFAULT)
    except Exception:
        pass
    # remove persisted file so subsequent invocations start with original default
    try:
        if os.path.exists(_ACCENT_FILE):
            os.remove(_ACCENT_FILE)
    except Exception:
        pass


def _write_log(tag: str, msg: str):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"{timestamp} [{tag}] {msg}\n"
    with LOG_FILE.open("a", encoding="utf-8") as f:
        f.write(line)


def server(msg: str):
    typer.echo(f"{SERVER_TAG} {msg}")
    _write_log("SERVER", msg)


def firewall(msg: str):
    typer.echo(f"{FIREWALL_TAG} {msg}")
    _write_log("FIREWALL", msg)


def database(msg: str):
    typer.echo(f"{DB_TAG} {msg}")
    _write_log("DB", msg)


def error(msg: str):
    typer.echo(f"{ERROR_TAG} {msg}")
    _write_log("ERROR", msg)


def info(msg: str):
    typer.echo(f"{INFO_TAG} {msg}")
    _write_log("INFO", msg)


def websocket(msg: str):
    typer.echo(f"{WEBSOCKET_TAG} {msg}")
    _write_log("WEBSOCKET", msg)
