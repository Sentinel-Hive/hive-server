import typer
from svh.commands.db import core

app = typer.Typer(help="Database management commands")

# Attach DB subcommands
app.add_typer(core.app, name="core")
