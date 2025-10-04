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
.\.venv\Scripts\Activate.ps1
```

**4. Install in editable (dev) mode**
```bash
pip install --editable .
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
