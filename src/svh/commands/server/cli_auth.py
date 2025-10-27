from __future__ import annotations
import typer
from svh.commands.server.auth_users import (
    login,
    logout,
    users_create,
    users_seed,
    users_insert,
    insp_show,
    users_reset,
)


def attach_auth_commands(app: typer.Typer) -> None:
    app.command("login")(login)
    app.command("logout")(logout)

    # Server-side allowed DB operations (proxied via Client API):
    # - insert rows into a table
    users = typer.Typer(help="Admin-only insert utilities (proxied through the Client API).")
    users.command("create")(users_create)
    users.command("seed")(users_seed)
    users.command("insert")(users_insert)
    users.command("reset")(users_reset)
    app.add_typer(users, name="users")

    # Limited inspect: only `show` is exposed on the server CLI (admin required).
    inspect = typer.Typer(help="Local DB inspection (admin login required, limited to 'show').")
    inspect.command("show")(insp_show)
    app.add_typer(inspect, name="inspect")
