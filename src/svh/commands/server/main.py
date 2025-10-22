from svh import notify
import urllib.error
import urllib.request
import os
import json
import typer
from pathlib import Path
from svh.commands.server import crud
from svh.commands.server.manager import manage_service
from svh.commands.server.helper import load_config
from svh.commands.server.cli_auth import attach_auth_commands
from svh.commands.server.config import config, state

app = typer.Typer(help="Server management commands")

app.add_typer(config.config_app, name="config")

DEFAULT_CONFIG_PATH = Path(__file__).parent / "config/config.yml"

attach_auth_commands(app)


@app.command(help="Start one or more API servers.")
def start(
    service: str = typer.Option(
        "all", "--service", "-s", help="Service to start (client, db, or all)"
    ),
    config: Path = typer.Option(
        None, "--config", "-c", help="Path to configuration file", exists=True
    ),
    detach: bool = typer.Option(
        False, "--detach", "-d", help="Run in detached mode"),
):
    config_path = config or DEFAULT_CONFIG_PATH
    cfg = load_config(config_path)
    state.save_config_state(config_path)
    manage_service("start", service, cfg, detach=detach)


@app.command(help="Stop one or more API servers.")
def stop(
    service: str = typer.Option(
        "all", "--service", "-s", help="Service to stop (client, db, or all)"
    ),
):
    cfg_path = state.load_config_state()
    manage_service("stop", service, cfg_path)


@app.command(help="List all API servers currently running.")
def list():
    crud.list_servers()


@app.command(help='Broadcast a popup to all connected clients via the client API /notify endpoint.')
def broadcast(
    message: str = typer.Argument(..., help='Text to show in the popup'),
    base_url: str = typer.Option(
        "http://127.0.0.1:5167", "--base-url", "-b", help="Client API base URL"),
    key: str | None = typer.Option(
        None, "--key", help="Notify key; defaults to $SVH_NOTIFY_KEY if set"),
):
    url = base_url.rstrip("/") + "/notify"
    headers = {"Content-Type": "application/json"}

    # Allow --key or environment variable
    key = key or os.getenv("SVH_NOTIFY_KEY")
    if key:
        headers["X-Notify-Key"] = key

    data = json.dumps({"text": message}).encode("utf-8")
    req = urllib.request.Request(
        url, data=data, headers=headers, method="POST")

    notify.server(f"Broadcasting to {url}")
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
            if payload.get("ok"):
                notify.server("Broadcast sent.")
            else:
                notify.error(f"Broadcast response: {payload}")
                raise typer.Exit(code=1)

    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="ignore")
        notify.error(f"Broadcast failed: HTTP {e.code} {e.reason} — {detail}")
        raise typer.Exit(code=1)

    except urllib.error.URLError as e:
        notify.error(f"Broadcast failed: {e.reason}")
        raise typer.Exit(code=1)
