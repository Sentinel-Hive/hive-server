import typer
from svh.commands.server import core, firewall

app = typer.Typer(help="Server management commands")

# Attach sub-groups
app.add_typer(core.app, name="core")
app.add_typer(firewall.app, name="firewall")
