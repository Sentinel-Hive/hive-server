import typer
from pathlib import Path
from svh.commands.server import crud
from svh.commands.server.helper import load_config
from svh import notify

app = typer.Typer(help="Server management commands")

DEFAULT_CONFIG_PATH = Path(__file__).parent / "config.yml"


@app.command(help="Create and start Client and DB API servers.")
def start(
    config: Path = typer.Option(
        None,
        "--config",
        "-c",
        help="Path to the configuration file",
        exists=True,
    )
):
    config_path = config if config else DEFAULT_CONFIG_PATH
    cfg = load_config(config_path)

    notify.server(f"Successfully loaded config: {config_path}")

    try:
        crud.start_user_server(cfg)
        crud.start_db_server(cfg)
    except Exception as e:
        notify.error(f"Unhandled error while starting servers: {e}")
        raise typer.Exit(code=1)


@app.command(help="Stop both the Client and DB API servers.")
def stop():
    try:
        crud.stop_client_server()
        crud.stop_db_server()
    except Exception as e:
        notify.error(f"Unhandled error while stopping servers: {e}")
        raise typer.Exit(code=1)


@app.command(help="Start only the Client API server.")
def start_client(
    config: Path = typer.Option(
        None,
        "--config",
        "-c",
        help="Path to the configuration file",
        exists=True,
    )
):
    config_path = config if config else DEFAULT_CONFIG_PATH
    cfg = load_config(config_path)
    crud.start_user_server(cfg)


@app.command(help="Stop only the Client API server.")
def stop_client():
    crud.stop_client_server()


@app.command(help="Start only the DB API server.")
def start_db(
    config: Path = typer.Option(
        None,
        "--config",
        "-c",
        help="Path to the configuration file",
        exists=True,
    )
):
    config_path = config if config else DEFAULT_CONFIG_PATH
    cfg = load_config(config_path)
    crud.start_db_server(cfg)


@app.command(help="Stop only the DB API server.")
def stop_db():
    crud.stop_db_server()


@app.command(help="List all API servers currently running.")
def list():
    crud.list_servers()
