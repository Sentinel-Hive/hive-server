import os
import json
import typer
from sqlalchemy import inspect, MetaData, Table, select, func, text
from datetime import datetime
from sqlalchemy import update as sa_update, delete as sa_delete

from svh.commands.db.session import create_all, get_engine, session_scope
from svh.commands.db.config.template import (
    load_db_template,
    save_db_template,
    reset_db_template,
)

import pathlib
import time
import os
from sqlalchemy import select

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
    eng = get_engine()
    return bool(inspect(eng).get_table_names())


def _has_users() -> bool:
    """Return True if the users table contains at least one row.

    This is used to allow unauthenticated creation when the DB is present
    but has no users (e.g. was auto-created by svh server start).
    """
    # ensure tables exist so we can query
    create_all()
    try:
        from svh.commands.db.models import User
        from sqlalchemy import select, func
        with session_scope() as s:
            cnt = s.scalar(select(func.count()).select_from(User))
            return bool(cnt and int(cnt) > 0)
    except Exception:
        # if anything goes wrong, be conservative and say there are users
        return True


def _token_file() -> str:
    # match server CLI token storage location
    if os.name == "nt":
        root = os.environ.get("APPDATA") or os.path.expanduser("~")
        base = os.path.join(root, "svh")
    else:
        base = os.path.join(os.path.expanduser("~"), ".config", "svh")
    os.makedirs(base, exist_ok=True)
    return os.path.join(base, "token.json")


def _load_token() -> str | None:
    env_tok = os.environ.get("SVH_TOKEN")
    if env_tok:
        return env_tok.strip()
    p = _token_file()
    if not os.path.exists(p):
        return None
    try:
        j = json.loads(pathlib.Path(p).read_text(encoding="utf-8"))
        return j.get("token") if j.get("token") else None
    except Exception:
        return None


def _require_admin():
    """Exit if no valid admin token is present in SVH_TOKEN or token file."""
    tok = _load_token()
    if not tok:
        typer.echo("Admin privileges required. Set SVH_TOKEN or run 'svh db login' to obtain a token.")
        raise typer.Exit(1)
    # ensure DB exists and token corresponds to active, admin user
    create_all()
    from svh.commands.db.models import AuthToken
    from svh.commands.db.models import User

    with session_scope() as s:
        row = s.scalar(select(AuthToken).where(AuthToken.token == tok))
        if not row or getattr(row, "revoked_at", None) is not None:
            typer.echo("Token invalid or revoked. Obtain a new token via 'svh db login'.")
            raise typer.Exit(1)
        usr = getattr(row, "user", None)
        if not usr:
            # try to resolve via user_id
            uid = getattr(row, "user_id", None)
            if uid:
                usr = s.scalar(select(User).where(User.user_id == uid))
        if not usr or not getattr(usr, "is_admin", False):
            typer.echo("Admin privileges required. Token does not belong to an admin.")
            raise typer.Exit(1)


# ---- commands --------------------------------------------------------------

@app.command(help="Create a new database from the template (if not exists or --force).")
def create(
    force: bool = typer.Option(
        False, "--force", "-f", "--f", "-force", help="Force recreate the database if it exists."
    ),
    seed_admins: int | None = typer.Option(
        None, "--seed-admins", "-A", "--A", "-admins", help="Admins to create on first init."
    ),
    seed_users: int | None = typer.Option(
        None, "--seed-users", "-U", "--U", "-users", help="Users to create on first init."
    ),
    prompt: bool = typer.Option(
        True, "--prompt/--no-prompt", "-p", "--p", "-prompt", help="Ask for seed counts on first init if not provided."
    ),
):
    exists = _db_exists()
    # If there are existing users, require admin for any create/recreate operations.
    try:
        users_exist = _has_users()
    except Exception:
        users_exist = True

    if users_exist:
        _require_admin()

    # first_time if the DB didn't exist before or we're forcing recreate
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
            typer.echo("Non-SQLite URL detected; skipping physical deletion (will reuse connection).")

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
    _require_admin()
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
    _require_admin()
    reset_db_template()
    typer.echo("Database template reset to default settings.")


@app.command(help="Edit the database template using a JSON file.")
def edit_template(json_path: str):
    _require_admin()
    if not os.path.exists(json_path):
        typer.echo(f"File not found: {json_path}")
        raise typer.Exit(1)
    with open(json_path, "r", encoding="utf-8") as f:
        new_template = json.load(f)
    save_db_template(new_template)
    typer.echo("Database template updated from provided JSON file.")

@app.command(help="Show the SQLite file path if using sqlite:///; otherwise print the URL.")
def path():
    _require_admin()
    cfg = load_db_template()
    url = cfg.get("url", "sqlite:///./hive.sqlite")
    sqlite_path = _sqlite_path_from_url(url)
    if sqlite_path:
        typer.echo(sqlite_path)
    else:
        typer.echo(url)

@app.command(help="List tables and row counts.")
def tables():
    _require_admin()
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
    _require_admin()
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
def show(table: str, limit: int = typer.Option(10, "--limit", "-l", "--l", "-limit")):
    _require_admin()
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
def sql(query: str, write: bool = typer.Option(False, "--write", "-w", "--w", "-write")):
    _require_admin()
    q = (query or "").lstrip().lower()
    if not write and not (q.startswith("select") or q.startswith("with")):
        typer.echo("Refusing non-SELECT without --write")
        raise typer.Exit(1)
    create_all()
    eng = get_engine()
    # For write operations we must COMMIT; use a transaction context.
    if write:
        with eng.begin() as conn:
            res = conn.execute(text(query))
            # No explicit commit needed; eng.begin() auto-commits on success.
            try:
                rows = res.mappings().all()
                # If a write unexpectedly returns rows, print them.
            except Exception:
                # Best-effort report of affected rows if available
                try:
                    rc = getattr(res, "rowcount", None)
                    if rc is not None and rc >= 0:
                        typer.echo(f"(ok) rows={rc}")
                    else:
                        typer.echo("(ok)")
                except Exception:
                    typer.echo("(ok)")
                return
    else:
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
    hard: bool = typer.Option(False, "--hard", "-H", "--H", "-hard", help="Hard delete all rows instead of revoking"),
    vacuum: bool = typer.Option(False, "--vacuum", "-V", "--V", "-vacuum", help="Run VACUUM after hard delete (SQLite only)")
):
    from svh.commands.db.models import AuthToken
    from svh.commands.db.config.template import load_db_template

    _require_admin()
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
    user: str = typer.Option("admin", "--user", "-u", "--u", "-user", help="Dev admin user_id"),
    password: str = typer.Option("admin", "--pass", "-p", "--p", "-pass", help="Dev admin password"),
):
    from svh.commands.db.seed import upsert_user
    _require_admin()
    create_all()
    with session_scope() as s:
        out = upsert_user(s, user, password, is_admin=True)
    action = "Created" if out["created"] else "Updated"
    typer.echo(f"{action} dev admin: user_id={out['user_id']} password={out['password']} admin=True")

