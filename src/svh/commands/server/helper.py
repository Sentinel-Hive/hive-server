import ipaddress
import typer
import re
from pathlib import Path
import yaml
from svh import notify
import psutil
import os
import platform


def _process_exists(pid: int) -> bool:
    if platform.system() == "Windows":
        return psutil.pid_exists(pid)
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def isHost(value: str) -> bool:
    try:
        ipaddress.ip_address(value)
        return True
    except ValueError:
        pass

    domain_pattern = re.compile(r"^(?!-)(?:[a-zA-Z0-9-]{1,63}\.)+[a-zA-Z]{2,63}$")
    if domain_pattern.match(value) or value == "localhost":
        return True

    return False


def _invalid_config(field) -> bool:
    choice = input(
        f"Invalid {field} detected. Would you like to use the defualt? [y/n] "
    )
    if choice.lower() in ("y", "yes"):
        return True
    else:
        return False


def load_config(config_path: Path) -> dict:
    if not config_path.exists() or not config_path.is_file():
        notify.error(f"Config not found or is not a file: {config_path}")
        raise typer.Exit(code=1)

    try:
        with open(config_path, "r") as f:
            return yaml.safe_load(f)
    except yaml.YAMLError as e:
        notify.error(f"Invalid YAML in config: {e}")
        raise typer.Exit(code=1)
