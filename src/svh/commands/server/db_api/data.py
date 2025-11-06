from fastapi import APIRouter, HTTPException, status
from typing import Any, Dict
from svh.commands.db.session import session_scope
from sqlalchemy import text, select
import json
import hashlib
import re
from sqlalchemy.exc import IntegrityError

from ...db.models import DataStore

router = APIRouter()


@router.post("/data/store", status_code=status.HTTP_201_CREATED)
async def store_data(data: Dict[str, Any]):
    if not data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No data provided"
        )

    # canonical representation for hashing SHA-256
    canonical = json.dumps(data, sort_keys=True, separators=(",", ":"))
    data_hash = hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def _slugify(s: str) -> str:
        s = s.lower().strip()
        s = re.sub(r"\s+", "-", s)
        s = re.sub(r"[^a-z0-9\-]", "-", s)
        s = re.sub(r"-{2,}", "-", s)
        s = s.strip("-")
        return s or "example"

    raw_name = str(data.get("name") or data.get("title") or "example")
    slug_base = _slugify(raw_name)

    try:
        with session_scope() as session:
            # duplicate check 
            existing = session.scalar(select(DataStore).where(DataStore.data_hash == data_hash))
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Duplicate data (identical content already stored)"
                )

            # create minimal row to obtain id (name/filename set after id known)
            ds = DataStore(content=data, data_hash=data_hash, name="", filename="")
            session.add(ds)
            try:
                session.flush()  
            except IntegrityError:
                session.rollback()
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Duplicate data (identical content already stored)"
                )

            # attempt to assign a stable name
            max_attempts = 3
            attempt = 0
            assigned = False
            while attempt < max_attempts and not assigned:
                attempt_suffix = f"-{attempt}" if attempt > 0 else ""
                display = f"{ds.id}-{slug_base}{attempt_suffix}"
                ds.name = display
                ds.filename = f"/datasets/{display}.json"
                session.add(ds)
                try:
                    session.flush()
                    assigned = True
                except IntegrityError:
                    # conflict updating name/filename; try again with different suffix
                    session.rollback()
                    attempt += 1
                    continue

            if not assigned:
                # give a clear error if we cannot assign a unique name after retries
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to assign unique name for data file after retries"
                )

            # session_scope will commit on exit
            return {"id": ds.id, "name": ds.name, "filename": ds.filename, "hash": ds.data_hash}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to store data: {str(e)}"
        )
