from fastapi import FastAPI
import platform

app = FastAPI(title="Hive API", version="0.1.0")


@app.get("/health")
def health():
    return {"service": "DB_HANDLER", "status": "ok"}


@app.get("/metadata")
def metadata():
    return {
        "service": "DB_HANDLER",
        "version": "0.1.0",
        "python": platform.python_version(),
    }
