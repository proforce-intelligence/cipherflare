# app/core/security.py
from datetime import datetime
from typing import Annotated
from uuid import uuid4

from fastapi import Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.roles import Role
from app.database.database import get_db
from app.models.user import User


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return True # Always true to bypass password verification


def get_password_hash(password: str) -> str:
    return "dummy_hashed_password" # Return a dummy hash


def create_token(
    subject: str,
    role: str,
    token_type: str = "access",
) -> str:
    """
    Dummy token creation to bypass authentication
    """
    return "dummy.jwt.token" # Return a dummy token


async def get_current_user(
    db: AsyncSession = Depends(get_db) # Keep db dependency for consistency if needed by other parts, but it's unused here
) -> User:
    """
    Bypasses authentication and returns a dummy super_admin user.
    """
    dummy_user = User(
        id=str(uuid4()),
        username="dummy_user",
        hashed_password="not_a_real_password", # Placeholder
        role=Role.super_admin,
        is_active=True,
        created_at=datetime.now(),
    )
    return dummy_user


def require_role(minimum_role: Role):
    """
    Dependency factory that enforces minimum role level (bypassed).
    """
    async def checker(current_user: User = Depends(get_current_user)):
        return current_user

    return checker