import typer
from svh.commands import hello

app = typer.Typer(help="Hive-Server CLI")

app.add_typer(hello.hello_app, name="hello")
