import typer
from pathlib import Path
from svh.commands.server import crud
from svh.commands.server.manager import manage_service
from svh.commands.server.helper import load_config
from svh.commands.server.cli_auth import attach_auth_commands
from svh.commands.server.config import config, state
from svh.commands.server.firewall import firewall_ssh_status, configure_firewall_from_config

app = typer.Typer(help="Server management commands")

app.add_typer(config.config_app, name="config")

DEFAULT_CONFIG_PATH = Path(__file__).parent / "config/config.yml"

attach_auth_commands(app)

@app.command(help="Start one or more API servers.")
def start(
    service: str = typer.Option(
        "all", "--service", "-s", help="Service to start (client, db, or all)"
    ),
    config: Path = typer.Option(
        None, "--config", "-c", help="Path to configuration file", exists=True
    ),
    detach: bool = typer.Option(False, "--detach", "-d", help="Run in detached mode"),
    configure_firewall: bool = typer.Option(
        True, "--configure-firewall/--no-configure-firewall", help="Configure firewall from config"
    ),
):
    config_path = config or DEFAULT_CONFIG_PATH
    cfg = load_config(config_path)
    state.save_config_state(config_path)
    
    # Configure firewall (resets UFW and allows only ports from config + SSH)
    if configure_firewall:
        try:
            configure_firewall_from_config(str(config_path))
        except Exception as e:
            typer.secho(f"⚠ Failed to configure firewall: {e}", fg=typer.colors.YELLOW)
            typer.echo("Continuing with service start...\n")
    
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
        typer.secho(f"⚠ Config file not found: {config_path}", fg=typer.colors.YELLOW)
        typer.echo("Running status check without config validation...\n")
        result = firewall_ssh_status(None)
    else:
        result = firewall_ssh_status(str(config_path))
    
    typer.echo(f"OS: {result['os']}")
    typer.echo(f"SSH Port: {result['ssh_port']}")
    typer.echo(f"Firewall Enabled: {result['details'].get('firewall_enabled')}")
    typer.echo(f"SSH Running: {result['details'].get('ssh_running')}")
    typer.echo(f"SSH Port Listening: {result['details'].get('ssh_port_listening')}")
    typer.echo(f"Allowed Ports: {result['details'].get('allowed_ports')}")
    typer.echo(f"Defaults: {result['details'].get('defaults')}\n")
    
    if result["ok"]:
        typer.secho("✓ Server firewall and SSH are configured correctly", fg=typer.colors.GREEN)
    else:
        typer.secho("✗ Issues detected:", fg=typer.colors.RED)
        if not result['details'].get('firewall_enabled'):
            typer.echo("  • Firewall is not enabled. Run: sudo ufw enable")
        if not result['details'].get('ssh_running'):
            typer.echo("  • SSH service is not running")
        if not result['details'].get('ssh_port_listening'):
            typer.echo("  • SSH port is not listening")
        if config_path.exists():
            typer.echo(f"  • Run 'svh server start -c {config_path}' to configure firewall from config")
        raise typer.Exit(1)


