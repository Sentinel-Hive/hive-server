# src/svh/commands/server/client_api/cli.py
from __future__ import annotations
import json
import os
import sys
import urllib.request
import urllib.error
import typer

app = typer.Typer(help="Call the Client API (auth, users, health) from the CLI.")

def _base_url_opt():
    return typer.Option("http://127.0.0.1:8000", "--base-url", envvar="SVH_API_BASE",
                        help="Base URL of the Client API.")

def _token_opt():
    return typer.Option(None, "--token", envvar="SVH_TOKEN",
                        help="Bearer token. If omitted, will try $SVH_TOKEN.")

# ---- helpers ---------------------------------------------------------------

def _req(method: str, url: str, body: dict | None = None, token: str | None = None):
    data = None if body is None else json.dumps(body).encode("utf-8")
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req) as r:
            raw = r.read().decode("utf-8")
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        msg = e.read().decode("utf-8")
        typer.echo(f"[HTTP {e.code}] {msg}", err=True)
        raise typer.Exit(1)
    except urllib.error.URLError as e:
        typer.echo(f"[ERROR] {e}", err=True)
        raise typer.Exit(1)

# ---- health ----------------------------------------------------------------

@app.command("health", help="Check server readiness.")
def health(base_url: str = _base_url_opt()):
    out = _req("GET", f"{base_url}/health/ready")
    typer.echo(json.dumps(out, indent=2))

# ---- auth ------------------------------------------------------------------

auth = typer.Typer(help="Authentication commands.")
app.add_typer(auth, name="auth")

@auth.command("login", help="Login and print a bearer token.")
def login(user_id: str, password: str, ttl: int = typer.Option(3600, "--ttl"),
          base_url: str = _base_url_opt()):
    out = _req("POST", f"{base_url}/auth/login",
               body={"user_id": user_id, "password": password, "ttl": ttl})
    token = out.get("token")
    if token:
        typer.echo(token)
        typer.echo("Tip: set it for this shell with:  set SVH_TOKEN=" + token if os.name=="nt"
                   else f'export SVH_TOKEN="{token}"', err=True)
    else:
        typer.echo("[ERROR] No token returned.", err=True); raise typer.Exit(1)

@auth.command("logout", help="Logout and revoke a token.")
def logout(token: str = _token_opt(), base_url: str = _base_url_opt()):
    if not token:
        typer.echo("Missing --token or $SVH_TOKEN", err=True); raise typer.Exit(1)
    out = _req("POST", f"{base_url}/auth/logout", body={"token": token})
    typer.echo(json.dumps(out, indent=2))

@auth.command("check", help="Check whether a token is active.")
def check(token: str = _token_opt(), base_url: str = _base_url_opt()):
    if not token:
        typer.echo("Missing --token or $SVH_TOKEN", err=True); raise typer.Exit(1)
    out = _req("GET", f"{base_url}/auth/check?token={urllib.parse.quote(token)}")
    typer.echo(json.dumps(out, indent=2))

# ---- users (admin only) ----------------------------------------------------

users = typer.Typer(help="Admin-only user utilities.")
app.add_typer(users, name="users")

@users.command("seed", help="Seed N admin and M user accounts (prints credentials).")
def seed(admins: int = 1, users: int = 5,
         token: str = _token_opt(), base_url: str = _base_url_opt()):
    if not token:
        typer.echo("Missing --token or $SVH_TOKEN", err=True); raise typer.Exit(1)
    out = _req("POST", f"{base_url}/users/seed?admins={admins}&users={users}",
               token=token)
    typer.echo(json.dumps(out, indent=2))

@users.command("create", help="Create a single account and print its credentials.")
def create(admin: bool = typer.Option(False, "--admin"),
           token: str = _token_opt(), base_url: str = _base_url_opt()):
    if not token:
        typer.echo("Missing --token or $SVH_TOKEN", err=True); raise typer.Exit(1)
    out = _req("POST", f"{base_url}/users/create?admin={'true' if admin else 'false'}",
               token=token)
    typer.echo(json.dumps(out, indent=2))

@users.command("insert", help="Insert a row into a table. Example: --values '{\"k\":\"v\"}'")
def insert(table_name: str,
           values: str = typer.Option(..., "--values", help="JSON object of column values."),
           token: str = _token_opt(), base_url: str = _base_url_opt()):
    if not token:
        typer.echo("Missing --token or $SVH_TOKEN", err=True); raise typer.Exit(1)
    try:
        body = {"values": json.loads(values)}
    except json.JSONDecodeError:
        typer.echo("Invalid JSON for --values", err=True); raise typer.Exit(1)
    out = _req("POST", f"{base_url}/users/insert/{table_name}", body=body, token=token)
    typer.echo(json.dumps(out, indent=2))
