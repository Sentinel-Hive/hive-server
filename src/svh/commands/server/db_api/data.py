from fastapi import APIRouter, HTTPException, status, Query
from typing import Any, Dict, Optional
from svh.commands.db.session import session_scope
from sqlalchemy import text
from svh import notify, storage
import httpx

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


@router.get("/data", status_code=status.HTTP_200_OK)
async def get_data(
    id: Optional[str] = Query(
        None, description="ID of the stored item (omit to fetch all)"
    )
):
    """
    Retrieve stored data.
    """
    try:
        with session_scope() as session:
            if id is None:
                q = text(
                    """
                    SELECT *
                    FROM datasets
                    ORDER BY added_at DESC, id DESC
                    """
                )
                result = session.execute(q).fetchall()

                def to_dict(r):
                    added = r[3]
                    try:
                        added = added.isoformat()
                    except Exception:
                        pass
                    return {
                        "id": r[0],
                        "dataset_name": r[1],
                        "dataset_path": r[2],
                        "added_at": added,
                    }

                return [to_dict(row) for row in result]
            try:
                item_id = int(id)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid id; must be an integer",
                )
            q = text(
                """
                SELECT id, dataset_name, dataset_path, added_at
                FROM datasets
                WHERE id = :id
                """
            )
            row = session.execute(q, {"id": item_id}).fetchone()
            if not row:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Item with id={item_id} not found",
                )

            added = row[3]
            try:
                added = added.isoformat()
            except Exception:
                pass

            return {
                "id": row[0],
                "dataset_name": row[1],
                "dataset_path": row[2],
                "added_at": added,
            }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve data: {str(e)}",
        )
