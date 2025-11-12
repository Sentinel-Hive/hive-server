import signal
import sys
import platform
import time
import asyncio
from typing import Dict
from svh import notify
from svh.commands.server import crud
from svh.commands.server.client_api.websocket.hub import websocket_hub

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


def _handle_exit_graceful(selected_services: list, config: Dict) -> None:
    """Gracefully stop services and close websocket connections."""
    notify.server("Recevied shudown signal - initiation graceful shutdown...")

    # If client service is running, disconnect websocket clients first
    if "client" in selected_services:
        try:
            notify.server("Disconnecting all active websocket clients...")

            # Create event loop
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            # Shudown websocket hub
            loop.run_until_complete(websocket_hub.shutdown())
            notify.server("All websocket clients disconnected.")
        except Exception as e:
            notify.error(f"Error during websocket shutdown: {e}")

    # Stop services
    notify.server("Stopping running service(s)...")
    for s in reversed(selected_services):
        _stop_single_service(s, config)

    notify.server("Shutdown complete.")
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
            _handle_exit_graceful(selected, config)

        
        signal.signal(signal.SIGINT, handle_exit)
        signal.signal(signal.SIGTERM, handle_exit)

        if platform.system().lower() == "windows":
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                _handle_exit_graceful(selected, config)
        else:
            signal.pause()

    elif action == "stop":
        for s in selected:
            
            _stop_single_service(s, config)
    else:
        notify.error(f"Unsupported action: {action}")
