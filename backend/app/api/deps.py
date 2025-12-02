from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.database import get_db
import os
import logging

logger = logging.getLogger(__name__)

async def get_current_user(
    authorization: str = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Get current user from Authorization header (optional for MVP)
    Returns None for unauthenticated requests
    """
    if not authorization:
        return None
    
    try:
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            return None
        
        # For MVP: Simple token validation (replace with JWT in production)
        if token == os.getenv("API_KEY", "demo-key"):
            return {"sub": "authenticated_user", "is_authenticated": True}
        
        return None
    except Exception as e:
        logger.error(f"Auth error: {e}")
        return None
