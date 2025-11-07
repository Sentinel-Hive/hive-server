#!/usr/bin/env python3
"""
Usage:
    python gen_ndjson.py [count] [--seed N]
Example:
    python gen_ndjson.py 200 --seed 42 > sample.ndjson
"""

import json
import random
import sys
from datetime import datetime, timedelta
from ..security import gen_userid

COUNT = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else 100
SEED = None
if "--seed" in sys.argv:
    try:
        SEED = int(sys.argv[sys.argv.index("--seed") + 1])
    except Exception:
        SEED = None

random.seed(SEED)

APPS = [
    "SSH Daemon", "VPN Client", "HTTP Server", "Web App", "SFTP Service",
    "DB Proxy", "FTP Service", "Metrics Agent", "Custom App", "Load Balancer",
    "Firewall", "IDS", "DNS Server", "Mail Server", "NTP Server"
]
EVENT_TYPES = [
    ["ssh","login"], ["ssh","exec"], ["ssh","bruteforce"],
    ["http","get"], ["http","post"], ["http","sql_injection"],
    ["http","xss_attempt"], ["tcp","connect"], ["tcp","scan"],
    ["udp","dns_query"], ["icmp","ping"], ["sftp","transfer"],
    ["ftp","file_transfer"], ["rdp","login"], ["snmp","trap"],
    ["arp","spoof"], ["mitm","detected"], ["ddos","syn_flood"],
    ["malware","download"], ["smtp","send"]
]
CONDITIONAL = ["success","failure","info","warning"]
RISK = ["low", "medium", "high", "critical", ""]
ATTACK_REASONS = [
    "Invalid credentials", "connection timeout", "blocked by policy", "rate limit",
    "2FA required", "permission denied", "checksum mismatch", "multiple failed attempts",
    "detected signatures of SQLi", "large number of SYN", "ARP cache poisoning detected",
    "suspicious user-agent", "suspicious payload", "port closed", "timeout"
]
HOST_PREFIXES = ["app","host","web","db","vpn","fw","scanner","lb","ids","mail"]
PORTS = [22, 80, 443, 21, 3389, 3306, 5432, 53, 123, 8080, 8443, 2022, 5060]

def rand_ip(publicish=True):
    if random.random() < 0.6:
        return f"10.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(1,254)}"
    else:
        return f"{random.randint(1,223)}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(1,254)}"

def iso_now_minus():
    dt = datetime.utcnow() - timedelta(minutes=random.randint(0, 60*24*14))
    return dt.replace(microsecond=0).isoformat() + "Z"

def make_inner(idn, app, user, src_ip, dest, etype, src_port, dest_port, reason=None, resource_name=None):
    inner = {
        "id": idn,
        "createdDateTime": iso_now_minus(),
        "appDisplayName": app,
        "userPrincipalName": user,
        "ipAddress": src_ip,
        "dest": dest,
        "eventtype": etype,
        "src_port": src_port,
        "dest_port": dest_port
    }
    if resource_name:
        inner["resourceDisplayName"] = resource_name
    if reason:
        inner["status"] = {"failureReason": reason}
    return inner

def make_record(i):
    app = random.choice(APPS)
    user = gen_userid() + "@sentinelhive.com"
    src_ip = rand_ip()
    dest = rand_ip()
    et = random.choice(EVENT_TYPES)
    eventtype_out = et if random.random() < 0.85 else ",".join(et)
    cond = random.choice(CONDITIONAL)
    risk = random.choices(RISK, weights=[40,30,15,8,7])[0]
    host = f"{random.choice(HOST_PREFIXES)}-{random.randint(1,50)}"
    idn = f"evt-{str(i).zfill(4)}"

    # pick ports according to protocol bias
    proto = et[0] if isinstance(et, list) else (et.split(",")[0] if isinstance(et,str) else "tcp")
    if proto in ("ssh",):
        dest_port = 22
    elif proto in ("http",):
        dest_port = random.choice([80, 8080, 8443])
    elif proto in ("https",):
        dest_port = 443
    elif proto in ("ftp","sftp"):
        dest_port = random.choice([21, 2022])
    elif proto in ("rdp",):
        dest_port = 3389
    elif proto in ("udp", "dns_query"):
        dest_port = 53
    elif proto in ("icmp",):
        dest_port = 0
    elif proto in ("ddos",):
        dest_port = random.choice([80, 443, 8080])
    else:
        dest_port = random.choice(PORTS)

    src_port = random.randint(1024, 65535)

    # decide reason/attack
    is_attack = False
    reason = None
    resource = None
    if "bruteforce" in (et if isinstance(et,list) else [et]):
        is_attack = True
        reason = "multiple failed attempts"
    elif "scan" in (et if isinstance(et,list) else [et]) or random.random() < 0.06:
        is_attack = True
        reason = "port scan detected"
    elif "sql_injection" in (et if isinstance(et,list) else [et]) or random.random() < 0.03:
        is_attack = True
        reason = "detected signatures of SQLi"
        resource = "/api/v1/items?id=1' OR '1'='1"
    elif "xss" in (et if isinstance(et,list) else [et]) or random.random() < 0.02:
        is_attack = True
        reason = "detected XSS payload"
        resource = "/comments?c=<script>"
    elif "ddos" in (et if isinstance(et,list) else [et]) or random.random() < 0.01:
        is_attack = True
        reason = "traffic volume spike - SYN flood"
    elif "mitm" in (et if isinstance(et,list) else [et]) or random.random() < 0.01:
        is_attack = True
        reason = "ARP cache poisoning detected"

    if not reason and random.random() < 0.12:
        reason = random.choice(ATTACK_REASONS)

    inner = make_inner(idn, app, user, src_ip, dest, et, src_port, dest_port, reason, resource)

    result = {
        "src_port": src_port,
        "dest_port": dest_port,
        "_time": inner["createdDateTime"],
        "conditionalAccessStatus": cond,
        "riskLevelDuringSignIn": risk,
        "host": host,
        "appDisplayName": app,
        "ipAddress": src_ip,
        "dest": dest,
        "userPrincipalName": user
    }

    if inner.get("status") and random.random() < 0.4:
        result["status"] = inner["status"]

    use_raw = random.random() < 0.45
    if use_raw:
        # embed inner JSON stringified and also keep ports at top-level
        result["_raw"] = json.dumps(inner, separators=(",", ":"), ensure_ascii=False)
        result["eventtype"] = eventtype_out if isinstance(eventtype_out, str) else eventtype_out
    else:
        # flatten inner into top-level result (ensuring ports present)
        for k, v in inner.items():
            result[k] = v
        if isinstance(result.get("eventtype"), list) and random.random() < 0.2:
            result["eventtype"] = ",".join(result["eventtype"])

    if is_attack:
        result["threatIndicator"] = "attack"

    return {"result": result}

def main():
    for i in range(1, COUNT+1):
        rec = make_record(i)
        print(json.dumps(rec, ensure_ascii=False))

if __name__ == "__main__":
    main()
