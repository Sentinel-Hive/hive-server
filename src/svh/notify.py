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

# Styled tags
SERVER_TAG = typer.style("[SERVER]", fg=typer.colors.GREEN, bold=True)
FIREWALL_TAG = typer.style("[FIREWALL]", fg=typer.colors.MAGENTA, bold=True)
DB_TAG = typer.style("[SERVER]", fg=typer.colors.BLUE, bold=True)
ERROR_TAG = typer.style("[ERROR]", fg=typer.colors.RED, bold=True)
INFO_TAG = typer.style("[INFO]", fg=typer.colors.YELLOW, bold=True)


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
