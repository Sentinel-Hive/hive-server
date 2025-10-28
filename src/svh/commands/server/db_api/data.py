from fastapi import APIRouter, HTTPException, status
from typing import Any, Dict
from svh.commands.db.session import session_scope
from sqlalchemy import text
import json

router = APIRouter()


@router.post("/data/store", status_code=status.HTTP_201_CREATED)
async def store_data(data: Dict[str, Any]):
    """
    Store JSON data in the database.
    Internal endpoint - only called by Client API.
    """
    if not data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="No data provided"
        )

    try:
        with session_scope() as session:
            query = text(
                """
                INSERT INTO data_store (content, created_at)
                VALUES (:content, CURRENT_TIMESTAMP)
                RETURNING id
            """
            )
            result = session.execute(query, {"content": json.dumps(data)})
            row = result.fetchone()
            return {"id": row[0]}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to store data: {str(e)}",
        )
