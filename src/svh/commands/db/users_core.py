import typer
from .session import session_scope
from .seed import create_user, seed_users
from .seed import upsert_user
from .security import gen_password
import os
import pathlib
import json


def _token_file() -> str:
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
    tok = _load_token()
    if not tok:
        typer.echo("Admin privileges required. Set SVH_TOKEN or run 'svh db login' to obtain a token.")
        raise typer.Exit(1)
    from .models import AuthToken, User
    from .session import create_all
    create_all()
    from sqlalchemy import select
    with session_scope() as s:
        row = s.scalar(select(AuthToken).where(AuthToken.token == tok))
        if not row or getattr(row, "revoked_at", None) is not None:
            typer.echo("Token invalid or revoked. Obtain a new token via 'svh db login'.")
            raise typer.Exit(1)
        usr = getattr(row, "user", None)
        if not usr:
            uid = getattr(row, "user_id", None)
            if uid:
                usr = s.scalar(select(User).where(User.user_id == uid))
        if not usr or not getattr(usr, "is_admin", False):
            typer.echo("Admin privileges required. Token does not belong to an admin.")
            raise typer.Exit(1)

app = typer.Typer(help="User utilities")

@app.command(help="Create one user with generated credentials")
def create(admin: bool = typer.Option(False, "--admin", "-a", "--a", "-admin")):
    _require_admin()
    with session_scope() as s:
        uid_pwd_admin = create_user(s, admin)  # returns (user_id, password, is_admin) or dict per your export
        # If you kept the dict shape, adapt the print line accordingly.
        if isinstance(uid_pwd_admin, dict):
            u, p, a = uid_pwd_admin["user_id"], uid_pwd_admin["password"], uid_pwd_admin["is_admin"]
        else:
            u, p, a = uid_pwd_admin
        typer.echo(f"user_id={u} password={p} admin={a}")

@app.command(help="Seed initial users on an empty DB (no-op if users already exist)")
def seed(
    admins: int = typer.Option(1, "--admins", "-A", "--A", "-admins"),
    users: int = typer.Option(5, "--users", "-U", "--U", "-users"),
):
    _require_admin()
    created = seed_users(admins, users)
    if not created:
        typer.echo("Users already exist; no seeding performed.")
        return
    for c in created:
        typer.echo(f"user_id={c['user_id']} password={c['password']} admin={c['is_admin']}")


@app.command(help="Reset (or create) a user's password and print the new cleartext password")
def reset(user_id: str, admin: bool = typer.Option(False, "--admin", "-a", "--a", "-admin")):
    _require_admin()
    pwd = gen_password()
    with session_scope() as s:
        out = upsert_user(s, user_id, pwd, admin)
    typer.echo(f"user_id={out['user_id']} password={out['password']} admin={out['is_admin']}")
