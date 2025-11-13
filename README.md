# Hive-Server (`svh` CLI)

**Hive-Server** is a Python-based CLI and API for database management.

This documentation is meant to serve as a "quick-start"! To get a better understanding, please visit the **Hive-Server wiki**!.

---

## Installation
*Install files/scripts coming soon!*

## Installation (Dev)

### Linux / macOS Installation

**1. Clone repository**
```bash
git clone https://github.com/yourusername/hive-server.git
cd hive-server
```

**2. Create and activate virtual environment**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

**3. Install in editable (dev) mode**
```bash
pip install --editable .
```
### Windows (PowerShell)

**1. Clone repository**
```bash
git clone https://github.com/yourusername/hive-server.git
cd hive-server
```

**2. Create virtual environment**
```bash
python -m venv .venv
```

**3. Activate virtual environment**
```bash
.\.venv\Scripts\activate.bat
```

**4. Install in editable (dev) mode**
```bash
pip install --editable .
```

**5. Install dependencies**
```bash
pip install httpx
```

```powershell
Add-WindowsCapability -Online -Name OpenSSH.Server~~~~0.0.1.0
Start-Service sshd
Set-Service -Name sshd -StartupType 'Automatic'
```

---

## Commands
Commands generally follow the structure below.
```bash
svh <OPTIONS> [COMMAND] [ARGS]
```

If CLI tool is not installed globally, they then follow this format:
```bash
python -m svh.cli <OPTIONS> [COMMAND] [ARGS]
```

### API Server
To run both the Client and Db API Servers, use the command:
```bash
svh server start
```

However, you can also run each individually, and stop each individually with:
```bash
svh server start -s client
svh server stop -s client
# OR
svh server start -s db
svh server stop -s db
```

### Database

```bash
# TODO
```

---

## Testing Data Ingestion Endpoint

The data ingestion endpoint accepts JSON data and stores it in the database.

### Prerequisites
1. Start both servers:
```bash
svh server start -dhttps://github.com/Sentinel-Hive/hive-server/pull/9/conflict?name=src%252Fsvh%252Fcommands%252Fserver%252Fclient_api%252Fmain.py&ancestor_oid=0a8d2b553cdf4bf11042cdaeef9177fa7274ffab&base_oid=e7c3cf257506fcdee5168a9fb0f6d000336b41f5&head_oid=42f935e35a729a8237db3ecf92190ee5d71a46c8
```

2. Login to create a session (default credentials: admin/admin):
```bash
svh server login --u admin --p admin
```

### Test With Admin Authentication (Production Endpoint)

**Step 1: Get an authentication token**
```bash
curl -X POST http://localhost:5167/auth/login \
  -H "Content-Type: application/json" \
  -d '{"user_id": "admin", "password": "admin"}'
```

**Response:**
```json
{"token": "admin.1760992694.bca67429b758d0398a3bfcc2fef00519f61de07c179021176c500011d1008f47"}
```

**Step 2: Use the token to store data**
```bash
curl -X POST http://localhost:5167/data \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer admin.1760992694.bca67429b758d0398a3bfcc2fef00519f61de07c179021176c500011d1008f47" \
  -d '{"authenticated": true, "secure": "data", "admin_test": "success"}'
```

**Expected Response:**
```json
{"success": true, "id": 2}
```

### Firewall

**Note for Windows users**: Firewall operations require administrator privileges. You'll be prompted by UAC (User Account Control) to approve elevated access when configuring firewall rules.

You can check firewall status with this command:
```bash
svh server status
```
You can start the firewall with this commnad: 
```bash
svh server -F

or

svh server firewall
```
You can start the server and the firewall at the same time with this commnad:
```bash
svh server start -cF -d
```
