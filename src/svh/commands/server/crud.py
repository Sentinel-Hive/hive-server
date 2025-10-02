import subprocess
import os
import signal
from pathlib import Path
from svh import notify
from svh.commands.server.helper import invalid_config, isHost

PID_FILES = {
    "client": Path(".svh_user_api.pid"),
    "db": Path(".svh_db_api.pid"),
}
DEFAULT_HOST = "127.0.0.1"
DEFAULT_CLIENT_PORT = 5167
DEFAULT_DB_PORT = 5169


def _resolve_config(config: dict, service: str):
    server_cfg = config.get("server", {})
    host = server_cfg.get("host").strip().lstrip("\"'").rstrip("\"'")
    if not host:
        notify.error(f"No host specified in configuration: [host: {host}]")
        useDefault = invalid_config("host")
        if useDefault:
            notify.server(f"Defaulting to host:`{DEFAULT_HOST}`")
            host = DEFAULT_HOST
        else:
            notify.error("Cannot start server because no host was specified.")
            exit(1)

    if not isHost(host):
        notify.error(f"Host ({host}) is invalid. Please ensure you use a valid host.")
        host = DEFAULT_HOST
        notify.server(f"Defaulting to host:`{DEFAULT_HOST}`")

    if service == "client":
        port = server_cfg.get("client_port")
        if port == None:
            notify.error(
                f"No CLIENT port specified in configuration. [client_port: {port}]"
            )
            port = DEFAULT_CLIENT_PORT
            notify.server(f"Defaulting to client_port:`{port}`")
    else:
        port = server_cfg.get("db_port")
        if port == None:
            notify.error(f"No DB port specified in configuration. [db_port: {port}]")
            port = DEFAULT_DB_PORT
            notify.server(f"Defaulting to db_port:`{port}`")

    return host, port


def _start_service(config: dict, service: str, app_path: str):
    pid_file = PID_FILES[service]
    host, port = _resolve_config(config, service)

    if host == None or port == None:
        raise ValueError(
            f"Unexpected values found in `host: {host}, port: {port}` definitions."
        )

    cmd = [
        "uvicorn",
        app_path,
        "--host",
        host,
        "--port",
        str(port),
        "--reload",
        "--log-level",
        "critical",
    ]

    try:
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        pid_file.write_text(str(process.pid))
        notify.server(f"{service} API started on {host}:{port} (PID {process.pid})")
    except Exception as e:
        notify.error(f"Failed to start {service} API: {e}")
        exit(1)


def start_user_server(config: dict):
    _start_service(config, "client", "svh.commands.server.client_api.main:app")


def start_db_server(config: dict):
    _start_service(config, "db", "svh.commands.server.db_api.main:app")


def _stop_service(service: str):
    pid_file = PID_FILES[service]
    if not pid_file.exists():
        notify.error(f"No running {service} API found.")
        exit(1)

    pid = int(pid_file.read_text())
    try:
        os.kill(pid, signal.SIGTERM)
    except ProcessLookupError:
        notify.error(f"No process found with PID {pid}.")
    finally:
        pid_file.unlink(missing_ok=True)

    notify.server(f"Stopped {service} API with PID {pid}.")


def stop_client_server():
    _stop_service("client")


def stop_db_server():
    _stop_service("db")
