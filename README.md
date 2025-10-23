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

**4. Install dependencies**
```bash
pip install httpx
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
svh server start -d
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

