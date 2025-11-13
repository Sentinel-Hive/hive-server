import typer
from datetime import datetime
from pathlib import Path
import socket

# Determine project root relative to this file
PROJECT_ROOT = Path(__file__).parent.parent.parent.resolve()
LOG_DIR = PROJECT_ROOT / "log"
LOG_DIR.mkdir(exist_ok=True)

# Timestamped log file (one per server run)
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
LOG_FILE = LOG_DIR / f".svh_server_{timestamp}.log"

# Styled tags
SERVER_TAG = typer.style("[SERVER]", fg=typer.colors.GREEN, bold=True)
FIREWALL_TAG = typer.style("[FIREWALL]", fg=typer.colors.MAGENTA, bold=True)
DB_TAG = typer.style("[DATABASE]", fg=typer.colors.BLUE, bold=True)
ERROR_TAG = typer.style("[ERROR]", fg=typer.colors.RED, bold=True)
INFO_TAG = typer.style("[INFO]", fg=typer.colors.YELLOW, bold=True)
WEBSOCKET_TAG = typer.style("[WEBSOCKET]", fg=typer.colors.CYAN, bold=True)

_cached_ip = None


def _get_local_ip() -> str:
    """Get the local IP address of this machine."""
    global _cached_ip
    if _cached_ip is not None:
        return _cached_ip
    
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        _cached_ip = ip
        return ip
    except Exception:
        _cached_ip = "127.0.0.1"
        return _cached_ip


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

def show_ip():
    """Display the server IP address."""
    ip = _get_local_ip()
    typer.echo(f"{SERVER_TAG} IP Address: {ip}")
    _write_log("SERVER", f"IP Address: {ip}")
