from pathlib import Path
from svh.commands.server.helper import load_config

STATE_FILE = Path(".svh_current_config")


def save_config_state(config_path: Path):
    try:
        STATE_FILE.write_text(str(config_path.resolve()))
    except Exception as e:
        raise RuntimeError(f"Failed to save config state: {e}")


def load_config_state() -> dict:
    if not STATE_FILE.exists():
        raise FileNotFoundError(
            "No saved config state found. Did you start the server with a config?"
        )
    cfg_path = Path(STATE_FILE.read_text().strip())
    if not cfg_path.exists():
        raise FileNotFoundError(
            f"The saved config file {cfg_path} does not exist anymore."
        )
    return load_config(cfg_path)


def clear_config_state():
    if STATE_FILE.exists():
        STATE_FILE.unlink(missing_ok=True)
