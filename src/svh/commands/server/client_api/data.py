from fastapi import APIRouter, HTTPException, status, Header, Depends
from typing import Any, Dict, Optional
from svh.commands.db.session import session_scope
from svh.commands.db.models import User, AuthToken
from sqlalchemy import text, select
from datetime import datetime
import json
import httpx
from svh.commands.server.util_config import get_db_api_base_for_client

router = APIRouter()

DB_API_URL = get_db_api_base_for_client()


async def verify_admin_token(authorization: Optional[str] = Header(None)):
    """Verify the bearer token belongs to an admin user."""
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    
    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header"
        )
    
    token_value = authorization.replace("Bearer ", "")
    
    try:
        with session_scope() as session:
            # Find valid token
            token = session.execute(
                select(AuthToken).where(
                    AuthToken.token == token_value
                )
            ).scalar_one_or_none()
            
            if not token:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token"
                )
            
            # Check if token is revoked
            if token.revoked_at is not None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token has been revoked"
                )
            
            # Get all users and find by id 
            # Get schema and find the tables columns
            schema_query = text("PRAGMA table_info(users)")
            schema_result = session.execute(schema_query)
            columns = [row[1] for row in schema_result.fetchall()]
            
            # Parse username from token string
            token_parts = token.token.split('.')
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
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User not found"
                )
            
            # Find is_admin column index
            is_admin_idx = columns.index('is_admin') if 'is_admin' in columns else None
            
            if is_admin_idx is None or not user_row[is_admin_idx]:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Admin access required"
                )
            
            return user_row
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Token verification failed: {str(e)}"
        )


@router.post("/data", status_code=status.HTTP_201_CREATED)
async def store_data(
    data: Dict[str, Any],
    user: User = Depends(verify_admin_token)
):
    """
    Store JSON data in the database (admin only).
    """
    if not data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No data provided"
        )
    
    try:
        # Pass JSON data to DB_Endpoint (DB API)
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{DB_API_URL}/data/store",
                json=data,
                timeout=10.0
            )
            
            if response.status_code != 201:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="DB API failed to store data"
                )
            
            result = response.json()
            return {"success": True, "id": result["id"]}
            
    except httpx.RequestError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to communicate with DB API: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to store data: {str(e)}"
        )
