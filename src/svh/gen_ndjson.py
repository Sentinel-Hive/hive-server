#!/usr/bin/env python3
"""
Usage examples:
    # default: produce 100 random records to stdout
    python gen_ndjson.py

    # generate 200 records for only the Firewall and Web App combined
    python gen_ndjson.py 200 --apps Firewall,Web App > sample.ndjson

    # generate 50 records per-app and write separate files (Firewall -> firewall.ndjson)
    python gen_ndjson.py 50 --apps Firewall,Web App --mode separate --out-dir ./datasets

Options:
    --apps APP1,APP2  Limit generation to records for matching app names (case-insensitive substring).
    --mode combined|separate  If 'combined' (default), produce all matching records in one stream/file.
                              If 'separate', create one ndjson file per selected app (COUNT each).
    --out FILE        When used with --mode combined, write output to FILE instead of stdout.
    --out-dir DIR     When used with --mode separate, place per-app files into DIR (defaults to cwd).
    --seed N          Same as before: set RNG seed for reproducible output.
"""

import argparse
import json
import os
from pathlib import Path
import random
import sys
from datetime import datetime, timedelta, timezone
import uuid
import os
import secrets, string


_sysrand = secrets.SystemRandom()

def _load_words() -> list[str]:
    p = Path(__file__).resolve().parent / "commands" / "db" / "config" / "wordlist.txt"
    if not p.exists():
        raise FileNotFoundError(f"Required wordlist not found at {p}")
    words = [w.strip().lower() for w in p.read_text(encoding="utf-8").splitlines()
             if w.strip() and not w.startswith("#")]
    # basic hygiene: only simple ascii words
    return [w for w in words if w.isascii() and w.replace("-", "").isalpha()]

_WORDS = None
def _words() -> list[str]:
    global _WORDS
    if _WORDS is None:
        _WORDS = _load_words()
    return _WORDS


def _mem_username(words:int=2, sep:str="-", digits:int=2) -> str:
    pool = _words()
    parts = [_sysrand.choice(pool) for _ in range(max(1, words))]
    suffix = "".join(_sysrand.choice(string.digits) for _ in range(max(0, digits)))
    return sep.join(parts) + (suffix if suffix else "")

def gen_userid() -> str:
    """
    Generate a human-friendly user_id.
    Config (env):
      SVH_USER_WORDS   (default 2)
      SVH_USER_SEP     (default '-')
      SVH_USER_DIGITS  (default 2)
      SVH_CRED_STYLE   ('memorable' or 'random'; default 'memorable')
    """
    style = os.getenv("SVH_CRED_STYLE", "memorable").lower()
    if style == "random":
        # non-memorable-- 10 random URL-safe chars
        return secrets.token_urlsafe(8).rstrip("=")
    return _mem_username(
        words=int(os.getenv("SVH_USER_WORDS", "2")),
        sep=os.getenv("SVH_USER_SEP", "-"),
        digits=int(os.getenv("SVH_USER_DIGITS", "2")),
    )


def parse_args():
    p = argparse.ArgumentParser(description="Generate NDJSON synthetic event records by app type")
    p.add_argument("count", nargs="?", type=int, default=100,
                   help="Number of records (per-app when --mode separate). Default: 100")
    p.add_argument("--seed", type=int, default=None, help="Optional RNG seed for reproducible output")
    p.add_argument("--apps", type=str, default=None,
                   help="Comma-separated list of app names or substrings to include (case-insensitive)."
                        " If omitted, all apps are allowed.")
    p.add_argument("--mode", choices=("combined", "separate"), default="combined",
                   help="combined: one stream with records from any selected app (default)."
                        " separate: create one file per selected app (COUNT records each).")
    datasets_dir = str(Path(__file__).resolve().parent.parent.parent / "datasets")
    p.add_argument("--out", type=str, default=None,
                   help="Output file when --mode combined. If omitted and output is not redirected, writes to datasets/output.ndjson")
    p.add_argument("--out-dir", type=str, 
                   default=datasets_dir,
                   help="Directory to write files when --mode separate. Always uses project's datasets/ folder.")
    args = p.parse_args()
    return args


args = parse_args()

COUNT = args.count
SEED = args.seed

random.seed(SEED)

# Pre-generate a pool of users for reuse (about 20% of record count but at least 5)
USER_POOL = [gen_userid() + "@sentinelhive.com" for _ in range(max(5, COUNT // 5))]
REUSE_USER_CHANCE = 0.7  # 70% chance to reuse an existing user

APPS = [
    "SSH-Daemon",
    "HTTP-App",
    "SFTP-Service",
    "DB-Proxy",
    "FTP-Service",
    "DNS-Server",
    "Mail-Server",
    "NTP-Server",
    "Firewall",
    "IDS",
    "Server-Events",
    "System-Logs",
    "Alerts",
]
# Map app (lowercase name substring) -> list of EVENT_TYPES proto keys to prefer
APP_EVENT_MAP = {
    "ssh": ["ssh", "auth", "user"],  # SSH focused on auth and user activities
    "ssh daemon": ["ssh", "auth", "user", "privilege"],  # SSH with privilege escalation possibilities
    "http": ["http", "auth", "access", "db"],  # HTTP with auth and access patterns
    "http web app": ["http", "auth", "db", "api"],  # Web app specific patterns
    "web": ["http", "auth", "api"],  # Generic web patterns
    "sftp": ["sftp", "file", "auth", "transfer"],  # File transfer focus
    "ftp": ["ftp", "file", "auth", "transfer"],  # File transfer focus
    "db": ["db", "tcp", "auth", "query"],  # Database specific activities
    "db proxy": ["db", "tcp", "auth", "query"],  # Database proxy patterns
    "dns": ["udp", "dns_query", "system"],  # DNS specific activities
    "mail": ["smtp", "mail", "auth", "phishing"],  # Mail with security focus
    "ntp": ["udp", "system", "config"],  # NTP with system time focus
    "firewall": ["tcp", "udp", "alert", "ddos", "access", "scan"],  # Network security
    "ids": ["alert", "malware", "ddos", "scan", "mitm", "phishing"],  # Security detection
    "server events": ["system", "config", "process", "file", "auth", "service"],  # Server operations
    "system logs": ["system", "config", "process", "file", "auth", "service"],  # System operations
    "alerts": ["alert", "security", "notice", "system", "auth"],  # General alerting
}
EVENT_TYPES = [
    # SSH
    ["ssh","login"], ["ssh","exec"], ["ssh","bruteforce"], ["ssh","password_change"],
    # HTTP / Web
    ["http","get"], ["http","post"], ["http","put"], ["http","delete"], ["http","sql_injection"],
    ["http","xss_attempt"], ["http","csrf_attempt"], ["http","directory_traversal"],
    # TCP/Network
    ["tcp","connect"], ["tcp","scan"], ["tcp","syn_scan"], ["tcp","xmas_scan"],
    ["udp","dns_query"], ["icmp","ping"], ["icmp","large_ping"],
    ["smb","access"], ["smb","brute_force"],
    # File and process
    ["file","read"], ["file","write"], ["file","delete"], ["process","start"], ["process","stop"],
    # SFTP/FTP
    ["sftp","transfer"], ["ftp","file_transfer"], ["ftp","bruteforce"],
    # RDP and other remote
    ["rdp","login"], ["snmp","trap"],
    # ARP, MITM, DDOS
    ["arp","spoof"], ["mitm","detected"], ["ddos","syn_flood"], ["ddos","amplification"],
    # Malware / phishing
    ["malware","download"], ["malware","execution"], ["ransomware","encrypt"],
    ["phishing","email_open"], ["phishing","click"],
    # SMTP / Mail
    ["smtp","send"], ["smtp","receive"],
    # Database
    ["db","query"], ["db","slow_query"], ["db","unauthorized_access"],
    # Auth / user lifecycle
    ["auth","login_success"], ["auth","login_failed"], ["auth","logout"], ["auth","token_revoke"],
    ["auth","password_reset"], ["auth","password_change"], ["auth","mfa_challenge"], ["auth","mfa_fail"],
    ["user","create"], ["user","delete"], ["user","modify"], ["user","role_change"],
    ["privilege","escalation"], ["lateral","movement"],
    # Config and system
    ["config","change"], ["config","apply"], ["system","reboot"], ["system","service_start"],
    ["system","service_stop"], ["system","maintenance"], ["system","resource_alert"], ["system","auth_fail"],
    # Alerts
    ["alert","notice"], ["alert","security"], ["alert","performance"], ["alert","availability"],
    # Supply chain / other
    ["supply_chain","compromise"], ["api","rate_limit"], ["access","denied"]
]
CONDITIONAL = ["success","failure","info","warning"]
RISK = ["low", "medium", "high", "critical", ""]
ATTACK_REASONS = [
    "Invalid credentials", "connection timeout", "blocked by policy", "rate limit",
    "2FA required", "permission denied", "checksum mismatch", "multiple failed attempts",
    "detected signatures of SQLi", "large number of SYN", "ARP cache poisoning detected",
    "suspicious user-agent", "suspicious payload", "port closed", "timeout",
    "credential stuffing detected", "password spraying", "malicious file download",
    "suspicious command execution", "privilege escalation attempt", "unusual lateral movement",
    "known C2 beaconing", "suspicious registry change", "unauthorized schema change"
]
HOST_PREFIXES = ["app","host","web","db","vpn","fw","scanner","lb","ids","mail"]
PORTS = [22, 80, 443, 21, 3389, 3306, 5432, 53, 123, 8080, 8443, 2022, 5060]

def rand_ip(publicish=True):
    if random.random() < 0.6:
        return f"10.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(1,254)}"
    else:
        return f"{random.randint(1,223)}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(1,254)}"

def iso_now_minus():
    # choose a random time from now back up to 365 days (1 year)
    dt = datetime.now(timezone.utc) - timedelta(minutes=random.randint(0, 60*24*365))
    return dt.replace(microsecond=0).isoformat()

def make_inner(idn, app, user, src_ip, dest, etype, src_port, dest_port, reason=None, resource_name=None, extras=None):
    """Construct inner event dict. extras can include app-specific fields (e.g., firewall action, IDS alert)."""
    display_name = app
    if isinstance(etype, list):
        event_desc = etype[1] if len(etype) > 1 else etype[0]
    else:
        event_desc = etype.split(",")[1] if "," in etype else etype
        
    if extras and "message" in extras:
        if "login" in extras["message"].lower():
            display_name = f"{app} - Authentication"
        elif "health check" in extras["message"].lower():
            display_name = f"{app} - Health Monitor"
        elif "maintenance" in extras["message"].lower():
            display_name = f"{app} - Maintenance"
        elif "crash" in extras["message"].lower():
            display_name = f"{app} - Crash Report"
        elif "usage" in extras["message"].lower():
            display_name = f"{app} - Resource Monitor"
        elif "scan" in extras["message"].lower():
            display_name = f"{app} - Security Scan"
    elif extras:
        if "sshEvent" in extras:
            display_name = f"{app} - {extras['sshEvent'].replace('_', ' ').title()}"
        elif "httpMethod" in extras:
            display_name = f"{app} - {extras['httpMethod']} Request"
        elif "dbEvent" in extras:
            display_name = f"{app} - {extras['dbEvent'].replace('_', ' ').title()}"
        elif "firewallAction" in extras:
            display_name = f"{app} - {extras['firewallAction'].title()} Traffic"
        elif "alertCategory" in extras:
            display_name = f"{app} - {extras['alertCategory'].replace('-', ' ').title()}"
        elif "dnsDirection" in extras:
            display_name = f"{app} - DNS {extras['dnsDirection'].title()}"
    
    # If no specific context was added, use the event type
    if display_name == app:
        display_name = f"{app} - {event_desc.replace('_', ' ').title()}"

    inner = {
        "id": idn,
        "createdDateTime": iso_now_minus(),
        "appDisplayName": display_name,
        "userPrincipalName": user,
        "ipAddress": src_ip,
        "dest": dest,
        "eventtype": etype,
        "src_port": src_port,
        "dest_port": dest_port,
    }
    if resource_name:
        inner["resourceDisplayName"] = resource_name
    if reason:
        inner["status"] = {"failureReason": reason}
    if extras and isinstance(extras, dict):
        # merge extras into inner (app-specific fields)
        for k, v in extras.items():
            inner[k] = v
    return inner

def make_record(i):
    return make_record_for_app(i, None)


def make_record_for_app(i, app_override=None):
    app = app_override if app_override is not None else random.choice(APPS)
    
    # 70% chance to reuse an existing user, 30% chance for a new one
    if USER_POOL and random.random() < REUSE_USER_CHANCE:
        user = random.choice(USER_POOL)
    else:
        user = gen_userid() + "@sentinelhive.com"
        # Maybe add new user to pool (50% chance if pool isn't too big)
        if len(USER_POOL) < max(10, COUNT // 3) and random.random() < 0.5:
            USER_POOL.append(user)
            
    src_ip = rand_ip()
    dest = rand_ip()

    # Prefer event types appropriate for the app when possible
    def choose_event_for_app(a):
        a_low = a.lower()
        candidates = []
        # 1) Try explicit mapping: find any map key that appears in the app name
        mapped_protos = []
        for mk, protos in APP_EVENT_MAP.items():
            if mk in a_low:
                mapped_protos.extend(protos)
        # remove duplicates while preserving order
        seen = set()
        mapped_protos = [p for p in mapped_protos if not (p in seen or seen.add(p))]

        if mapped_protos:
            for proto in mapped_protos:
                for et in EVENT_TYPES:
                    et_proto = et[0] if isinstance(et, list) else (et.split(",")[0] if isinstance(et, str) else "")
                    if et_proto == proto:
                        candidates.append(et)

        if not candidates:
            for et in EVENT_TYPES:
                proto = et[0] if isinstance(et, list) else (et.split(",")[0] if isinstance(et, str) else "")
                if "ssh" in a_low and proto == "ssh":
                    candidates.append(et)
                elif ("http" in a_low or "web" in a_low) and proto == "http":
                    candidates.append(et)
                elif ("sftp" in a_low) and proto == "sftp":
                    candidates.append(et)
                elif ("ftp" in a_low) and proto == "ftp":
                    candidates.append(et)
                elif ("dns" in a_low) and (proto == "udp" or proto == "dns_query"):
                    candidates.append(et)
                elif ("mail" in a_low or "smtp" in a_low) and proto == "smtp":
                    candidates.append(et)
                elif ("ntp" in a_low) and proto == "udp":
                    candidates.append(et)
                elif ("db" in a_low) and proto in ("tcp","http","mysql","db"):
                    candidates.append(et)
                elif ("system" in a_low or "server" in a_low) and proto == "system":
                    candidates.append(et)
                elif ("alerts" in a_low or a_low == "alerts") and proto == "alert":
                    candidates.append(et)

        if not candidates:
            return random.choice(EVENT_TYPES)

        return random.choice(candidates)

    et = choose_event_for_app(app)
    eventtype_out = et if random.random() < 0.85 else ",".join(et)
    cond = random.choice(CONDITIONAL)
    risk = random.choices(RISK, weights=[40,30,15,8,7])[0]
    host = f"{random.choice(HOST_PREFIXES)}-{random.randint(1,50)}"
    idn = f"evt-{str(i).zfill(4)}"

    # Determine ports and app-specific extras
    extras = {}

    if app.lower().startswith("ssh"):
        dest_port = 22
        src_port = random.randint(1024, 65535)
        ssh_scenario = random.random()
        if ssh_scenario < 0.3:  # 30% login attempts
            extras["sshEvent"] = "login_attempt"
            if random.random() < 0.8:  # 80% success rate
                extras["message"] = f"Successful login from {src_ip}"
                et = ["ssh", "login"]
            else:
                extras["message"] = f"Failed login attempt from {src_ip}"
                et = ["ssh", "bruteforce"] if random.random() < 0.4 else ["auth", "login_failed"]
        elif ssh_scenario < 0.5:  # 20% command execution
            extras["sshEvent"] = "command"
            extras["message"] = "Remote command execution"
            et = ["ssh", "exec"]
        elif ssh_scenario < 0.7:  # 20% file operations
            extras["sshEvent"] = "file_operation"
            op = random.choice(["read", "write", "delete"])
            extras["message"] = f"SSH file {op} operation"
            et = ["file", op]
        elif ssh_scenario < 0.85:  # 15% privileged operations
            extras["sshEvent"] = "privilege_escalation"
            extras["message"] = "Privilege escalation attempt"
            if random.random() < 0.7:
                extras["status"] = {"failureReason": "Permission denied"}
            et = ["privilege", "escalation"]
        else:  # 15% session management
            extras["sshEvent"] = "session"
            extras["message"] = random.choice([
                "Session terminated",
                "Session timeout",
                "Connection closed",
                "New session established"
            ])
            et = ["ssh", "session"]
        eventtype_out = et if random.random() < 0.85 else ",".join(et)
    elif "http" in app.lower() or "web" in app.lower():
        dest_port = random.choice([80, 8080, 8443, 443])
        src_port = random.randint(1024, 65535)
        web_scenario = random.random()
        if web_scenario < 0.5:  # 50% normal requests
            method = random.choice(["GET", "POST", "PUT", "DELETE"])
            path = random.choice([
                "/api/v1/users",
                "/api/v1/data",
                "/api/v1/auth",
                "/dashboard",
                "/login",
                "/static/assets",
                "/health"
            ])
            extras["httpMethod"] = method
            extras["path"] = path
            extras["message"] = f"{method} {path}"
            status = random.choices([200, 201, 400, 401, 403, 404, 500], 
                                 weights=[70, 10, 5, 5, 5, 3, 2])[0]
            extras["statusCode"] = status
            if status >= 400:
                et = ["http", "error"]
            else:
                et = ["http", method.lower()]
        elif web_scenario < 0.7:  # 20% auth related
            auth_type = random.choice(["Basic", "Bearer", "JWT"])
            extras["authType"] = auth_type
            if random.random() < 0.7:
                extras["message"] = "Successful authentication"
                extras["statusCode"] = 200
                et = ["auth", "login_success"]
            else:
                extras["message"] = "Authentication failed"
                extras["statusCode"] = 401
                et = ["auth", "login_failed"]
        elif web_scenario < 0.85:  # 15% potential attacks
            attack_type = random.random()
            if attack_type < 0.4:
                extras["message"] = "SQL injection attempt detected"
                extras["path"] = "/api/v1/users?id=1' OR '1'='1"
                et = ["http", "sql_injection"]
            elif attack_type < 0.7:
                extras["message"] = "XSS attempt detected"
                extras["path"] = "/comment?text=<script>alert(1)</script>"
                et = ["http", "xss_attempt"]
            elif attack_type < 0.9:
                extras["message"] = "CSRF attempt detected"
                et = ["http", "csrf_attempt"]
            else:
                extras["message"] = "Directory traversal attempt"
                extras["path"] = "../../etc/passwd"
                et = ["http", "directory_traversal"]
            extras["statusCode"] = 403
        else:  # 15% performance/errors
            perf_scenario = random.random()
            if perf_scenario < 0.6:
                extras["message"] = "Slow request detected"
                extras["responseTime"] = random.randint(5000, 15000)
                et = ["http", "performance"]
            else:
                extras["message"] = "Internal server error"
                extras["statusCode"] = 500
                et = ["http", "error"]
        eventtype_out = et if random.random() < 0.85 else ",".join(et)
    elif "sftp" in app.lower():
        dest_port = random.choice([21, 2022])
        src_port = random.randint(1024, 65535)
    elif "db proxy" in app.lower() or "db proxy" in app.lower() or "db" in app.lower():
        dest_port = random.choice([3306, 5432, 1433, 27017])  # MySQL, PostgreSQL, MSSQL, MongoDB
        src_port = random.randint(1024, 65535)
        db_scenario = random.random()
        if db_scenario < 0.4:  # 40% normal queries
            extras["dbEvent"] = "query"
            query_type = random.choice(["SELECT", "INSERT", "UPDATE", "DELETE"])
            table = random.choice(["users", "data", "logs", "events", "config"])
            extras["message"] = f"{query_type} operation on {table}"
            extras["queryType"] = query_type
            extras["table"] = table
            if random.random() < 0.1:  # 10% chance of slow query
                extras["queryTime"] = random.randint(1000, 5000)
                et = ["db", "slow_query"]
            else:
                extras["queryTime"] = random.randint(1, 999)
                et = ["db", "query"]
        elif db_scenario < 0.6:  # 20% auth/access
            extras["dbEvent"] = "auth"
            if random.random() < 0.7:
                extras["message"] = "Database authentication successful"
                et = ["db", "auth_success"]
            else:
                extras["message"] = "Database authentication failed"
                extras["status"] = {"failureReason": "Invalid credentials"}
                et = ["db", "auth_fail"]
        elif db_scenario < 0.8:  # 20% schema/admin
            extras["dbEvent"] = "admin"
            admin_op = random.choice([
                "Schema modification",
                "Index creation",
                "User permission change",
                "Configuration update"
            ])
            extras["message"] = admin_op
            et = ["db", "admin"]
        else:  # 20% potential issues
            extras["dbEvent"] = "issue"
            issue = random.random()
            if issue < 0.4:
                extras["message"] = "Unauthorized access attempt"
                et = ["db", "unauthorized_access"]
            elif issue < 0.7:
                extras["message"] = "Connection limit reached"
                et = ["db", "resource_limit"]
            else:
                extras["message"] = "Database deadlock detected"
                et = ["db", "error"]
        eventtype_out = et if random.random() < 0.85 else ",".join(et)
    elif "ftp" in app.lower() and "sftp" not in app.lower():
        dest_port = random.choice([21, 2022])
        src_port = random.randint(1024, 65535)
    elif "dns" in app.lower():
        if random.random() < 0.6:
            # incoming query
            dest_port = 53
            src_port = random.randint(1024, 65535)
            extras["dnsDirection"] = "query"
        else:
            # outgoing response
            src_port = 53
            dest_port = random.randint(1024, 65535)
            extras["dnsDirection"] = "response"
    elif "mail" in app.lower():
        dest_port = random.choice([25, 465, 110, 143, 995, 993])
        src_port = random.randint(1024, 65535)
    elif "ntp" in app.lower():
        dest_port = 123
        src_port = random.randint(1024, 65535)
    elif "firewall" in app.lower():
        # firewall sees traffic to/from many services
        service_ports = [22, 80, 443, 8080, 8443, 21, 2022, 3306, 53, 123, 25, 465, 110]
        dest_port = random.choice(service_ports)
        src_port = random.randint(1024, 65535)
        fw_scenario = random.random()
        
        if fw_scenario < 0.6:  # 60% normal traffic filtering
            extras["firewallAction"] = random.choices(["allowed", "denied", "dropped"], weights=[80,15,5])[0]
            protocol = "TCP" if dest_port not in [53, 123] else "UDP"
            extras["protocol"] = protocol
            extras["message"] = f"{protocol} {src_ip}:{src_port} -> {dest}:{dest_port}"
            if extras["firewallAction"] != "allowed":
                extras["actionReason"] = random.choice([
                    "blocked by policy",
                    "rate limit exceeded",
                    "invalid packet",
                    "unauthorized source"
                ])
            et = ["tcp" if protocol == "TCP" else "udp", "connect"]
        elif fw_scenario < 0.75:  # 15% port scans
            extras["firewallAction"] = "dropped"
            extras["scanType"] = random.choice(["SYN", "FIN", "XMAS", "NULL"])
            extras["message"] = f"Port scan detected from {src_ip}"
            extras["actionReason"] = f"{extras['scanType']} scan detected"
            et = ["tcp", "scan"]
        elif fw_scenario < 0.85:  # 10% DDoS
            extras["firewallAction"] = "dropped"
            ddos_type = random.choice(["SYN flood", "UDP flood", "ICMP flood", "HTTP flood"])
            extras["attackType"] = ddos_type
            extras["message"] = f"{ddos_type} attack detected"
            extras["packetRate"] = random.randint(10000, 1000000)
            et = ["ddos", "flood"]
        else:  # 15% other security events
            extras["firewallAction"] = "dropped"
            sec_event = random.random()
            if sec_event < 0.4:
                extras["message"] = "IP spoofing attempt detected"
                et = ["mitm", "spoof"]
            elif sec_event < 0.7:
                extras["message"] = "Invalid TCP flags combination"
                et = ["tcp", "invalid"]
            else:
                extras["message"] = "Blacklisted IP detected"
                et = ["access", "denied"]
            extras["actionReason"] = extras["message"]
            
        # Add severity for security events
        if extras["firewallAction"] != "allowed":
            extras["severity"] = random.choices(
                ["low", "medium", "high", "critical"],
                weights=[40, 30, 20, 10]
            )[0]
        eventtype_out = et if random.random() < 0.85 else ",".join(et)
    elif "ids" in app.lower():
        service_ports = [22, 80, 443, 8080, 8443, 21, 2022, 3306, 53, 123, 25]
        dest_port = random.choice(service_ports)
        src_port = random.randint(1024, 65535)
        # IDS logs include alerts and severity
        extras["alertCategory"] = random.choice(["port-scan","sql-injection","xss","malware","suspicious-traffic","mitm"])
        extras["severity"] = random.choices(["low","medium","high","critical"], weights=[50,30,15,5])[0]
        extras["alert"] = random.choice(ATTACK_REASONS)
    elif "alerts" in app.lower() and app.lower().strip() == "alerts":
        # Dedicated Alerts app: produce records that match alerts_schema.AlertOut
        dest_port = 0
        src_port = 0
        alert_id = str(uuid.uuid4())
        alert_ts = iso_now_minus()
        severity = random.choice(["critical", "high", "medium", "low"])
        source = random.choice(["server", "ids", "firewall", "mail", "db", "network"])
        title = random.choice([
            "Potential attack detected",
            "Server maintenance scheduled",
            "High severity IDS alert",
            "Suspicious login activity",
            "Service crash detected"
        ])
        description = random.choice([
            "Multiple failed logins observed from single IP",
            "Scheduled maintenance window started",
            "Signature matched for SQL injection attempt",
            "Elevated resource usage detected",
            None
        ])
        tags = random.sample(["security","maintenance","performance","availability","auth","network"], k=random.randint(0,3))
        extras["type"] = "alert"
        extras["id"] = alert_id
        extras["timestamp"] = alert_ts
        extras["title"] = title
        extras["severity"] = severity
        extras["source"] = source
        if description:
            extras["description"] = description
        extras["tags"] = tags
    elif "system" in app.lower() or "server" in app.lower() or "server events" in app.lower() or "system logs" in app.lower():
        # System/server logs are host-centric and often don't have network ports
        dest_port = 0
        src_port = 0
        extras["logLevel"] = random.choice(["INFO","NOTICE","WARN","ERROR","CRITICAL"])
        svc = random.choice(["svh-server","nginx","postgres","redis","cron","systemd","sshd"])
        extras["serviceName"] = svc
        # pick a realistic message and matching event type
        msg_type = random.random()
        if msg_type < 0.15:
            extras["message"] = "Scheduled maintenance window started"
            extras["alertType"] = "maintenance"
            extras["scheduled"] = True
            extras["durationMinutes"] = random.choice([30,60,120,240])
            et = ["system", "maintenance"]
        elif msg_type < 0.25:
            extras["message"] = "Unplanned service crash detected"
            extras["alertType"] = "service_crash"
            extras["scheduled"] = False
            et = ["system", "service_stop"]
        elif msg_type < 0.45:
            extras["message"] = f"{svc} restarted successfully"
            et = ["system", "service_start"]
        elif msg_type < 0.65:
            extras["message"] = f"{svc} failed health check"
            et = ["system", "service_stop"]
        elif msg_type < 0.85:
            extras["message"] = f"High CPU usage detected on host: {random.randint(60,98)}%"
            et = ["system", "resource_alert"]
        elif msg_type < 0.95:
            extras["message"] = f"Disk usage exceeded threshold on /var: {random.randint(80,99)}%"
            et = ["system", "resource_alert"]
        else:
            extras["message"] = f"User login failed for user {gen_userid()}"
            et = ["system", "auth_fail"]
        extras["uptimeSeconds"] = random.randint(60, 60*60*24*30)
        extras["cpuPercent"] = round(random.uniform(0.5, 98.0), 1)
        extras["memoryPercent"] = round(random.uniform(0.5, 98.0), 1)
        eventtype_out = et if random.random() < 0.85 else ",".join(et)
    else:
        # fallback: pick reasonable port
        proto = et[0] if isinstance(et, list) else (et.split(",")[0] if isinstance(et, str) else "tcp")
        if proto in ("ssh",):
            dest_port = 22
        elif proto in ("http",):
            dest_port = random.choice([80, 8080, 8443])
        elif proto in ("udp", "dns_query"):
            dest_port = 53
        else:
            dest_port = random.choice(PORTS)
        src_port = random.randint(1024, 65535)

    # decide reason/attack
    is_attack = False
    reason = None
    resource = None
    if "bruteforce" in (et if isinstance(et, list) else [et]):
        is_attack = True
        reason = "multiple failed attempts"
    elif "scan" in (et if isinstance(et, list) else [et]) or random.random() < 0.06:
        is_attack = True
        reason = "port scan detected"
    elif "sql_injection" in (et if isinstance(et, list) else [et]) or random.random() < 0.03:
        is_attack = True
        reason = "detected signatures of SQLi"
        resource = "/api/v1/items?id=1' OR '1'='1"
    elif "xss" in (et if isinstance(et, list) else [et]) or random.random() < 0.02:
        is_attack = True
        reason = "detected XSS payload"
        resource = "/comments?c=<script>"
    elif "ddos" in (et if isinstance(et, list) else [et]) or random.random() < 0.01:
        is_attack = True
        reason = "traffic volume spike - SYN flood"
    elif "mitm" in (et if isinstance(et, list) else [et]) or random.random() < 0.01:
        is_attack = True
        reason = "ARP cache poisoning detected"

    if not reason and random.random() < 0.12:
        reason = random.choice(ATTACK_REASONS)

    inner = make_inner(idn, app, user, src_ip, dest, et, src_port, dest_port, reason, resource, extras)

    result = {
        "src_port": src_port,
        "dest_port": dest_port,
        "_time": inner["createdDateTime"],
        "conditionalAccessStatus": cond,
        "riskLevel": risk,
        "host": host,
        "appDisplayName": app,
        "ipAddress": src_ip,
        "dest": dest,
        "userPrincipalName": user
    }

    # include any inner status if present
    if inner.get("status") and random.random() < 0.4:
        result["status"] = inner["status"]

    if extras and isinstance(extras, dict):
        for k in extras:
            if k not in result:
                result[k] = inner.get(k)

    # if extras include IDS/Firewall fields, promote to top-level for easier parsing
    for k in ("firewallAction", "actionReason", "alertCategory", "severity", "alert", "dnsDirection"):
        if k in inner:
            result[k] = inner[k]

    use_raw = random.random() < 0.45
    if use_raw:
        result["_raw"] = json.dumps(inner, separators=(",",":"), ensure_ascii=False)
        result["eventtype"] = eventtype_out if isinstance(eventtype_out, str) else eventtype_out
    else:
        for k, v in inner.items():
            result[k] = v
        if isinstance(result.get("eventtype"), list) and random.random() < 0.2:
            result["eventtype"] = ",".join(result["eventtype"])

    if is_attack:
        result["threatIndicator"] = "attack"

    return {"result": result}

def main():
    # Determine selected apps based on --apps patterns (case-insensitive substring match)
    def select_apps(patterns):
        if not patterns:
            return APPS[:]
        pats = [p.strip().lower() for p in patterns.split(",") if p.strip()]
        selected = []
        for p in pats:
            for a in APPS:
                if p in a.lower() and a not in selected:
                    selected.append(a)
        return selected

    selected_apps = select_apps(args.apps)
    if not selected_apps:
        print("No apps matched --apps patterns. Available apps:\n" + ", ".join(APPS), file=sys.stderr)
        sys.exit(2)

    if args.mode == "combined":
        outfh = None
        # If output is not being redirected and no --out specified, use datasets folder
        if not args.out and sys.stdout.isatty():
            os.makedirs(args.out_dir, exist_ok=True)
            output_path = os.path.join(args.out_dir, "output.ndjson")
            outfh = open(output_path, "w", encoding="utf-8")
        elif args.out:
            outfh = open(args.out, "w", encoding="utf-8")
        
        target_print = (lambda s: outfh.write(s + "\n")) if outfh else (lambda s: print(s))
        for i in range(1, COUNT+1):
            app_choice = random.choice(selected_apps)
            rec = make_record_for_app(i, app_choice)
            target_print(json.dumps(rec, ensure_ascii=False))
        if outfh:
            outfh.close()
            path_msg = args.out if args.out else output_path
            print(f"Wrote combined output to {path_msg}", file=sys.stderr)
    else:
        out_dir = args.out_dir or os.getcwd()
        os.makedirs(out_dir, exist_ok=True)
        for app in selected_apps:
            slug = "".join([c if c.isalnum() else "_" for c in app]).lower()
            path = os.path.join(out_dir, f"{slug}.ndjson")
            with open(path, "w", encoding="utf-8") as fh:
                for i in range(1, COUNT+1):
                    rec = make_record_for_app(i, app)
                    fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
            print(f"Wrote {COUNT} records for '{app}' -> {path}", file=sys.stderr)

if __name__ == "__main__":
    main()
