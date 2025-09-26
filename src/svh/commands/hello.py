import typer

hello_app = typer.Typer(help="Hello-related commands")

@hello_app.command("world")
def hello_world():
    """
    Print 'hello world'.
    """
    typer.echo("hello world")
