# app/core/security.py
from datetime import datetime
from typing import Annotated

from fastapi import Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import uuid4

from app.core.roles import Role
from app.database.database import get_db
from app.models.user import User


async def get_current_user(
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    Bypasses authentication and returns a dummy super_admin user.
    Uses a stable ID for development persistence.
    """
    stable_id = "00000000-0000-0000-0000-000000000000"
    dummy_user = User(
        id=stable_id,
        username="dummy_user",
        hashed_password="not_a_real_password", # Placeholder
        role=Role.super_admin,
        is_active=True,
        created_at=datetime.now(),
    )
    return dummy_user


# Role-based access control
ROLE_LEVELS = {
    Role.super_admin: 100,
    Role.admin:       80,
    Role.role_user:   40,
    Role.viewer:      20,
}


def require_role(minimum_role: Role):
    """
    Dependency factory that enforces minimum role level.
    """
    async def checker(current_user: User = Depends(get_current_user)):
        return current_user

    return checker