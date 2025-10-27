import typer
from pathlib import Path
from svh.commands.server import crud
from svh.commands.server.manager import manage_service
from svh.commands.server.helper import load_config
from svh.commands.server.cli_auth import attach_auth_commands
from svh.commands.server.config import config, state
from svh.commands.server.firewall import firewall_ssh_status, configure_firewall_from_config
from svh import notify  
from typing import Optional
import sys

app = typer.Typer(help="Server management commands")

app.add_typer(config.config_app, name="config")

DEFAULT_CONFIG_PATH = Path(__file__).parent / "config/config.yml"

attach_auth_commands(app)

@app.callback(invoke_without_command=True)
def main_callback(
    ctx: typer.Context,
    configure_firewall: bool = typer.Option(
        False, "-F", help="Configure firewall (shortcut for 'firewall' command)"
    ),
):
    """Server management commands."""
    if configure_firewall and ctx.invoked_subcommand is None:
        # Redirect to firewall command
        ctx.invoke(firewall_cmd, config=None)

@app.command(help="Start one or more API servers.")
def start(
    service: str = typer.Option(
        "all", "--service", "-s", help="Service to start (client, db, or all)"
    ),
    use_default_config: bool = typer.Option(
        False, "--use-default-config", "-c", help="Use the built-in default config.yml"
    ),
    config_file: Optional[Path] = typer.Option(
        None, "--config", "-C", help="Path to configuration file", exists=True
    ),
    detach: bool = typer.Option(False, "--detach", "-d", help="Run in detached mode"),
    configure_firewall: bool = typer.Option(
        False, "-F", help="Configure firewall from config"
    ),
):
    # Determine config path
    if use_default_config:
        config_path = DEFAULT_CONFIG_PATH
    elif config_file is not None:
        config_path = config_file
    else:
        config_path = DEFAULT_CONFIG_PATH

    cfg = load_config(config_path)
    state.save_config_state(config_path)
    
    # Configure firewall (resets UFW and allows only ports from config + SSH)
    if configure_firewall:
        try:
            configure_firewall_from_config(str(config_path))
        except Exception as e:
            notify.error(f"Failed to configure firewall: {e}")
            notify.firewall("Continuing with service start...")
    else:
        notify.firewall("Skipping firewall configuration (use -F to apply config).")
    
    manage_service("start", service, cfg, detach=detach)


@app.command(help="Stop one or more API servers.")
def stop(
    service: str = typer.Option(
        "all", "--service", "-s", help="Service to stop (client, db, or all)"
    ),
):
    cfg_path = state.load_config_state()
    manage_service("stop", service, cfg_path)


@app.command(help="List all API servers currently running.")
def list():
    crud.list_servers()


@app.command()
def status(
    config: Path = typer.Option(
        None, "--config", "-c", help="Path to config.yml", exists=False
    )
):
    """Check firewall and SSH configuration status."""
    config_path = config or DEFAULT_CONFIG_PATH

    if not config_path.exists():
        notify.error(f"Config file not found: {config_path}")
        notify.firewall("Running status check without config validation...")
        result = firewall_ssh_status(None)
    else:
        result = firewall_ssh_status(str(config_path))

    # concise summary routed through notify
    notify.firewall(f"OS: {result['os']}")
    notify.firewall(f"SSH Port: {result['ssh_port']}")
    notify.firewall(f"Firewall Enabled: {result['details'].get('firewall_enabled')}")
    notify.firewall(f"SSH Running: {result['details'].get('ssh_running')}")
    notify.firewall(f"SSH Port Listening: {result['details'].get('ssh_port_listening')}")
    notify.firewall(f"Allowed Ports: {result['details'].get('allowed_ports')}")
    notify.firewall(f"Defaults: {result['details'].get('defaults')}")

    if result["ok"]:
        notify.firewall("✓ Server firewall and SSH are configured correctly")
    else:
        notify.error("Issues detected with firewall or SSH configuration")
        if not result['details'].get('firewall_enabled'):
            notify.error("Firewall is not enabled. Run: sudo ufw enable")
        if not result['details'].get('ssh_running'):
            notify.error("SSH service is not running")
        if not result['details'].get('ssh_port_listening'):
            notify.error("SSH port is not listening")
        if config_path.exists():
            if config_path == DEFAULT_CONFIG_PATH:
                notify.firewall("Run 'svh server start -c -F -d' to configure firewall from default config")
            else:
                notify.firewall(f"Run 'svh server start -C {config_path} -F -d' to configure firewall from this config")
        raise typer.Exit(1)


@app.command(name="firewall")
def firewall_cmd(
    config: Path = typer.Option(
        None, "--config", "-c", help="Path to configuration file", exists=True
    ),
):
    """Configure firewall and SSH from config.yml (can be run while server is running)."""
    config_path = config or DEFAULT_CONFIG_PATH
    
    try:
        result = configure_firewall_from_config(str(config_path))
        notify.firewall(f"Firewall configured successfully. SSH port: {result['ssh']['port']}")
    except Exception as e:
        notify.error(f"Failed to configure firewall: {e}")
        raise typer.Exit(1)


