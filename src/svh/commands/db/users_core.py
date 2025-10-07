import typer
from sqlalchemy.orm import Session
from .session import session_scope
from .models import User
from .security import gen_userid, gen_password, hash_password

app = typer.Typer(help="User utilities")

@app.command(help="Create one user with generated credentials")
def create(admin: bool = False):
    with session_scope() as s:
        uid, pwd = _create_one(s, admin)
        typer.echo(f"user_id={uid} password={pwd} admin={admin}")

@app.command(help="Seed multiple users/admins")
def seed(admins: int = 1, users: int = 5):
    with session_scope() as s:
        for _ in range(admins):
            uid, pwd = _create_one(s, True)
            typer.echo(f"user_id={uid} password={pwd} admin=True")
        for _ in range(users):
            uid, pwd = _create_one(s, False)
            typer.echo(f"user_id={uid} password={pwd} admin=False")

def _create_one(s: Session, is_admin: bool):
    uid = gen_userid(); pwd = gen_password()
    salt_hex, pass_hash = hash_password(pwd)
    s.add(User(user_id=uid, is_admin=is_admin, salt_hex=salt_hex, pass_hash=pass_hash))
    return uid, pwd
