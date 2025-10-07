import typer
from .session import session_scope
from .seed import create_user, seed_users

app = typer.Typer(help="User utilities")

@app.command(help="Create one user with generated credentials")
def create(admin: bool = False):
    with session_scope() as s:
        uid_pwd_admin = create_user(s, admin)  # returns (user_id, password, is_admin) or dict per your export
        # If you kept the dict shape, adapt the print line accordingly.
        if isinstance(uid_pwd_admin, dict):
            u, p, a = uid_pwd_admin["user_id"], uid_pwd_admin["password"], uid_pwd_admin["is_admin"]
        else:
            u, p, a = uid_pwd_admin
        typer.echo(f"user_id={u} password={p} admin={a}")

@app.command(help="Seed initial users on an empty DB (no-op if users already exist)")
def seed(admins: int = 1, users: int = 5):
    created = seed_users(admins, users)
    if not created:
        typer.echo("Users already exist; no seeding performed.")
        return
    for c in created:
        typer.echo(f"user_id={c['user_id']} password={c['password']} admin={c['is_admin']}")
