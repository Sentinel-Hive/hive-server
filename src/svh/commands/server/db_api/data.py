from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import text

from svh import notify, storage
from svh.commands.db.session import session_scope

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


@router.get("/data/file", status_code=status.HTTP_200_OK)
async def get_data_file(
    id: int = Query(..., description="ID of the stored item whose file to read")
):
    """
    Return the *file contents* for a given dataset id.
    """
    # 1) Look up dataset_path in the DB
    with session_scope() as session:
        row = session.execute(
            text(
                """
                SELECT dataset_path
                FROM datasets
                WHERE id = :id
                """
            ),
            {"id": id},
        ).fetchone()

        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Item with id={id} not found",
            )

        dataset_path = row[0]

    # 2) Build absolute path from PROJECT_ROOT + relative dataset_path
    file_path = Path(storage.PROJECT_ROOT) / dataset_path

    # 3) Read the file as text
    try:
        if not file_path.is_file():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"File at path '{dataset_path}' not found on storage",
            )

        content = file_path.read_text(encoding="utf-8")

        # If you know it's JSON and want to parse it:
        # import json
        # try:
        #     parsed = json.loads(content)
        # except json.JSONDecodeError:
        #     parsed = content

        return {
            "id": id,
            "dataset_path": dataset_path,
            "content": content,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to read stored file: {e}",
        )
