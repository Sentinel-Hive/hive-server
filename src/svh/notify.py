import typer

# Define reusable styled tags
SERVER_TAG = typer.style("[SERVER]", fg=typer.colors.GREEN, bold=True)
DB_TAG = typer.style("[SERVER]", fg=typer.colors.BLUE, bold=True)
ERROR_TAG = typer.style("[ERROR]", fg=typer.colors.RED, bold=True)
INFO_TAG = typer.style("[INFO]", fg=typer.colors.YELLOW, bold=True)


def server(msg: str):
    typer.echo(f"{SERVER_TAG} {msg}")


def database(msg: str):
    typer.echo(f"{DB_TAG} {msg}")


def error(msg: str):
    typer.echo(f"{ERROR_TAG} {msg}")


def info(msg: str):
    typer.echo(f"{INFO_TAG} {msg}")
