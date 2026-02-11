# app/routers/auth.py  (or your existing file)
from fastapi import APIRouter, Depends, HTTPException, status, Response, Request, Query, Body
from fastapi.security import OAuth2PasswordRequestForm

from datetime import timedelta
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.security import (
    verify_password,
    create_token,
    get_current_user,
    oauth2_scheme,
    require_role,
    ACCESS_TOKEN_EXPIRE_MINUTES,
    REFRESH_TOKEN_EXPIRE_DAYS,
)
from app.database.database import get_db
from app.models.user import User, AuditLog, LoginLog
from app.core.roles import Role

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


# def set_auth_cookies(
#     response: Response,
#     access_token: str,
#     refresh_token: str,
#     secure: bool = False,           # False in local dev without HTTPS
#     samesite: str = "lax",
# ):
#     # Access token – short lived
#     response.set_cookie(
#         key="access_token",
#         value=access_token,
#         httponly=True,
#         secure=secure,
#         samesite=samesite,
#         max_age=int(ACCESS_TOKEN_EXPIRE_MINUTES * 60),
#         path="/",
#     )
# 
#     # Refresh token – long lived
#     response.set_cookie(
#         key="refresh_token",
#         value=refresh_token,
#         httponly=True,
#         secure=secure,
#         samesite=samesite,
#         max_age=int(REFRESH_TOKEN_EXPIRE_DAYS * 24 * 3600),
#         path="/",
#     )

# 
# @router.post("/login")
# async def login(
#     form: OAuth2PasswordRequestForm = Depends(),
#     db: AsyncSession = Depends(get_db),
#     request: Request = None,
# ):
#     """
#     Authenticate user and return access + refresh tokens in response body
#     (Bearer token style – suitable for API clients, Swagger, Postman, mobile apps, etc.)
#     """
#     ip_address = request.client.host if request else "unknown"
#     user_agent = request.headers.get("user-agent", "unknown")
# 
#     # Find user
#     result = await db.execute(select(User).where(User.username == form.username))
#     user: User | None = result.scalar_one_or_none()
# 
#     # Check credentials
#     success = user is not None and verify_password(form.password, user.hashed_password)
# 
#     # Log attempt (even failed ones)
#     login_log = LoginLog(
#         user_id=user.id if user else None,
#         ip_address=ip_address,
#         user_agent=user_agent,
#         success=success,
#     )
#     db.add(login_log)
# 
#     if not success:
#         await db.commit()
#         raise HTTPException(
#             status_code=status.HTTP_401_UNAUTHORIZED,
#             detail="Incorrect username or password",
#             headers={"WWW-Authenticate": "Bearer"},
#         )
# 
#     # ─── Create tokens ───────────────────────────────────────────────
#     access_token = create_token(
#         subject=str(user.id),
#         role=user.role.value,
#         expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
#         token_type="access",
#     )
# 
#     refresh_token = create_token(
#         subject=str(user.id),
#         role=user.role.value,
#         expires_delta=timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
#         token_type="refresh",
#     )
# 
#     # ─── Log successful login ────────────────────────────────────────
#     db.add(
#         AuditLog(
#             user_id=user.id,
#             action="login_success",
#             details={"ip": ip_address, "user_agent": user_agent},
#         )
#     )
# 
#     await db.commit()
# 
#     # ─── Return tokens + user info in body ───────────────────────────
#     return {
#         "access_token": access_token,
#         "refresh_token": refresh_token,     # optional – remove if you don't want to expose it
#         "token_type": "bearer",
#         "expires_in": int(ACCESS_TOKEN_EXPIRE_MINUTES * 60),  # in seconds
#         "message": "Login successful",
#         "user": {
#             "id": user.id,
#             "username": user.username,
#             "role": user.role.value,
#             "status": "ACTIVE" if user.is_active else "INACTIVE",
#             "created_at": user.created_at.isoformat() if user.created_at else None,
#         }
#     }


@router.post("/refresh")
async def refresh_token(
    refresh_token: str = Body(..., embed=True),  # send as JSON: {"refresh_token": "..."}
    db: AsyncSession = Depends(get_db),
):
    credentials_exception = HTTPException(
        status_code=401,
        detail="Invalid refresh token"
    )

    try:
        payload = jwt.decode(refresh_token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None or payload.get("type") != "refresh":
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise credentials_exception

    new_access_token = create_token(
        subject=str(user.id),
        role=user.role.value,
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
        token_type="access",
    )

    return {
        "access_token": new_access_token,
        "token_type": "bearer",
        "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60
    }

@router.get("/profile")
async def get_profile(current_user: User = Depends(get_current_user)):
    """
    Returns basic information about the authenticated user
    """
    return {
        "id": current_user.id,
        "username": current_user.username,
        "role": current_user.role.value,
        "is_active": current_user.is_active,
        # Add more fields if needed (email, full_name, created_at, etc.)
    }


# Optional: logout (clears cookies)
@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie("access_token", path="/")
    response.delete_cookie("refresh_token", path="/")
    return {"message": "Logged out successfully"}

# ───────────────────────────────────────────────────────────────
# PROTECTED ENDPOINTS - All use Bearer token from core/security.py
# ───────────────────────────────────────────────────────────────

@router.post("/admin")
async def create_admin(
    username: str = Query(..., min_length=3, max_length=50, description="Unique username for the new admin"),
    password: str = Query(..., min_length=8, description="Password for the new admin (min 8 chars)"),
    current_user: User = Depends(require_role(Role.super_admin)),  # Strictly super_admin only
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new admin account - ONLY super_admin is allowed to perform this action.
    
    - Username must be unique
    - Password must be at least 8 characters
    - The new admin will have no parent (top-level admin)
    """
    try:
        # Check if username already exists
        result = await db.execute(select(User).where(User.username == username))
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username is already taken. Please choose a different one."
            )

        # Optional: Add basic password strength check (you can expand this)
        if len(password) < 8:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password must be at least 8 characters long."
            )

        # Hash the password
        hashed_password = get_password_hash(password)

        # Create new admin user
        new_admin = User(
            username=username.strip(),
            hashed_password=hashed_password,
            role=Role.admin,
            parent_admin_id=None,  # Top-level admin (no parent)
            is_active=True
        )

        db.add(new_admin)
        await db.flush()  # Flush to get new_admin.id if needed for audit

        # Audit log entry
        audit = AuditLog(
            user_id=current_user.id,
            action="create_admin",
            details={
                "target_username": username,
                "target_role": Role.admin.value,
                "created_by": current_user.username,
                "ip": request.client.host if request else "unknown"
            }
        )
        db.add(audit)

        await db.commit()
        await db.refresh(new_admin)

        return {
            "message": "Admin created successfully",
            "admin": {
                "id": new_admin.id,
                "username": new_admin.username,
                "role": new_admin.role.value,
                "created_at": new_admin.created_at.isoformat()
            }
        }

    except HTTPException as http_exc:
        await db.rollback()
        raise http_exc
    except Exception as e:
        await db.rollback()
        logger.error(f"Error creating admin: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while creating the admin."
        )

@router.post("/role-user")
async def create_role_user(
    username: str,
    password: str,
    current_user: User = Depends(require_role(Role.admin)),  # Only regular admin
    db: AsyncSession = Depends(get_db),
):
    """Create a new role user - only regular admins allowed"""
    result = await db.execute(select(User).where(User.username == username))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Username already taken")

    hashed_password = get_password_hash(password)
    new_user = User(
        username=username,
        hashed_password=hashed_password,
        role=Role.role_user,
        parent_admin_id=current_user.id,
    )
    db.add(new_user)
    await db.commit()

    db.add(
        AuditLog(
            user_id=current_user.id,
            action="create_role_user",
            details={"target_username": username},
        )
    )
    await db.commit()

    return {"message": "Role user created successfully"}


@router.get("/users/search")
async def search_users(
    q: Optional[str] = Query(None, description="Search term (partial username match)"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(require_role(Role.admin)),  # Admin or higher
    db: AsyncSession = Depends(get_db),
):
    """Search users with pagination"""
    offset = (page - 1) * limit

    query = select(User)

    if current_user.role != Role.super_admin:
        query = query.where(
            (User.parent_admin_id == current_user.id) & (User.role == Role.role_user)
        )

    if q:
        query = query.where(User.username.ilike(f"%{q}%"))

    total_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total = total_result.scalar() or 0

    result = await db.execute(
        query.offset(offset).limit(limit).order_by(User.created_at.desc())
    )
    users = result.scalars().all()

    return {
        "data": [u.__dict__ for u in users],
        "pagination": {
            "total": total,
            "page": page,
            "limit": limit,
            "totalPages": (total + limit - 1) // limit if total > 0 else 0
        }
    }


@router.get("/logs/login")
async def get_role_users_login_logs(
    current_user: User = Depends(require_role(Role.admin)),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """View login logs with pagination"""
    offset = (page - 1) * limit

    query = select(LoginLog)

    if current_user.role != Role.super_admin:
        child_users_result = await db.execute(
            select(User.id).where(User.parent_admin_id == current_user.id)
        )
        child_user_ids = [row[0] for row in child_users_result.all()]

        if not child_user_ids:
            return {
                "data": [],
                "pagination": {"total": 0, "page": page, "limit": limit, "totalPages": 0}
            }

        query = query.where(LoginLog.user_id.in_(child_user_ids))

    total_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total = total_result.scalar() or 0

    result = await db.execute(
        query.offset(offset).limit(limit).order_by(LoginLog.timestamp.desc())
    )
    logs = result.scalars().all()

    return {
        "data": [log.__dict__ for log in logs],
        "pagination": {
            "total": total,
            "page": page,
            "limit": limit,
            "totalPages": (total + limit - 1) // limit if total > 0 else 0
        }
    }


@router.get("/logs/activities")
async def get_role_users_activities(
    current_user: User = Depends(require_role(Role.admin)),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """View activities with pagination"""
    offset = (page - 1) * limit

    query = select(AuditLog)

    if current_user.role != Role.super_admin:
        child_users_result = await db.execute(
            select(User.id).where(User.parent_admin_id == current_user.id)
        )
        child_user_ids = [row[0] for row in child_users_result.all()]

        if not child_user_ids:
            return {
                "data": [],
                "pagination": {"total": 0, "page": page, "limit": limit, "totalPages": 0}
            }

        query = query.where(AuditLog.user_id.in_(child_user_ids))

    total_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total = total_result.scalar() or 0

    result = await db.execute(
        query.offset(offset).limit(limit).order_by(AuditLog.timestamp.desc())
    )
    activities = result.scalars().all()

    return {
        "data": [act.__dict__ for act in activities],
        "pagination": {
            "total": total,
            "page": page,
            "limit": limit,
            "totalPages": (total + limit - 1) // limit if total > 0 else 0
        }
    }

@router.get("/allUsers")
async def get_all_users(
    current_user: User = Depends(require_role(Role.super_admin)),  # Super admin only
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Super admin: Get all users (admins + role users) with pagination & search"""
    offset = (page - 1) * limit

    query = select(User)

    if search:
        query = query.where(
            or_(
                User.username.ilike(f"%{search}%"),
            )
        )

    total_result = await db.execute(select(select(User).subquery().count()))
    total = total_result.scalar() or 0

    result = await db.execute(
        query.offset(offset).limit(limit).order_by(User.created_at.desc())
    )
    users = result.scalars().all()

    return {
        "data": [u.__dict__ for u in users],
        "pagination": {
            "total": total,
            "page": page,
            "limit": limit,
            "totalPages": (total + limit - 1) // limit if total else 0
        }
    }


@router.get("/role_users")
async def get_my_users(
    current_user: User = Depends(require_role(Role.admin)),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Admin: Get only role users under them; Super admin sees all"""
    offset = (page - 1) * limit

    if current_user.role == Role.super_admin:
        query = select(User).where(User.role == Role.role_user)
    else:
        query = select(User).where(
            (User.parent_admin_id == current_user.id) & (User.role == Role.role_user)
        )

    if search:
        query = query.where(User.username.ilike(f"%{search}%"))

    total_result = await db.execute(select(select(query.subquery()).count()))
    total = total_result.scalar() or 0

    result = await db.execute(
        query.offset(offset).limit(limit).order_by(User.created_at.desc())
    )
    users = result.scalars().all()

    return {
        "data": [u.__dict__ for u in users],
        "pagination": {
            "total": total,
            "page": page,
            "limit": limit,
            "totalPages": (total + limit - 1) // limit if total else 0
        }
    }


@router.get("/admin/{admin_id}/logs")
async def get_admin_logs(
    admin_id: str,
    current_user: User = Depends(require_role(Role.super_admin)),  # Super admin only
    log_type: str = Query("activities", regex="^(login|activities)$"),
    db: AsyncSession = Depends(get_db),
):
    """Super admin only: Get logs/activities of a specific admin + their role users"""
    # Find the admin
    admin_result = await db.execute(select(User).where(User.id == admin_id))
    admin = admin_result.scalar_one_or_none()
    if not admin or admin.role != Role.admin:
        raise HTTPException(404, "Admin not found")

    # Get all role users under this admin
    children = await db.execute(
        select(User.id).where(User.parent_admin_id == admin_id)
    )
    child_ids = [row[0] for row in children.all()]

    # Include the admin themselves
    all_ids = [admin_id] + child_ids

    if log_type == "login":
        result = await db.execute(select(LoginLog).where(LoginLog.user_id.in_(all_ids)))
        logs = result.scalars().all()
        return {"logs": [log.__dict__ for log in logs]}
    else:
        result = await db.execute(select(AuditLog).where(AuditLog.user_id.in_(all_ids)))
        activities = result.scalars().all()
        return {"activities": [act.__dict__ for act in activities]}


@router.get("/user/{user_id}/logs")
async def get_user_logs(
    user_id: str,
    current_user: User = Depends(require_role(Role.admin)),
    log_type: str = Query("activities", regex="^(login|activities)$"),
    db: AsyncSession = Depends(get_db),
):
    """Admin: Get logs of a specific role user under them; Super admin can see any"""
    # Check if the target user exists and is a role user
    user_result = await db.execute(select(User).where(User.id == user_id))
    target_user = user_result.scalar_one_or_none()
    if not target_user or target_user.role != Role.role_user:
        raise HTTPException(404, "Role user not found")

    # Permission check
    if current_user.role != Role.super_admin:
        if target_user.parent_admin_id != current_user.id:
            raise HTTPException(403, "You can only view your own role users")

    if log_type == "login":
        result = await db.execute(select(LoginLog).where(LoginLog.user_id == user_id))
        logs = result.scalars().all()
        return {"logs": [log.__dict__ for log in logs]}
    else:
        result = await db.execute(select(AuditLog).where(AuditLog.user_id == user_id))
        activities = result.scalars().all()
        return {"activities": [act.__dict__ for act in activities]}


@router.get("/log/{log_id}")
async def get_login_log_detail(
    log_id: str,
    current_user: User = Depends(require_role(Role.admin)),
    db: AsyncSession = Depends(get_db),
):
    """Get detailed single login log - super admin or owning admin"""
    log_result = await db.execute(select(LoginLog).where(LoginLog.id == log_id))
    log = log_result.scalar_one_or_none()
    if not log:
        raise HTTPException(404, "Log not found")

    if current_user.role != Role.super_admin:
        # Check if this log belongs to one of their role users
        user_result = await db.execute(select(User).where(User.id == log.user_id))
        target_user = user_result.scalar_one_or_none()
        if not target_user or target_user.parent_admin_id != current_user.id:
            raise HTTPException(403, "You can only view your own role users' logs")

    return log.__dict__


@router.get("/activity/{activity_id}")
async def get_activity_detail(
    activity_id: str,
    current_user: User = Depends(require_role(Role.admin)),
    db: AsyncSession = Depends(get_db),
):
    """Get detailed single audit log - super admin or owning admin"""
    act_result = await db.execute(select(AuditLog).where(AuditLog.id == activity_id))
    activity = act_result.scalar_one_or_none()
    if not activity:
        raise HTTPException(404, "Activity not found")

    if current_user.role != Role.super_admin:
        user_result = await db.execute(select(User).where(User.id == activity.user_id))
        target_user = user_result.scalar_one_or_none()
        if not target_user or target_user.parent_admin_id != current_user.id:
            raise HTTPException(403, "You can only view your own role users' activities")

    return activity.__dict__


@router.delete("/user/{user_id}")
async def delete_user(
    user_id: str,
    current_user: User = Depends(require_role(Role.admin)),
    db: AsyncSession = Depends(get_db),
):
    """Delete user - super admin any, admin only their role users"""
    user_result = await db.execute(select(User).where(User.id == user_id))
    target = user_result.scalar_one_or_none()
    if not target:
        raise HTTPException(404, "User not found")

    if current_user.role != Role.super_admin:
        if target.role != Role.role_user or target.parent_admin_id != current_user.id:
            raise HTTPException(403, "You can only delete your own role users")

    await db.delete(target)
    await db.commit()

    return {"message": "User deleted successfully"}


@router.put("/user/{user_id}")
async def update_user(
    user_id: str,
    username: Optional[str] = None,
    password: Optional[str] = None,
    current_user: User = Depends(require_role(Role.admin)),
    db: AsyncSession = Depends(get_db),
):
    """Update user details/password - super admin any, admin only their role users"""
    user_result = await db.execute(select(User).where(User.id == user_id))
    target = user_result.scalar_one_or_none()
    if not target:
        raise HTTPException(404, "User not found")

    if current_user.role != Role.super_admin:
        if target.role != Role.role_user or target.parent_admin_id != current_user.id:
            raise HTTPException(403, "You can only update your own role users")

    if username:
        # Check uniqueness if changing username
        check = await db.execute(select(User).where(User.username == username, User.id != user_id))
        if check.scalar_one_or_none():
            raise HTTPException(400, "Username already taken")
        target.username = username

    if password:
        target.hashed_password = get_password_hash(password)

    await db.commit()

    return {"message": "User updated successfully"}

auth = router