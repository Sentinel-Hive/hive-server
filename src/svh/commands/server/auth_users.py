from __future__ import annotations
import json, os, pathlib, urllib.request, urllib.error, urllib.parse
import time
import typer
from svh import notify

app = typer.Typer(help="Server management and authenticated admin utilities.")


# ---------- Config ----------
def _base_url_opt():
    return typer.Option(
        "http://127.0.0.1:5167",
        "--base-url",
        envvar="SVH_API_BASE",
        help="Base URL of the Client API (should be http://127.0.0.1:5167). Requests are routed through the client API to the DB API as needed.",
    )


def _token_file() -> str:
    if os.name == "nt":
        root = os.environ.get("APPDATA") or os.path.expanduser("~")
        base = os.path.join(root, "svh")
    else:
        base = os.path.join(os.path.expanduser("~"), ".config", "svh")
    os.makedirs(base, exist_ok=True)
    return os.path.join(base, "token.json")


# ---------- Token store ----------
def _save_token(token: str, exp_epoch: int):
    pathlib.Path(_token_file()).write_text(
        json.dumps({"token": token, "exp": exp_epoch}), encoding="utf-8"
    )


def _load_token() -> tuple[str, int] | None:
    # prefer env override
    env_tok = os.environ.get("SVH_TOKEN")
    if env_tok:
        return (env_tok.strip(), int(time.time()) + 3600)
    p = _token_file()
    if not os.path.exists(p):
        return None
    try:
        j = json.loads(pathlib.Path(p).read_text(encoding="utf-8"))
        return (j.get("token"), int(j.get("exp") or 0)) if j.get("token") else None
    except Exception:
        return None


def _clear_token():
    try:
        os.remove(_token_file())
    except Exception:
        pass


def _is_expired(exp_epoch: int) -> bool:
    # consider a small safety margin
    return exp_epoch <= int(time.time())


# ---------- HTTP helpers ----------
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

        notify.error(f"[HTTP {e.code}] {msg}")
        raise typer.Exit(1)
    except urllib.error.URLError as e:
        notify.error(f"[ERROR] {e}")
        raise typer.Exit(1)


# ---------- Auth gate ----------
def _ensure_admin(base_url: str) -> str:
    """Return a valid token, or exit. Enforces login, expiry, and admin."""
    t = _load_token()
    if not t:
        notify.error("Not logged in. Run: svh server login")
        raise typer.Exit(1)
    token, exp = t
    if _is_expired(exp):
        _clear_token()
        notify.error("Session expired; please login again.")
        raise typer.Exit(1)
    # Check it's active and admin
    who = _req("GET", f"{base_url}/auth/whoami", token=token)
    if not who or not who.get("is_admin"):
        notify.error("Admin privileges required. Login with an admin account.")
        raise typer.Exit(1)
    return token


# ---------- Commands: login/logout ----------
@app.command(
    "login",
    help="Login to the Client API (port 5167) and store a token (required for admin commands).",
)
def login(
    user_id: str = typer.Option(..., "--u"),
    password: str = typer.Option(..., "--p"),
    ttl: int = typer.Option(3600, "--ttl", help="Session TTL (seconds)"),
    base_url: str = _base_url_opt(),
    replace: bool = typer.Option(
        False, "--replace", help="Auto-logout the existing session if present"
    ),
):
    existing = _load_token()
    if existing and not replace and not _is_expired(existing[1]):
        notify.error(
            "A session is already active. Run `svh server logout` or pass --replace."
        )
        raise typer.Exit(1)
    if existing and replace:
        try:
            _req(
                "POST",
                f"{base_url}/auth/logout",
                {"token": existing[0]},
                token=existing[0],
            )
        except Exception:
            pass
        _clear_token()

    out = _req(
        "POST",
        f"{base_url}/auth/login",
        {"user_id": user_id, "password": password, "ttl": ttl},
    )
    token = out.get("token")
    if not token:
        notify.error("No token returned.")
        raise typer.Exit(1)
    exp = int(time.time()) + int(ttl)
    _save_token(token, exp)
    typer.echo("Logged in.")
    typer.echo(f"Token expires in {ttl} seconds.")


@app.command("logout", help="Logout the current session.")
def logout(base_url: str = _base_url_opt()):
    t = _load_token()
    if not t:
        typer.echo("No saved session.")
        return
    token, _ = t
    try:
        _req("POST", f"{base_url}/auth/logout", {"token": token}, token=token)
    except Exception:
        pass
    _clear_token()
    typer.echo("Logged out.")


# ---------- Admin (proxied) users commands ----------
users = typer.Typer(help="Admin-only user utilities (proxied through the Client API, which routes to the DB API as needed).")
app.add_typer(users, name="users")


@users.command("create", help="Create a user and print credentials.")
def users_create(
    admin: bool = typer.Option(False, "--admin"),
    base_url: str = _base_url_opt(),
):
    token = _ensure_admin(base_url)
    q = "true" if admin else "false"
    out = _req("POST", f"{base_url}/users/create?admin={q}", token=token)
    typer.echo(json.dumps(out, indent=2))


@users.command("seed", help="Seed initial users (only if table empty).")
def users_seed(
    admins: int = typer.Option(1, "--admins"),
    users: int = typer.Option(5, "--users"),
    base_url: str = _base_url_opt(),
):
    token = _ensure_admin(base_url)
    out = _req(
        "POST", f"{base_url}/users/seed?admins={admins}&users={users}", token=token
    )
    typer.echo(json.dumps(out, indent=2))


@users.command(
    "insert", help='Insert a row into a table. Example: --values \'{"k":"v"}\''
)
def users_insert(
    table_name: str,
    values: str = typer.Option(..., "--values", help="JSON object of column values"),
    base_url: str = _base_url_opt(),
):
    token = _ensure_admin(base_url)
    try:
        body = {"values": json.loads(values)}
    except json.JSONDecodeError:
        notify.error("Invalid JSON for --values")
        raise typer.Exit(1)
    enc = urllib.parse.quote(table_name)
    out = _req("POST", f"{base_url}/users/insert/{enc}", body=body, token=token)
    typer.echo(json.dumps(out, indent=2))


# ---------- Local DB inspect helpers (admin required even though local) ----------
inspect = typer.Typer(help="Local DB inspection (admin login required, routed through Client API).")
app.add_typer(inspect, name="inspect")

from svh.commands.db.session import get_engine, create_all
from sqlalchemy import inspect as sa_inspect, MetaData, Table, select, func, text


@inspect.command("tables", help="List tables with row counts (local).")
def insp_tables(base_url: str = _base_url_opt()):
    _ensure_admin(base_url)  # gate by admin
    create_all()
    eng = get_engine()
    insp = sa_inspect(eng)
    names = sorted(insp.get_table_names())
    if not names:
        typer.echo("(no tables)")
        return
    for t in names:
        with eng.connect() as conn:
            cnt = conn.execute(
                select(func.count()).select_from(
                    Table(t, MetaData(), autoload_with=eng)
                )
            ).scalar_one()
        typer.echo(f"{t}\t{cnt}")


@inspect.command("schema", help="Show schema for a table (local).")
def insp_schema(table: str, base_url: str = _base_url_opt()):
    _ensure_admin(base_url)
    create_all()
    eng = get_engine()
    insp = sa_inspect(eng)
    if table not in insp.get_table_names():
        raise typer.Exit(f"Unknown table: {table}")
    cols = insp.get_columns(table)
    pk = set(insp.get_pk_constraint(table).get("constrained_columns", []) or [])
    header = f"{'name':20} {'type':20} {'nullable':8} {'pk':2} {'default'}"
    typer.echo(header)
    typer.echo("-" * len(header))
    for c in cols:
        name = c.get("name", "")
        typ = str(c.get("type", ""))
        nul = str(c.get("nullable", ""))
        dfl = c.get("default", "")
        ispk = "Y" if name in pk else ""
        typer.echo(f"{name:20} {typ:20} {nul:8} {ispk:2} {dfl}")


@inspect.command("show", help="Print rows from a table (local).")
def insp_show(
    table: str,
    limit: int = typer.Option(10, "--limit"),
    base_url: str = _base_url_opt(),
):
    _ensure_admin(base_url)
    create_all()
    eng = get_engine()
    md = MetaData()
    try:
        tbl = Table(table, md, autoload_with=eng)
    except Exception:
        notify.error(f"Unknown table: {table}")
        raise typer.Exit(1)
    with eng.connect() as conn:
        rows = [dict(r._mapping) for r in conn.execute(select(tbl).limit(limit))]
    if not rows:
        typer.echo("(no rows)")
        return
    cols = list(rows[0].keys())
    typer.echo("\t".join(cols))
    for r in rows:
        typer.echo("\t".join("" if r[c] is None else str(r[c]) for c in cols))


@inspect.command(
    "sql", help="Run a read-only SQL query (local). Use --write to allow writes."
)
def insp_sql(
    query: str,
    write: bool = typer.Option(False, "--write"),
    base_url: str = _base_url_opt(),
):
    _ensure_admin(base_url)
    q = (query or "").lstrip().lower()
    if not write and not (q.startswith("select") or q.startswith("with")):
        notify.error("Refusing non-SELECT without --write")
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
