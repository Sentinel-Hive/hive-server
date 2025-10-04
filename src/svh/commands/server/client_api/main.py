from fastapi import FastAPI
import platform
from datetime import datetime

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
