import typer
from svh.commands.server import main as serverCore
from svh.commands.db import main as dbCore

app = typer.Typer(
    help="Hive-Server CLI",
    add_completion=False,
    context_settings={"help_option_names": ["-h", "-help", "--h", "--help"]},
)

app.add_typer(serverCore.app, name="server")
app.add_typer(dbCore.app, name="db")
