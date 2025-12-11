from fastapi import Depends, HTTPException, status, Header
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.database import get_db
import os
import logging
from typing import Optional
import uuid

logger = logging.getLogger(__name__)

TEST_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")

async def get_current_user(
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db)
):
    """
    Get current user from Authorization header (optional for testing)
    Returns a test user UUID by default, or None if explicitly needed
    For MVP: No authentication required - defaults to test user
    """
    if not authorization:
        return {"sub": str(TEST_USER_ID), "is_authenticated": False}
    
    try:
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            return {"sub": str(TEST_USER_ID), "is_authenticated": False}
        
        # For MVP: Simple token validation (replace with JWT in production)
        if token == os.getenv("API_KEY", "demo-key"):
            return {"sub": str(uuid.uuid4()), "is_authenticated": True}
        
        return {"sub": str(TEST_USER_ID), "is_authenticated": False}
    except Exception as e:
        logger.error(f"Auth error: {e}")
        return {"sub": str(TEST_USER_ID), "is_authenticated": False}
