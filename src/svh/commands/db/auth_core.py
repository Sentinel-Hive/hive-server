import typer
from sqlalchemy import select
from datetime import datetime
from .session import session_scope
from .models import User, AuthToken
from .security import verify_password
from .token import make_token, cache

app = typer.Typer(help="Auth utilities")

@app.command(help="Login and produce a token (CLI)")
def login(
    user_id: str = typer.Option(..., "--user", "-u", "--u", "-user"),
    password: str = typer.Option(..., "--pass", "-p", "--p", "-pass"),
    ttl: int = typer.Option(3600, "--ttl", "-t", "--t", "-ttl"),
):
    with session_scope() as s:
        user = s.scalar(select(User).where(User.user_id == user_id))
        if not user or not verify_password(password, user.salt_hex, user.pass_hash):
            typer.echo("Invalid credentials"); raise typer.Exit(1)
        token = make_token(user_id)
        s.add(AuthToken(user=user, token=token)); s.commit()
        cache.set(token, user_id, ttl)
        typer.echo(token)

@app.command(help="Logout token (revoke)")
def logout(token: str):
    with session_scope() as s:
        row = s.scalar(select(AuthToken).where(AuthToken.token == token))
        if row and not row.revoked_at:
            row.revoked_at = datetime.utcnow()
        cache.delete(token)
        typer.echo("OK")

@app.command(help="Check token validity (cache/db)")
def check(token: str):
    if cache.get(token):
        typer.echo("active (cache)"); return
    with session_scope() as s:
        from sqlalchemy import select
        row = s.scalar(select(AuthToken).where(AuthToken.token == token))
        typer.echo("active (db)" if row and not row.revoked_at else "revoked/not-found")
