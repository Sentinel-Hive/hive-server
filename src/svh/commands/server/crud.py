import subprocess
import os
import signal
from pathlib import Path
from svh import notify
from svh.commands.server.helper import invalid_config

PID_FILE = Path(".svh_server.pid")
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 5167


def start_server(config: dict):

    server_cfg = config.get("server", {})
    host = server_cfg.get("host")
    port = server_cfg.get("port")

    if not host:
        notify.error(f"No host specified in configuration: [host: {host}]")
        useDefault = invalid_config("host")
        if useDefault:
            notify.server(f"Defaulting to `{DEFAULT_HOST}`")
            host = DEFAULT_HOST
        else:
            notify.error("Cannot start server because no host was specified.")
            exit(1)
    if not port:
        notify.error(f"No port specified in configuration: [port: {port}]")
        useDefault = invalid_config("port")
        if useDefault:
            notify.server(f"Defaulting to `{DEFAULT_PORT}`")
            port = DEFAULT_PORT
        else:
            notify.error("Cannot start server because no port was specified.")
            exit(1)

    cmd = [
        "uvicorn",
        "svh.commands.server.api:app",
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
        PID_FILE.write_text(str(process.pid))
        notify.server(f"Server started on {host}:{port} (PID {process.pid})")

    except Exception as e:
        notify.error(f"Failed to start server: {e}")
        exit(1)


def stop_server():
    if not PID_FILE.exists():
        notify.error("No running server found.")
        exit(1)

    pid = int(PID_FILE.read_text())
    try:
        os.kill(pid, signal.SIGTERM)
    except ProcessLookupError:
        notify.error("No process found with PID {pid}.")
    finally:
        PID_FILE.unlink(missing_ok=True)

    notify.server(f"Stopped server with PID {pid}.")
