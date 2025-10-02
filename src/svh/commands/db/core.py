import typer
import os
from svh import db

app = typer.Typer(help="Database management commands")

@app.command(help="Create a new database from the template (if not exists or --force).")
def create(force: bool = typer.Option(False, "--force", help="Force recreate the database if it exists.")):
    if db.db_exists() and not force:
        typer.echo("Database already exists. Use --force to recreate.")
        return
    if db.db_exists() and force:
        os.remove(db.DB_PATH)
        typer.echo("Existing database deleted.")
    db.create_db_from_template()
    typer.echo("Database created from template.")


@app.command(help="Delete the database file.")
def delete():
    if db.db_exists():
        os.remove(db.DB_PATH)
        typer.echo("Database deleted.")
    else:
        typer.echo("No database file found.")


@app.command(help="Reset the database template to default settings.")
def reset_template():
    db.reset_db_to_default()
    typer.echo("Database template reset to default settings.")


@app.command(help="Edit the database template using a JSON file.")
def edit_template(json_path: str):
    import json
    if not os.path.exists(json_path):
        typer.echo(f"File not found: {json_path}")
        raise typer.Exit(1)
    with open(json_path, 'r', encoding='utf-8') as f:
        new_template = json.load(f)
    from svh.db_template_utils import save_db_template
    save_db_template(new_template)
    typer.echo("Database template updated from provided JSON file.")
