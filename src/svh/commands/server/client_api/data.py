from typing import Any, Dict, List, Optional

import httpx
from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy import select, text

from svh import notify
from svh.commands.db.models import AuthToken, User
from svh.commands.db.session import session_scope
from svh.commands.server.util_config import get_db_api_base_for_client
from svh.storage import read

router = APIRouter()

DB_API_URL = get_db_api_base_for_client()


async def verify_admin_token(authorization: Optional[str] = Header(None)):
    """Verify the bearer token belongs to an admin user."""
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required"
        )

    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header",
        )

    token_value = authorization.replace("Bearer ", "")

    try:
        with session_scope() as session:
            # Find valid token
            token = session.execute(
                select(AuthToken).where(AuthToken.token == token_value)
            ).scalar_one_or_none()

            if not token:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
                )

            # Check if token is revoked
            if token.revoked_at is not None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token has been revoked",
                )

            # Get all users and find by id
            # Get schema and find the tables columns
            schema_query = text("PRAGMA table_info(users)")
            schema_result = session.execute(schema_query)
            columns = [row[1] for row in schema_result.fetchall()]

            # Parse username from token string
            token_parts = token.token.split(".")
            username_or_id = token_parts[0]

            # Get all users to find the right one
            all_users_query = text("SELECT * FROM users")
            all_users = session.execute(all_users_query).fetchall()

            user_row = None
            for row in all_users:
                # Check each column for a match
                for i, col in enumerate(columns):
                    try:
                        if str(row[i]).lower() == username_or_id.lower():
                            user_row = row
                            break
                    except:
                        continue
                if user_row:
                    break

            if not user_row:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found"
                )

            # Find is_admin column index
            is_admin_idx = columns.index("is_admin") if "is_admin" in columns else None

            if is_admin_idx is None or not user_row[is_admin_idx]:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Admin access required",
                )

            return user_row
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Token verification failed: {str(e)}",
        )


@router.post("/data", status_code=status.HTTP_201_CREATED)
async def store_data(data: Dict[str, Any], user: User = Depends(verify_admin_token)):
    """
    Store JSON data in the database (admin only).
    """
    if not data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="No data provided"
        )

    try:
        # Pass JSON data to DB_Endpoint (DB API)
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{DB_API_URL}/data/store", json=data, timeout=10.0
            )

            if response.status_code != 201:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="DB API failed to store data",
                )

            result = response.json()
            return {"success": True, "id": result["id"]}

    except httpx.RequestError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to communicate with DB API: {str(e)}",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to store data: {str(e)}",
        )


@router.delete("/data/{id}")
async def delete_data(id: int, user: User = Depends(verify_admin_token)):
    """
    Admin-only: delete a dataset by id.
    Forwards the request to the DB API and returns its result.
    """
    try:
        async with httpx.AsyncClient() as client:
            res = await client.delete(f"{DB_API_URL}/data/{id}", timeout=10.0)
            if res.status_code == 404:
                raise HTTPException(status_code=404, detail="Dataset not found")
            if res.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail=f"DB API failed to delete dataset (status {res.status_code})",
                )
            return res.json()
    except HTTPException:
        raise
    except httpx.RequestError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to communicate with DB API: {e}",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete dataset: {e}",
        )


async def verify_user_token(authorization: Optional[str] = Header(None)):
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required"
        )
    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header",
        )

    token_value = authorization.replace("Bearer ", "").strip()

    try:
        with session_scope() as session:
            token = session.execute(
                select(AuthToken).where(AuthToken.token == token_value)
            ).scalar_one_or_none()
            if not token:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
                )
            if token.revoked_at is not None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token has been revoked",
                )
            user = session.execute(
                select(User).where(User.id == token.user_id_fk)
            ).scalar_one_or_none()
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found"
                )
            return user
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Token verification failed: {str(e)}",
        )


@router.get("/data", status_code=status.HTTP_200_OK)
async def get_data(
    id: Optional[str] = Query(
        None, description="ID of the stored item (omit to fetch all)"
    ),
    include_record: bool = Query(
        True, description="Return DB metadata (id/name/path/etc)"
    ),
    include_file: bool = Query(
        False, description="Return the actual JSON stored at storage_path"
    ),
    file_path: Optional[str] = Query(
        None, description="Storage path of requested file"
    ),
    user: User = Depends(verify_user_token),
):
    """
    Retrieve stored data — authenticated users only.
    """
    if not include_record and not include_file:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one of include_record or include_file must be true.",
        )

    if not include_record and include_file and file_path:
        try:
            content = read(file_path)
            return {content}
        except:
            raise

    try:
        async with httpx.AsyncClient() as client:
            url = f"{DB_API_URL}/data/{id}" if id else f"{DB_API_URL}/data"
            res = await client.get(url, timeout=10.0)
            if res.status_code == 404:
                if id:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND, detail="No records found"
                    )
                return {"count": 0, "items": []}
            if res.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail=f"DB API failed to fetch data (status {res.status_code})",
                )
            payload = res.json()
            if isinstance(payload, dict) and "items" in payload:
                raw_records = payload.get("items", [])
            elif isinstance(payload, list):
                raw_records = payload
            else:
                raw_records = [payload]
            results: List[Dict[str, Any]] = []
            for record in raw_records:
                entry: Dict[str, Any] = {}
                if include_record:
                    entry["record"] = record

                results.append(entry)
            if id:
                if not results:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND, detail="No records found"
                    )
                return results[0]
            return {"count": len(results), "items": results}

    except HTTPException:
        raise
    except httpx.RequestError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to communicate with DB API or storage: {str(e)}",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve data: {str(e)}",
        )
