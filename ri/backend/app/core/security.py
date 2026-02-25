# app/core/security.py
from datetime import datetime, timedelta, timezone
from typing import Annotated, Optional

from fastapi import Depends, HTTPException, status, Request, Response
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.roles import Role
from app.database.database import get_db
from app.models.user import User

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 15     # short → forces refresh
REFRESH_TOKEN_EXPIRE_DAYS    = 14    # reasonable for most apps

SECRET_KEY = "your-very-long-random-secret-key-here"  # ← CHANGE THIS

# ─── Optional: also support Bearer header (for Swagger/Postman/curl) ───
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/v1/auth/login",
    auto_error=False   # ← important: do not auto-raise 401
)


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

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
        "type": token_type,
        "exp": expire,
    }
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


async def get_current_user(
    request: Request,
    token_from_header: Annotated[Optional[str], Depends(oauth2_scheme)] = None,
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    Try to authenticate from:
    1. Authorization: Bearer header (Swagger, API clients)
    2. access_token cookie (browser sessions)
    """
    token = None

    # 1. Prefer header (Swagger, Postman, mobile apps)
    if token_from_header:
        token = token_from_header

    # 2. Fallback to cookie (browser)
    elif "access_token" in request.cookies:
        token = request.cookies["access_token"]

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str | None = payload.get("sub")
        token_type: str | None = payload.get("type")

        if user_id is None or token_type != "access":
            raise credentials_exception

    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token validation failed: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        ) from e

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if user is None:
        raise credentials_exception

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )

    return user


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
        user_level = ROLE_LEVELS.get(current_user.role, 0)
        required_level = ROLE_LEVELS.get(minimum_role, 0)

        if user_level < required_level:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required role: {minimum_role.value} or higher"
            )

        return current_user

    return checker




def set_secure_auth_cookies(
    response: Response,
    access_token: str,
    refresh_token: str,
    request: Request,
):
    hostname = request.url.hostname

    # Treat these as development / insecure environments
    is_dev = any(
        s in hostname
        for s in [
            "0.0.0.0",
            "127.0.0.1",
            "0.0.0.0",
            "192.168.",           # ← add this (covers 192.168.x.x)
            "10.",                # optional: add common private ranges
            "172.16.", "172.17.", "172.18.", "172.19.", "172.20.", "172.21.", "172.22.", "172.23.", "172.24.", "172.25.", "172.26.", "172.27.", "172.28.", "172.29.", "172.30.", "172.31.",
        ]
    )

    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=not is_dev,
        samesite="lax",
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        path="/",
    )

    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=not is_dev,
        samesite="lax",
        max_age=REFRESH_TOKEN_EXPIRE_DAYS * 24 * 3600,
        path="/",
    )