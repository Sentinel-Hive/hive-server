import typer
from svh.commands.server import firewall

app = typer.Typer(help="Server management commands")

@app.command(help="Create and start the server.")
def start(
    config: str = typer.Option(
        "./default.yml",
        "--config",
        "-c",
        help="Path to the configuration file"
    )
):
    typer.echo(f"Starting server with config: {config}")

@app.command(help="Stop the server.")
def stop():
    typer.echo("Stopping server...")

@app.command(help="Delete current server instance.")
def delete():
    typer.echo("Deleting server...")

# Add firewall as a nested group
app.add_typer(firewall.app, name="firewall")
