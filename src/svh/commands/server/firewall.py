import typer

app = typer.Typer(help="Firewall commands")

@app.command()
def open():
    typer.echo("Opening firewall...")

@app.command()
def close():
    typer.echo("Closing firewall...")
