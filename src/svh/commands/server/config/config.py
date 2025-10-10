import typer
from pathlib import Path
from svh.commands.server.helper import load_config
from svh import notify
import subprocess
import os
import yaml

config_app = typer.Typer(help="Manage server configuration")
DEFAULT_CONFIG_PATH = Path(__file__).parent / "config.yml"


@config_app.command("show", help="Show current configuration")
def show(config: Path = typer.Option(None, "--config", "-c", exists=True)):
    config_path = config or DEFAULT_CONFIG_PATH
    cfg = load_config(config_path)
    notify.info("\n" + yaml.safe_dump(cfg, sort_keys=False))


@config_app.command("edit", help="Edit configuration in your text editor")
def edit(config: Path = typer.Option(None, "--config", "-c", exists=True)):
    config_path = config or DEFAULT_CONFIG_PATH

    if not config_path.exists():
        with open(config_path, "w") as f:
            yaml.safe_dump({}, f)

    before_content = config_path.read_text()

    editor = os.environ.get("EDITOR", "nano")
    subprocess.run([editor, str(config_path)])

    after_content = config_path.read_text()

    if before_content == after_content:
        notify.info("Edit exited without changes.")
    else:
        notify.info(f"Configuration saved to {config_path}")
