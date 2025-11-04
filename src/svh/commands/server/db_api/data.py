from fastapi import APIRouter, HTTPException, status
from typing import Any, Dict
from svh.commands.db.session import session_scope
from sqlalchemy import text
from svh import notify, storage

router = APIRouter()


@router.post("/data/store", status_code=status.HTTP_201_CREATED)
async def store_data(data: Dict[str, Any]):
    """
    Store JSON data in the database.
    Internal endpoint - only called by Client API.
    """
    file_path = ""
    if not data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="No data provided"
        )
    if "name" not in data or "content" not in data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing required fields: 'name' and 'content'",
        )

    notify.info(f"Received dataset: {data['name']}")
    try:
        file_path = storage.add(data)
        # Store relative path for portability
        dataset_path = str(file_path.relative_to(storage.PROJECT_ROOT))
    except Exception as e:
        notify.error(f"File write failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save file: {e}",
        )

    try:
        with session_scope() as session:
            query = text(
                """
                INSERT INTO datasets (dataset_name, dataset_path, added_at)
                VALUES (:dataset_name, :dataset_path, CURRENT_TIMESTAMP)
                RETURNING id
                """
            )
            result = session.execute(
                query,
                {
                    "dataset_name": data["name"][:100],
                    "dataset_path": dataset_path,
                },
            )
            row = result.fetchone()
        notify.database(f"Stored dataset '{data['name']}' with id={row[0]}")
        return {"id": row[0], "name": data["name"], "path": dataset_path}
    except Exception as e:
        notify.error(f"DB insert failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to store data: {str(e)}",
        )
