# app/core/security.py
from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import Depends, HTTPException, status
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
ACCESS_TOKEN_EXPIRE_MINUTES = 20
REFRESH_TOKEN_EXPIRE_DAYS    = 7

# IMPORTANT: Move this to environment variables or config!
# Never commit real secret keys
SECRET_KEY = "yourkeyherewithoutquotes"
if not SECRET_KEY:
    raise RuntimeError("SECRET_KEY not set in environment or config!")

# OAuth2 scheme – extracts token from Authorization: Bearer <token>
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/v1/auth/login",
    scheme_name="Bearer",
    description="JWT Access Token (format: Bearer <token>)",
    auto_error=True
)


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
    """
    Create a JWT token (access or refresh)
    """
    expire = datetime.now(timezone.utc) + expires_delta
    to_encode = {
        "sub": subject,
        "role": role,
        "type": token_type,
        "exp": expire,
    }
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    Validates the JWT from Authorization: Bearer header
    and returns the authenticated user.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str | None = payload.get("sub")
        token_type: str | None = payload.get("type")

        if user_id is None:
            raise credentials_exception

        if token_type != "access":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="This token cannot be used for authentication (expected access token)",
                headers={"WWW-Authenticate": "Bearer"},
            )

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