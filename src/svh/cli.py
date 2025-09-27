import typer
from svh.commands.server import core as serverCore
from svh.commands.db import core as dbCore

app = typer.Typer(help="Hive-Server CLI")

app.add_typer(serverCore.app, name="server")
app.add_typer(dbCore.app, name="db")
