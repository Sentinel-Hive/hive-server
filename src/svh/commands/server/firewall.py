import platform
import subprocess
from svh import notify


def open_port(port: int, proto: str = "tcp"):
    os_name = platform.system().lower()

    if os_name == "linux":
        cmd = ["sudo", "ufw", "allow", f"{port}/{proto}"]
    elif os_name == "windows":
        cmd = [
            "powershell",
            f"New-NetFirewallRule -DisplayName 'AllowPort{port}' -Direction Inbound -Protocol {proto.upper()} -LocalPort {port} -Action Allow",
        ]
    elif os_name == "darwin":
        notify.error("This application is not supported on macOS.")
        exit(1)
    else:
        notify.error(f"Firewall handling not implemented for {os_name}")
        exit(1)

    try:
        subprocess.run(
            cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True
        )
        notify.firewall(f"{port}:{proto.upper()} opened to allow traffic to service.")
    except subprocess.CalledProcessError as e:
        notify.error(f"Failed to open port {port}:{proto.upper()}. Error: {e}")


def close_port(port: int, proto: str = "tcp"):
    os_name = platform.system().lower()

    if os_name == "linux":
        cmd = ["sudo", "ufw", "delete", "allow", f"{port}/{proto}"]
    elif os_name == "windows":
        cmd = [
            "powershell",
            f"Get-NetFirewallRule | Where-Object {{$_.DisplayName -eq 'AllowPort{port}'}} | Remove-NetFirewallRule",
        ]
    elif os_name == "darwin":
        notify.error("This application is not supported on macOS.")
        exit(1)
    else:
        notify.error(f"Firewall handling not implemented for {os_name}")
        exit(1)

    try:
        subprocess.run(
            cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True
        )
        notify.firewall(f"{port}:{proto.upper()} closed.")
    except subprocess.CalledProcessError as e:
        notify.error(f"Failed to close port {port}:{proto.upper()}. Error: {e}")
