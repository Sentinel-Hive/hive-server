import os
import json
import typer
from sqlalchemy import inspect

from svh.commands.db.session import create_all, get_engine
from svh.commands.db.db_template_utils import (
    load_db_template,
    save_db_template,
    reset_db_template,
)

app = typer.Typer(help="Database management commands")

# ---- helpers ---------------------------------------------------------------

def _sqlite_path_from_url(url: str) -> str | None:
    # Supports sqlite:///relative/path.sqlite  and sqlite:///C:/absolute/path.sqlite
    prefix = "sqlite:///"
    if url.startswith(prefix):
        return os.path.abspath(url[len(prefix):])
    return None

def _db_exists() -> bool:
    cfg = load_db_template()
    url = cfg.get("url", "sqlite:///./hive.sqlite")
    sqlite_path = _sqlite_path_from_url(url)
    if sqlite_path:
        return os.path.exists(sqlite_path)
    # non-SQLite: consider DB "existing" if any tables exist
    eng = get_engine()
    return bool(inspect(eng).get_table_names())


# ---- commands --------------------------------------------------------------

@app.command(help="Create a new database from the template (if not exists or --force).")
def create(
    force: bool = typer.Option(
        False, "--force", help="Force recreate the database if it exists."
    ),
    seed_admins: int | None = typer.Option(
        None, "--seed-admins", help="Admins to create on first init."
    ),
    seed_users: int | None = typer.Option(
        None, "--seed-users", help="Users to create on first init."
    ),
    prompt: bool = typer.Option(
        True, "--prompt/--no-prompt", help="Ask for seed counts on first init if not provided."
    ),
):
    exists = _db_exists()
    first_time = (not exists) or force

    if exists and not force:
        typer.echo("Database already exists. Use --force to recreate.")
        return

    if exists and force:
        cfg = load_db_template()
        url = cfg.get("url", "sqlite:///./hive.sqlite")
        sqlite_path = _sqlite_path_from_url(url)
        if sqlite_path and os.path.exists(sqlite_path):
            os.remove(sqlite_path)
            typer.echo("Existing SQLite database file deleted.")
        else:
            # For non-SQLite we won’t drop the remote DB from the CLI.
            typer.echo("Non-SQLite URL detected; skipping physical deletion (will reuse connection).")

    # (re)create schema per current template URL
    create_all()
    typer.echo("Database created/initialized from template URL.")

    # --- First-time seeding logic ---
    if first_time:
        cfg = load_db_template()
        admins = seed_admins if seed_admins is not None else int(cfg.get("seed_admins", 0))
        users  = seed_users  if seed_users  is not None else int(cfg.get("seed_users", 0))

        if admins == 0 and users == 0 and prompt:
            admins = typer.prompt("How many ADMIN users to auto-create?", default=1, type=int)
            users  = typer.prompt("How many NON-admin users to auto-create?", default=0, type=int)

        # Persist chosen defaults back to the template (optional convenience)
        cfg["seed_admins"], cfg["seed_users"] = int(admins), int(users)
        save_db_template(cfg)

        if admins < 0 or users < 0:
            typer.echo("Seed counts must be >= 0")
            raise typer.Exit(1)

        try:
            from svh.commands.db.seed import seed_users as do_seed
            created = do_seed(admins, users)
            if created:
                typer.echo("Initial users created:")
                for c in created:
                    typer.echo(f"  user_id={c['user_id']} password={c['password']} admin={c['is_admin']}")
            else:
                typer.echo("Users already exist; skipping initial seeding.")
        except Exception as e:
            typer.echo(f"[WARN] Seeding skipped due to error: {e}")


@app.command(help="Delete the database (SQLite file only; non-SQLite is not dropped).")
def delete():
    cfg = load_db_template()
    url = cfg.get("url", "sqlite:///./hive.sqlite")
    sqlite_path = _sqlite_path_from_url(url)
    if sqlite_path and os.path.exists(sqlite_path):
        os.remove(sqlite_path)
        typer.echo("Database deleted.")
    else:
        typer.echo("No SQLite database file found (or non-SQLite URL). Nothing deleted.")


@app.command(help="Reset the database template to default settings.")
def reset_template_cmd():
    reset_db_template()
    typer.echo("Database template reset to default settings.")


@app.command(help="Edit the database template using a JSON file.")
def edit_template(json_path: str):
    if not os.path.exists(json_path):
        typer.echo(f"File not found: {json_path}")
        raise typer.Exit(1)
    with open(json_path, "r", encoding="utf-8") as f:
        new_template = json.load(f)
    save_db_template(new_template)
    typer.echo("Database template updated from provided JSON file.")
