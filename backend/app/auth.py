# app/core/security.py

import os
import bcrypt
from datetime import datetime, timedelta, timezone
from typing import Optional, Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.database import get_db
from app.models.user import User
from app.core.roles import Role


# ─── Configuration ──────────────────────────────────────────────────────────────
SECRET_KEY= "yourkeyherewithoutquotes"
if not SECRET_KEY:
    raise RuntimeError("SECRET_KEY environment variable is not set! Add it to .env")

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days - adjust as needed

security = HTTPBearer(
    scheme_name="Bearer Token",
    description="Paste your JWT access token (Bearer <token>)"
)

# ─── Password Hashing (using bcrypt) ────────────────────────────────────────────
def get_password_hash(password: str) -> str:
    """Hash password with bcrypt (secure, widely supported)"""
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password with bcrypt"""
    try:
        return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))
    except Exception:
        return False

# ─── JWT Token Creation ─────────────────────────────────────────────────────────
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT access token"""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# ─── Token Decoding Helper ──────────────────────────────────────────────────────
def decode_token(token: str) -> dict:
    """Decode JWT token and return payload"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

# ─── Get Current User from Bearer Token ─────────────────────────────────────────
async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    db: AsyncSession = Depends(get_db)
) -> User:
    """Validate Bearer token and return authenticated user"""
    payload = decode_token(credentials.credentials)
    user_id: str = payload.get("sub")

    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")

    # IMPORTANT: Force string comparison to avoid SQLAlchemy type confusion
    # This fixes 'str' object has no attribute 'hex' error
    result = await db.execute(
        select(User).where(User.id == str(user_id))
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="User inactive")

    return user

# ─── Role Checker (reusable dependency) ─────────────────────────────────────────
def require_role(min_role: Role):
    """Factory to create role-checking dependencies"""
    async def checker(current_user: User = Depends(get_current_user)):
        if current_user.role != min_role:
            raise HTTPException(
                status_code=403,
                detail=f"Required role: {min_role.value}"
            )
        return current_user
    return checker