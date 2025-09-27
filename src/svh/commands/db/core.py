import typer

app = typer.Typer(help="Database management commands")


@app.command(help="Create a database.")
def create():
    typer.echo("Creating db...")


@app.command(help="Edit a database.")
def edit():
    typer.echo("Changing db...")


@app.command(help="Delete a database.")
def delete():
    typer.echo("Deleting db...")
