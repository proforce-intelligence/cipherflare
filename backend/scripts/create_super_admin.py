#!/usr/bin/env python3
"""
Automatically create a super admin user if none exists.
Run on startup.
"""

import asyncio
import os

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models.user import User, Role, Base
from app.auth import get_password_hash
from app.database.database import engine  # This should exist — points to your async engine


# Default credentials — CHANGE IN PRODUCTION!
SUPER_ADMIN_USERNAME = "superadmin"
SUPER_ADMIN_PASSWORD = "SuperSecurePass123!"  # Change this after first login


async def create_super_admin_if_not_exists():
    # Ensure tables are created
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("[✓] Database tables ensured/created")

    async_session = async_sessionmaker(engine, expire_on_commit=False)
    async with async_session() as session:
        async with session.begin():
            # Check if super admin exists
            result = await session.execute(
                select(User).where(User.role == Role.super_admin)
            )
            if result.scalar_one_or_none():
                print("[✓] Super admin already exists. Skipping creation.")
                return

            # Create super admin
            hashed = get_password_hash(SUPER_ADMIN_PASSWORD)
            super_admin = User(
                username=SUPER_ADMIN_USERNAME,
                hashed_password=hashed,
                role=Role.super_admin,
                parent_admin_id=None,
                is_active=True,
            )
            session.add(super_admin)

        # Commit outside the nested begin() if needed
        await session.commit()
        print("[✓] Super admin created successfully!")
        print(f"    Username: {SUPER_ADMIN_USERNAME}")
        print(f"    Password: {SUPER_ADMIN_PASSWORD}")
        print("    → Login at http://localhost:8000/docs → POST /api/v1/auth/login")


if __name__ == "__main__":
    asyncio.run(create_super_admin_if_not_exists())



