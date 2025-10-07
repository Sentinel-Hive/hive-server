from fastapi import APIRouter
from ...db.session import create_all

router = APIRouter()

@router.get("/ready")
def ready():
    # ensure tables exist
    create_all()
    return {"ok": True}
