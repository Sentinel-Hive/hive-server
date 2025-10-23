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

from typing import Optional, List


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


@app.command(help='Broadcast to clients (popup or fallback to alert).')
def broadcast(
    message: str = typer.Argument(...),
    base_url: str = typer.Option("http://127.0.0.1:5167", "--base-url", "-b"),
    key: str | None = typer.Option(None, "--key"),
):
    import json
    import os
    import urllib.request
    import urllib.error
    from svh import notify

    endpoints = ["/notify", "/alerts/notify"]  # try popup, then alert
    headers = {"Content-Type": "application/json"}
    key = key or os.getenv("SVH_NOTIFY_KEY")
    if key:
        headers["X-Notify-Key"] = key

    for ep in endpoints:
        url = base_url.rstrip("/") + ep
        if ep == "/notify":
            payload = {"text": message}
        else:
            payload = {"title": message, "severity": "medium", "source": "cli"}

        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url, data=data, headers=headers, method="POST")
        notify.server(f"Broadcasting to {url}")
        try:
            with urllib.request.urlopen(req, timeout=5) as resp:
                out = json.loads(resp.read().decode("utf-8"))
                if out.get("ok"):
                    notify.server("Broadcast sent.")
                    return
                else:
                    notify.error(f"Server response: {out}")
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", errors="ignore")
            notify.error(f"HTTP {e.code} {e.reason} — {detail}")
        except urllib.error.URLError as e:
            notify.error(f"Failed to reach API: {e.reason}")

    raise typer.Exit(code=1)


@app.command(help="Send a structured alert to all connected clients (via /alerts/notify).")
def alert(
    title: str = typer.Argument(..., help="Alert title"),
    severity: str = typer.Option(
        "medium", "--severity", "-s", help="critical|high|medium|low"),
    source: str = typer.Option(
        "server", "--source", help="Origin (e.g., api-gw, db-core)"),
    description: Optional[str] = typer.Option(
        None, "--desc", help="Longer text"),
    tags: List[str] = typer.Option(
        [], "--tag", help="Repeatable: --tag api --tag errors"),
    base_url: str = typer.Option(
        "http://127.0.0.1:5167", "--base-url", "-b", help="Client API base URL"),
    key: Optional[str] = typer.Option(
        None, "--key", help="Notify key (or env SVH_NOTIFY_KEY)"),
):
    sev = severity.lower()
    if sev not in {"critical", "high", "medium", "low"}:
        notify.error("Invalid --severity. Use: critical|high|medium|low")
        raise typer.Exit(code=1)

    payload = {
        "title": title,
        "severity": sev,
        "source": source,
        "description": description,
        "tags": tags,
    }

    url = base_url.rstrip("/") + "/alerts/notify"
    headers = {"Content-Type": "application/json"}
    key = key or os.getenv("SVH_NOTIFY_KEY")
    if key:
        headers["X-Notify-Key"] = key

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url, data=data, headers=headers, method="POST")

    notify.server(f"Sending alert → {url}")
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            out = json.loads(resp.read().decode("utf-8"))
            if out.get("ok"):
                notify.server(f"Alert sent (id={out.get('id')})")
            else:
                notify.error(f"Server response: {out}")
                raise typer.Exit(code=1)
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="ignore")
        notify.error(f"HTTP {e.code} {e.reason} — {detail}")
        raise typer.Exit(code=1)
    except urllib.error.URLError as e:
        notify.error(f"Failed to reach API: {e.reason}")
        raise typer.Exit(code=1)
