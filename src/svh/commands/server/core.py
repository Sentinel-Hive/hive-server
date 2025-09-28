import typer
from pathlib import Path
import yaml
from svh.commands.server import crud
from svh.commands.server import firewall
from svh import notify

app = typer.Typer(help="Server management commands")

DEFAULT_CONFIG_PATH = Path(__file__).parent / "config.yml"


@app.command(help="Create and start the server.")
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

    if not config_path.exists() or not config_path.is_file():
        notify.error(f"Config for server not found or is not a file: {config_path}")
        raise typer.Exit(code=1)

    try:
        with open(config_path, "r") as f:
            config_contents = yaml.safe_load(f)

        notify.server(f"Successfully read configuration file: {config_path}")
    except yaml.YAMLError as e:
        notify.error(f"Invalid YAML in config: {e}")
        raise typer.Exit(code=1)

    try:
        crud.start_server(config_contents)
    except Exception as e:
        notify.error(f"Unhandled error: {e}")
        raise typer.Exit(code=1)


@app.command(help="Stop the server.")
def stop():
    ok, msg = crud.stop_server()
    if ok:
        notify.server(msg)
    else:
        notify.error(msg)


@app.command(help="Delete current server instance.")
def delete():
    typer.echo("Deleting server...")


# Add firewall as a nested group
app.add_typer(firewall.app, name="firewall")
