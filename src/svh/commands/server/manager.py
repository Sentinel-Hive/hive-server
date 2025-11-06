import signal
import sys
import platform
import time
from typing import Dict
from svh import notify
from svh.commands.server import crud

SERVICES = ["client", "db"]


def _start_single_service(service: str, config: Dict, detach: bool) -> None:
    if service == "client":
        crud.start_client_server(config, detach=detach)
    elif service == "db":
        crud.start_db_server(config, detach=detach)


def _stop_single_service(service: str, config: Dict) -> None:
    try:
        if service == "client":
            crud.stop_client_server(config)
        elif service == "db":
            crud.stop_db_server(config)
    except Exception as e:
        notify.error(f"Failed to stop {service}: {e}")


def _handle_exit(selected_services: list, config: Dict) -> None:
    notify.server("Gracefully stopping running service(s)...")
    for s in reversed(selected_services):
        _stop_single_service(s, config)
    # restore original color when services are stopped
    try:
        notify.reset_accent_to_default()
    except Exception:
        pass
    sys.exit(0)


def manage_service(
    action: str, service: str, config: Dict, detach: bool = False
) -> None:
    selected = SERVICES if service == "all" else [service]

    if action == "start":
        for s in selected:
            _start_single_service(s, config, detach)

        if detach:
            notify.server(f"{', '.join(selected)} server(s) started in detached mode.")
            return

        notify.server(f"{', '.join(selected)} server(s) running. Press Ctrl+C to stop.")

        def handle_exit(sig, frame):
            _handle_exit(selected, config)

        signal.signal(signal.SIGINT, handle_exit)
        signal.signal(signal.SIGTERM, handle_exit)
        if platform.system().lower() == "windows":
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                _handle_exit(selected, config)
        else:
            signal.pause()

    elif action == "stop":
        for s in selected:
            _stop_single_service(s, config)
        # restore original color when explicit stop completes
        try:
            notify.reset_accent_to_default()
        except Exception:
            pass
    else:
        notify.error(f"Unsupported action: {action}")
