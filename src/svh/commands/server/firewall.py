import platform
import subprocess
from svh import notify
from typing import Any, Dict, Iterable, Set, Tuple
import json
from typing import Optional
import shutil  # added to resolve ufw path

try:
    import yaml
except Exception:  
    yaml = None
    notify.error("PyYAML is required to load firewall configuration. Please install 'pyyaml'.")


def open_port(port: int, proto: str = "tcp"):
    os_name = platform.system().lower()

    if os_name == "linux":
        cmd = ["sudo", "ufw", "allow", f"{port}/{proto}"]
    elif os_name == "windows":
        cmd = [
            "powershell",
            f"New-NetFirewallRule -DisplayName 'AllowPort{port}' "
            f"-Direction Inbound -Protocol {proto.upper()} -LocalPort {port} -Action Allow",
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

def configure_firewall_from_config(config_path: str) -> Dict[str, Any]:
    """
    Configure the firewall to close all ports not present in config.yml,
    start SSH service, and ensure SSH port is allowed.

    Expected config format (examples):
      firewall:
        allowed_ports:
          - 80
          - "443/tcp"
          - { port: 53, proto: "udp" }
      ssh:
        port: 22
        username: "alice"
        password: "****"        # or
        key_path: "/path/to/key"

    Returns dict with parsed ssh configuration (without password value logging).
    """
    if yaml is None:
        raise RuntimeError("PyYAML not available; cannot load firewall config.")

    cfg = _load_yaml(config_path)
    firewall_cfg = (cfg or {}).get("firewall", {}) or {}
    ssh_cfg = (cfg or {}).get("ssh", {}) or {}

    allowed_ports = _parse_allowed_ports(firewall_cfg.get("allowed_ports", []))
    ssh_port = int(ssh_cfg.get("port", 22))
    # Always allow SSH port (tcp)
    allowed_ports.add((ssh_port, "tcp"))

    os_name = platform.system().lower()
    try:
        if os_name == "linux":
            _apply_linux_firewall(allowed_ports)
            _start_ssh_linux()
        elif os_name == "windows":
            _apply_windows_firewall(allowed_ports, ssh_port)
            _start_ssh_windows()
        elif os_name == "darwin":
            notify.error("This application is not supported on macOS.")
            exit(1)
        else:
            notify.error(f"Firewall handling not implemented for {os_name}")
            exit(1)
        notify.firewall(f"Firewall configured from {config_path}. SSH port {ssh_port} allowed.")
    except subprocess.CalledProcessError as e:
        notify.error(f"Failed to configure firewall/SSH. Error: {e}")

    return {
        "ssh": {
            "port": ssh_port,
            "username": ssh_cfg.get("username"),
            "password_set": bool(ssh_cfg.get("password")),
            "key_path": ssh_cfg.get("key_path"),
        }
    }

def firewall_ssh_status(config_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Report firewall and SSH status. If config_path is provided, verify that:
    - SSH port is allowed and listening
    - Allowed ports include those from config (plus SSH)
    Returns a dict with 'ok' flag and details, and logs concise notify messages.
    """
    expected_allowed: Set[Tuple[int, str]] = set()
    ssh_port = 22

    if config_path:
        cfg = _load_yaml(config_path)
        firewall_cfg = (cfg or {}).get("firewall", {}) or {}
        ssh_cfg = (cfg or {}).get("ssh", {}) or {}
        expected_allowed = _parse_allowed_ports(firewall_cfg.get("allowed_ports", []))
        ssh_port = int(ssh_cfg.get("port", 22))
    expected_allowed.add((ssh_port, "tcp"))

    os_name = platform.system().lower()
    if os_name == "linux":
        details = _linux_status(ssh_port)
    elif os_name == "windows":
        details = _windows_status(ssh_port)
    elif os_name == "darwin":
        notify.error("This application is not supported on macOS.")
        return {"ok": False, "os": os_name}

    allow_ok = True
    if config_path:
        current_allowed = set(details.get("allowed_ports", []))
        allow_ok = expected_allowed.issubset(current_allowed)

    ok = bool(details.get("firewall_enabled")) and bool(details.get("ssh_running")) and bool(details.get("ssh_port_listening")) and allow_ok

    notify.firewall(f"Status: firewall_enabled={details.get('firewall_enabled')}, defaults={details.get('defaults')}, ssh_running={details.get('ssh_running')}, ssh_port_listening={details.get('ssh_port_listening')}")
    if not allow_ok and config_path:
        notify.error("Allowed ports do not match expected allowlist from config.yml")
    else:
        notify.firewall("Allowed ports match expected config." if config_path else "Allowed ports listed.")

    return {
        "ok": ok,
        "os": os_name,
        "ssh_port": ssh_port,
        "allowed_ports_expected": sorted(list(expected_allowed)),
        "details": details,
    }

def _load_yaml(path: str) -> Dict[str, Any]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
            if not isinstance(data, dict):
                raise ValueError("YAML root must be a mapping.")
            return data
    except FileNotFoundError:
        notify.error(f"Config file not found: {path}")
        return {}
    except Exception as e:
        notify.error(f"Failed to parse YAML config {path}: {e}")
        return {}

def _parse_allowed_ports(items: Iterable[Any]) -> Set[Tuple[int, str]]:
    """
    Accepts items like:
      - 80
      - "443/tcp"
      - {"port": 53, "proto": "udp"}
    Defaults proto to tcp when missing.
    """
    result: Set[Tuple[int, str]] = set()
    for it in items or []:
        port: int
        proto: str = "tcp"
        if isinstance(it, int):
            port = it
        elif isinstance(it, str):
            if "/" in it:
                p, pr = it.split("/", 1)
                port = int(p.strip())
                proto = pr.strip().lower()
            else:
                port = int(it.strip())
        elif isinstance(it, dict):
            port = int(it.get("port"))
            proto = str(it.get("proto", "tcp")).lower()
        else:
            continue
        if port > 0:
            result.add((port, "udp" if proto == "udp" else "tcp"))
    return result

def _apply_linux_firewall(allowed: Set[Tuple[int, str]]) -> None:
    """
    Reset UFW and allow only the specified ports. This will remove all existing rules.
    """
    cmds = [
        ["sudo", "ufw", "--force", "reset"],
        ["sudo", "ufw", "default", "deny", "incoming"],
        ["sudo", "ufw", "default", "allow", "outgoing"],
    ]
    for port, proto in sorted(allowed):
        cmds.append(["sudo", "ufw", "allow", f"{port}/{proto}"])
    cmds.append(["sudo", "ufw", "--force", "enable"])

    for cmd in cmds:
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def _start_ssh_linux() -> None:
    """
    Enable and start SSH server (service name varies by distro).
    """
    candidates = [
        ["sudo", "systemctl", "enable", "--now", "sshd"],
        ["sudo", "systemctl", "enable", "--now", "ssh"],
        ["sudo", "service", "ssh", "start"],
    ]
    last_err = None
    for cmd in candidates:
        try:
            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return
        except subprocess.CalledProcessError as e:
            last_err = e
    if last_err:
        raise last_err

def _apply_windows_firewall(allowed: Set[Tuple[int, str]], ssh_port: int) -> None:
    """
    Configure Windows Defender Firewall:
      - Block inbound by default, allow outbound
      - Remove our previous AllowPort* rules
      - Add allows for specified ports (including SSH port)
    """
    rule_cmds = []
    rule_cmds.append("Set-NetFirewallProfile -Profile Domain,Public,Private -DefaultInboundAction Block -DefaultOutboundAction Allow")
    rule_cmds.append("Get-NetFirewallRule | Where-Object {$_.DisplayName -like 'AllowPort*'} | Remove-NetFirewallRule")

    for port, proto in sorted(allowed):
        rule_cmds.append(
            f"New-NetFirewallRule -DisplayName 'AllowPort{port}' -Direction Inbound -Protocol {proto.upper()} -LocalPort {port} -Action Allow"
        )

    ps_script = "; ".join(["$ErrorActionPreference = 'Stop'"] + rule_cmds)
    subprocess.run(["powershell", ps_script], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def _start_ssh_windows() -> None:
    """
    Ensure OpenSSH Server is enabled and running on Windows.
    """
    ps_script = "; ".join([
        "$ErrorActionPreference = 'Stop'",
        "Set-Service -Name sshd -StartupType Automatic",
        "Start-Service -Name sshd"
    ])
    subprocess.run(["powershell", ps_script], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def _linux_status(ssh_port: int) -> Dict[str, Any]:
    # Find ufw binary explicitly (non-root PATH often lacks /usr/sbin)
    ufw_path = shutil.which("ufw") or "/usr/sbin/ufw"
    try:
        # Use sudo to read ufw status
        proc = subprocess.run(["sudo", ufw_path, "status", "verbose"], capture_output=True, text=True, check=False)
        out = proc.stdout or ""
    except FileNotFoundError:
        notify.error("ufw not found on PATH. Ensure ufw is installed and available (e.g., /usr/sbin/ufw).")
        return {
            "firewall_enabled": False,
            "defaults": "unknown",
            "allowed_ports": [],
            "ssh_running": _linux_is_service_active("sshd") or _linux_is_service_active("ssh"),
            "ssh_port_listening": False,
        }

    enabled = "Status: active" in out
    defaults = "deny (incoming)" in out and "allow (outgoing)" in out

    allowed: Set[Tuple[int, str]] = set()
    for line in out.splitlines():
        line = line.strip()
        if not line or "/" not in line:
            continue
        parts = line.split()
        token = parts[0]
        if "/" in token:
            try:
                p, pr = token.split("/", 1)
                allowed.add((int(p), pr.lower()))
            except Exception:
                continue

    ssh_running = _linux_is_service_active("sshd") or _linux_is_service_active("ssh")
    if not ssh_running:
        ssh_running = subprocess.run(["pgrep", "-x", "sshd"], stdout=subprocess.DEVNULL).returncode == 0

    port_listening = False
    try:
        ss = subprocess.run(["ss", "-lnt"], capture_output=True, text=True)
        port_listening = f":{ssh_port} " in (ss.stdout or "")
    except Exception:
        ns = subprocess.run(["netstat", "-lnt"], capture_output=True, text=True)
        port_listening = f":{ssh_port} " in (ns.stdout or "")

    return {
        "firewall_enabled": enabled,
        "defaults": {"incoming": "deny", "outgoing": "allow"} if defaults else "unexpected",
        "allowed_ports": sorted(list(allowed)),
        "ssh_running": ssh_running,
        "ssh_port_listening": port_listening,
    }

def _linux_is_service_active(name: str) -> bool:
    try:
        p = subprocess.run(["systemctl", "is-active", name], capture_output=True, text=True)
        return (p.stdout or "").strip() == "active"
    except Exception:
        try:
            p = subprocess.run(["service", name, "status"], capture_output=True, text=True)
            return p.returncode == 0
        except Exception:
            return False

def _windows_status(ssh_port: int) -> Dict[str, Any]:
    try:
        ps_rules = [
            "Get-NetFirewallRule -DisplayName 'AllowPort*' | "
            "Get-NetFirewallPortFilter | "
            "Select-Object Protocol,LocalPort | ConvertTo-Json -Compress"
        ]
        r = subprocess.run(["powershell", "-Command", "; ".join(ps_rules)], capture_output=True, text=True)
        data = (r.stdout or "").strip()
        allowed: Set[Tuple[int, str]] = set()
        if data:
            jp = json.loads(data)
            items = jp if isinstance(jp, list) else [jp]
            for it in items:
                try:
                    port = int(it.get("LocalPort"))
                    proto = str(it.get("Protocol", "TCP")).lower()
                    allowed.add((port, "udp" if proto == "udp" else "tcp"))
                except Exception:
                    continue
        else:
            allowed = set()
    except Exception:
        allowed = set()

    prof = subprocess.run(
        ["powershell", "-Command", "(Get-NetFirewallProfile -Profile Domain,Public,Private).Enabled -contains 1"],
        capture_output=True, text=True
    )
    fw_enabled = "True" in (prof.stdout or "")

    svc = subprocess.run(["powershell", "-Command", "(Get-Service sshd).Status"], capture_output=True, text=True)
    ssh_running = "Running" in (svc.stdout or "")

    tnc = subprocess.run(
        ["powershell", "-Command", f"(Test-NetConnection -ComputerName localhost -Port {ssh_port}).TcpTestSucceeded"],
        capture_output=True, text=True
    )
    port_listening = "True" in (tnc.stdout or "")

    return {
        "firewall_enabled": fw_enabled,
        "defaults": "Block inbound / Allow outbound (Windows profiles)",
        "allowed_ports": sorted(list(allowed)),
        "ssh_running": ssh_running,
        "ssh_port_listening": port_listening,
    }
