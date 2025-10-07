from __future__ import annotations
import json, os, urllib.request, urllib.error, urllib.parse, pathlib
import typer

app = typer.Typer(help="Call the Client API (auth, users, health) from the CLI.")

def _base_url_opt():
    return typer.Option(
        "http://127.0.0.1:8000", "--base-url", envvar="SVH_API_BASE",
        help="Base URL of the Client API."
    )

# ---------------- token cache (per-user file) ----------------
def _token_path() -> str:
    if os.name == "nt":
        root = os.environ.get("APPDATA") or os.path.expanduser("~")
        base = os.path.join(root, "svh")
    else:
        base = os.path.join(os.path.expanduser("~"), ".config", "svh")
    os.makedirs(base, exist_ok=True)
    return os.path.join(base, "token")

def _save_token(token: str) -> None:
    p = _token_path()
    pathlib.Path(p).write_text(token, encoding="utf-8")

def _load_saved_token() -> str | None:
    # Prefer env var if present
    tok = os.environ.get("SVH_TOKEN")
    if tok:
        return tok.strip()
    p = _token_path()
    if os.path.exists(p):
        try:
            t = pathlib.Path(p).read_text(encoding="utf-8").strip()
            return t or None
        except Exception:
            return None
    return None

def _clear_saved_token() -> None:
    p = _token_path()
    try:
        if os.path.exists(p):
            os.remove(p)
    except Exception:
        pass

# ---------------- http helper ----------------
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

# ---------------- health ----------------
@app.command("health", help="Check server readiness.")
def health(base_url: str = _base_url_opt()):
    out = _req("GET", f"{base_url}/health/ready")
    typer.echo(json.dumps(out, indent=2))

# ---------------- auth ----------------
auth = typer.Typer(help="Authentication commands.")
app.add_typer(auth, name="auth")

class _LoginOpts(typer.Typer):
    ...

@auth.command("login", help="Login and store a bearer token locally. Refuses if a session is already saved.")
def login(
    user_id: str,
    password: str,
    ttl: int = typer.Option(3600, "--ttl"),
    base_url: str = _base_url_opt(),
    replace: bool = typer.Option(False, "--replace", help="Auto-logout the currently saved session before logging in.")
):
    existing = _load_saved_token()
    if existing and not replace:
        typer.echo(
            "A session is already active. Run `svh api auth logout` first "
            "or pass --replace to auto-logout and continue.",
            err=True,
        )
        raise typer.Exit(1)

    # If replacing, best-effort logout the saved token before proceeding
    if existing and replace:
        try:
            _req("POST", f"{base_url}/auth/logout", body={"token": existing})
        except Exception:
            # ignore network/logout errors here; we'll clear the saved token anyway
            pass
        _clear_saved_token()

    out = _req("POST", f"{base_url}/auth/login",
               body={"user_id": user_id, "password": password, "ttl": ttl})
    token = out.get("token")
    if not token:
        typer.echo("[ERROR] No token returned.", err=True); raise typer.Exit(1)
    _save_token(token)
    typer.echo(token)
    hint = f'set SVH_TOKEN={token}' if os.name == "nt" else f'export SVH_TOKEN="{token}"'
    typer.echo(f"Tip: {hint}", err=True)


@auth.command("logout", help="Logout using the saved token (or $SVH_TOKEN).")
def logout(base_url: str = _base_url_opt(), token: str = typer.Option(None, "--token")):
    tok = token or _load_saved_token()
    if not tok:
        typer.echo("No token found. Pass --token or set/login first.", err=True)
        raise typer.Exit(1)
    out = _req("POST", f"{base_url}/auth/logout", body={"token": tok})
    _clear_saved_token()
    typer.echo(json.dumps(out, indent=2))

@auth.command("check", help="Check whether the saved token is active.")
def check(base_url: str = _base_url_opt(), token: str = typer.Option(None, "--token")):
    tok = token or _load_saved_token()
    if not tok:
        typer.echo("No token found. Pass --token or set/login first.", err=True)
        raise typer.Exit(1)
    out = _req("GET", f"{base_url}/auth/check?token={urllib.parse.quote(tok)}")
    typer.echo(json.dumps(out, indent=2))

@auth.command("show-token", help="Print the currently saved token path and value.")
def show_token():
    p = _token_path()
    tok = _load_saved_token()
    typer.echo(f"path: {p}")
    typer.echo(f"token: {tok or '(none)'}")

# ---------------- users (admin-only) ----------------
users = typer.Typer(help="Admin-only user utilities.")
app.add_typer(users, name="users")

@users.command("seed", help="Seed N admin and M user accounts (prints credentials).")
def seed(admins: int = 1, users: int = 5,
         base_url: str = _base_url_opt(), token: str = typer.Option(None, "--token")):
    tok = token or _load_saved_token()
    if not tok:
        typer.echo("Missing token. Run: svh api auth login", err=True); raise typer.Exit(1)
    out = _req("POST", f"{base_url}/users/seed?admins={admins}&users={users}", token=tok)
    typer.echo(json.dumps(out, indent=2))

@users.command("create", help="Create a single account and print its credentials.")
def create(admin: bool = typer.Option(False, "--admin"),
           base_url: str = _base_url_opt(), token: str = typer.Option(None, "--token")):
    tok = token or _load_saved_token()
    if not tok:
        typer.echo("Missing token. Run: svh api auth login", err=True); raise typer.Exit(1)
    out = _req("POST", f"{base_url}/users/create?admin={'true' if admin else 'false'}", token=tok)
    typer.echo(json.dumps(out, indent=2))

@users.command("insert", help="Insert a row into a table. Example: --values '{\"k\":\"v\"}'")
def insert(table_name: str,
           values: str = typer.Option(..., "--values", help="JSON object of column values."),
           base_url: str = _base_url_opt(), token: str = typer.Option(None, "--token")):
    tok = token or _load_saved_token()
    if not tok:
        typer.echo("Missing token. Run: svh api auth login", err=True); raise typer.Exit(1)
    try:
        body = {"values": json.loads(values)}
    except json.JSONDecodeError:
        typer.echo("Invalid JSON for --values", err=True); raise typer.Exit(1)
    out = _req("POST", f"{base_url}/users/insert/{table_name}", body=body, token=tok)
    typer.echo(json.dumps(out, indent=2))
