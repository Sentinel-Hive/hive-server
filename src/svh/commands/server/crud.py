import subprocess
import os
import signal
from pathlib import Path
from svh import notify

PID_FILE = Path(".svh_server.pid")


def start_server(config: dict):
    host = config.get("server", {}).get("host")
    port = config.get("server", {}).get("port")

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
