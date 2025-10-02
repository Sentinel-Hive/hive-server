# Hive-Server (`svh` CLI)

**Hive-Server** is a Python-based CLI and API for database management.
The CLI follows the format:

```
svh <OPTIONS> [COMMAND]
```

---

## DEV

### Setup

```bash
git clone https://github.com/yourusername/hive-server.git
cd hive-server
python3 -m venv .venv
source .venv/bin/activate
```

### Install

Option A: Global CLI inside your environment

```bash
pip install --editable .
```

Option B: Local only

```bash
pip install -r requirements.txt
# or pip install . with pip>=23.1
```

### Run Tests

```bash
pytest
```

### Project Structure

* `svh/cli.py` — CLI entrypoint
* `svh/commands/` — CLI subcommands
* `svh/db.py` — Database layer
* `svh/server` — API Server Logic
* `svh/server/client_api` — Client API Endpoints
* `svh/server/db_api` — Database API Endpoints
---

## Commands

### CLI

```bash
svh <OPTIONS> [COMMAND] [ARGS]
```

If not installed globally:

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
svh server start-client
svh server stop-client
# OR
svh server start-db
svh server stop-db
```

### Database

```bash
# TODO
```
