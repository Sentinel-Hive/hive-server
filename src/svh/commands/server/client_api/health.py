from fastapi import APIRouter
from ...db.session import create_all

router = APIRouter()

@router.get("/ready")
def ready():
    create_all()  # ensure tables exist (idempotent)
    return {"ok": True}
