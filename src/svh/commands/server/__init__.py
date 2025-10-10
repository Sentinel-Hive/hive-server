import typer
from svh.commands.server import main

app = typer.Typer(help="Server management commands")

# Attach sub-groups
app.add_typer(main.app, name="server")
