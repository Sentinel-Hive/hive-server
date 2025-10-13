import typer
from svh.commands.db import main

app = typer.Typer(help="Database management commands")

# Attach DB subcommands
app.add_typer(main.app, name="main")
