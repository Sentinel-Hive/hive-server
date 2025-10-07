import typer
from svh.commands.server import main as serverCore
from svh.commands.db import core as dbCore
from svh.commands.server.client_api.cli import app as api_app

app = typer.Typer(
    help="Hive-Server CLI",
    add_completion=False,
    context_settings={"help_option_names": ["-h", "-help", "--h", "--help"]},
)

app.add_typer(serverCore.app, name="server")
app.add_typer(dbCore.app, name="db")
app.add_typer(api_app, name="api", help="Call Client API endpoints (auth, users, health).")
