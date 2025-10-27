import typer
from svh.commands.server import main
import click
from svh.commands.server.firewall import firewall_ssh_status

app = typer.Typer(help="Server management commands")

# Attach sub-groups
app.add_typer(main.app, name="server")

@click.group()
def server():
    """Server management commands."""
    pass

@server.command()
@click.option("--config", "-c", default="config.yml", help="Path to config.yml")
def status(config: str):
    """Check firewall and SSH status."""
    result = firewall_ssh_status(config)
    
    if result["ok"]:
        click.secho("✓ Server firewall and SSH are configured correctly", fg="green")
    else:
        click.secho("✗ Issues detected with firewall or SSH configuration", fg="red")
        click.echo(f"\nDetails: {result['details']}")
        exit(1)
