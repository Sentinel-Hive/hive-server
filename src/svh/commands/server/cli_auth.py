from __future__ import annotations
import typer
from svh.commands.server.auth_users import (
    login,
    logout,
    users_create,
    users_seed,
    users_insert,
    insp_tables,
    insp_schema,
    insp_show,
    insp_sql,
)


def attach_auth_commands(app: typer.Typer) -> None:
    app.command("login")(login)
    app.command("logout")(logout)

    users = typer.Typer(help="Admin-only user utilities")
    users.command("create")(users_create)
    users.command("seed")(users_seed)
    users.command("insert")(users_insert)
    app.add_typer(users, name="users")

    inspect = typer.Typer(help="Local DB inspection")
    inspect.command("tables")(insp_tables)
    inspect.command("schema")(insp_schema)
    inspect.command("show")(insp_show)
    inspect.command("sql")(insp_sql)
    app.add_typer(inspect, name="inspect")
