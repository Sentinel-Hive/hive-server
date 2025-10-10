import os
import json
import typer
from sqlalchemy import inspect, MetaData, Table, select, func, text
from datetime import datetime
from sqlalchemy import update as sa_update, delete as sa_delete

from svh.commands.db.session import create_all, get_engine, session_scope
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

@app.command(help="Show the SQLite file path if using sqlite:///; otherwise print the URL.")
def path():
    cfg = load_db_template()
    url = cfg.get("url", "sqlite:///./hive.sqlite")
    sqlite_path = _sqlite_path_from_url(url)
    if sqlite_path:
        typer.echo(sqlite_path)
    else:
        typer.echo(url)

@app.command(help="List tables and row counts.")
def tables():
    create_all()
    eng = get_engine()
    insp = inspect(eng)
    names = sorted(insp.get_table_names())
    if not names:
        typer.echo("(no tables)")
        return
    for t in names:
        with eng.connect() as conn:
            # safe because t comes from introspection, not user input
            cnt = conn.execute(select(func.count()).select_from(Table(t, MetaData(), autoload_with=eng))).scalar_one()
        typer.echo(f"{t}\t{cnt}")

@app.command(help="Show schema for a table (columns, types, nullable, primary key).")
def schema(table: str):
    create_all()
    eng = get_engine()
    insp = inspect(eng)
    if table not in insp.get_table_names():
        typer.echo(f"Unknown table: {table}")
        raise typer.Exit(1)
    cols = insp.get_columns(table)
    pk = set(insp.get_pk_constraint(table).get("constrained_columns", []) or [])
    header = f"{'name':20} {'type':20} {'nullable':8} {'pk':2} {'default'}"
    typer.echo(header)
    typer.echo("-" * len(header))
    for c in cols:
        name = c.get("name", "")
        typ  = str(c.get("type", ""))
        nul  = str(c.get("nullable", ""))
        dfl  = c.get("default", "")
        ispk = "Y" if name in pk else ""
        typer.echo(f"{name:20} {typ:20} {nul:8} {ispk:2} {dfl}")

@app.command(help="Print up to N rows from a table.")
def show(table: str, limit: int = typer.Option(10, "--limit")):
    create_all()
    eng = get_engine()
    md = MetaData()
    try:
        tbl = Table(table, md, autoload_with=eng)
    except Exception:
        typer.echo(f"Unknown table: {table}")
        raise typer.Exit(1)
    with eng.connect() as conn:
        res = conn.execute(select(tbl).limit(limit))
        rows = [dict(r._mapping) for r in res]
    if not rows:
        typer.echo("(no rows)")
        return
    cols = list(rows[0].keys())
    typer.echo("\t".join(cols))
    for r in rows:
        typer.echo("\t".join("" if r[c] is None else str(r[c]) for c in cols))

@app.command(help="Run a read-only SQL query (SELECT/CTE). Use --write to allow writes.")
def sql(query: str, write: bool = typer.Option(False, "--write")):
    q = (query or "").lstrip().lower()
    if not write and not (q.startswith("select") or q.startswith("with")):
        typer.echo("Refusing non-SELECT without --write")
        raise typer.Exit(1)
    create_all()
    eng = get_engine()
    with eng.connect() as conn:
        res = conn.execute(text(query))
        try:
            rows = res.mappings().all()
        except Exception:
            typer.echo("(ok)")
            return
    if not rows:
        typer.echo("(no rows)")
        return
    cols = list(rows[0].keys())
    typer.echo("\t".join(cols))
    for r in rows:
        typer.echo("\t".join("" if r[c] is None else str(r[c]) for c in cols))

@app.command(help="Revoke all active tokens (set revoked_at=now). Use --hard to DELETE rows instead.")
def clear_tokens(
    hard: bool = typer.Option(False, "--hard", help="Hard delete all rows instead of revoking"),
    vacuum: bool = typer.Option(False, "--vacuum", help="Run VACUUM after hard delete (SQLite only)")
):
    from svh.commands.db.models import AuthToken
    from svh.commands.db.db_template_utils import load_db_template

    create_all()
    with session_scope() as s:
        if hard:
            s.execute(sa_delete(AuthToken))
            typer.echo("Hard-deleted auth_tokens.")
        else:
            s.execute(
                sa_update(AuthToken)
                .where(AuthToken.revoked_at.is_(None))
                .values(revoked_at=datetime.utcnow())
            )
            typer.echo("Revoked all active tokens (kept history).")

    url = load_db_template().get("url", "sqlite:///./hive.sqlite")
    if hard and vacuum and url.startswith("sqlite:///"):
        eng = get_engine()
        with eng.begin() as conn:
            conn.exec_driver_sql("VACUUM")
        typer.echo("VACUUM complete.")


        # ---- convenience command for devs only -----REMOVE FOR PRODUCTION--------------

@app.command(help="Create or update a developer admin account (local CLI).")
def dev_admin(
    user: str = typer.Option("admin", "--user", help="Dev admin user_id"),
    password: str = typer.Option("admin", "--pass", help="Dev admin password"),
):
    from svh.commands.db.seed import upsert_user
    create_all()
    with session_scope() as s:
        out = upsert_user(s, user, password, is_admin=True)
    action = "Created" if out["created"] else "Updated"
    typer.echo(f"{action} dev admin: user_id={out['user_id']} password={out['password']} admin=True")

