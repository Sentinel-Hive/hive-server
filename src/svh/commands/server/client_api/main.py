from fastapi import FastAPI
import platform
from datetime import datetime
from .auth import router as auth_router
from .users import router as users_router
from .health import router as health_router

app = FastAPI(title="Sentinel API", version="0.1.0")

app.include_router(health_router, prefix="/health", tags=["health"])
app.include_router(users_router, prefix="/users", tags=["users"])
app.include_router(auth_router,  prefix="/auth",  tags=["auth"])

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
