# app/core/security.py
from datetime import datetime, timedelta, timezone
from typing import Annotated, Optional

from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.database import get_db
from app.models.user import User
from app.core.roles import Role

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

ALGORITHM = "HS256"

# Recommended lifetimes (adjust as needed)
ACCESS_TOKEN_EXPIRE_MINUTES = 20          # short-lived
REFRESH_TOKEN_EXPIRE_DAYS    = 7

# Move to app/core/config.py → settings.SECRET_KEY
# For now keeping fallback (but NEVER commit real key!)
SECRET_KEY = "yourkeyherewithoutquotes"
if not SECRET_KEY:
    raise RuntimeError("SECRET_KEY not set in environment or config!")

security = HTTPBearer(auto_error=False)  # We'll handle manually


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_token(
    subject: str,
    role: str,
    expires_delta: timedelta,
    token_type: str = "access",
) -> str:
    expire = datetime.now(timezone.utc) + expires_delta
    to_encode = {
        "sub": subject,
        "role": role,
        "type": token_type,          # helps distinguish access vs refresh
        "exp": expire,
    }
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db)
) -> User:
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid authentication credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None or payload.get("type") != "access":
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise credentials_exception
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Inactive user")

    return user


# Role-based access (unchanged but using new get_current_user)
ROLE_LEVELS = {
    Role.super_admin: 100,
    Role.admin: 80,
    Role.role_user: 40,
    Role.viewer: 20,
}


def require_role(minimum_role: Role):
    async def checker(current_user: User = Depends(get_current_user)):
        user_level = ROLE_LEVELS.get(current_user.role, 0)
        required_level = ROLE_LEVELS.get(minimum_role, 0)
        if user_level < required_level:
            raise HTTPException(
                status_code=403,
                detail=f"Required role: {minimum_role.value} or higher"
            )
        return current_user
    return checker