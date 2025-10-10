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
    detach: bool = typer.Option(False, "--detach", "-d", help="Run in detached mode"),
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


