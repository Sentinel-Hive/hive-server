from fastapi import FastAPI, Request, UploadFile, File
from typing import List, Optional
import platform
from datetime import datetime
from svh import notify

app = FastAPI(title="Sentinel API", version="0.1.0")


@app.get("/health")
def health():
    return {"name": "CLIENT_HANDLER", "status": "ok"}


@app.get("/metadata")
def metadata():
    return {
        "service": "CLIENT_HANDLER",
        "version": "0.1.0",
        "python": platform.python_version(),
        "platform": platform.system(),
        "started_at": datetime.now().isoformat(),
    }


@app.post("/ingest")
async def ingest(request: Request, files: Optional[List[UploadFile]] = File(None)):
    try:
        if files:
            count = len(files)
            notify.server(f"Received {count} file(s) via multipart/form-data")
            return {"status": "received", "files_received": count}

        content_type = request.headers.get("content-type", "")
        if "application/json" in content_type:
            data = await request.json()
            count = len(data.get("files", [])) if isinstance(data, dict) else 0
            notify.server(f"Received {count} file(s) via JSON payload")
            return {"status": "received", "files_received": count}

        notify.error(f"Unsupported Content-Type: {content_type}")
        return {
            "status": "error",
            "detail": f"Unsupported Content-Type: {content_type}",
        }

    except Exception as e:
        notify.error(f"Error processing ingestion request: {e}")
        return {"status": "error", "detail": str(e)}
