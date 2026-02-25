#!/usr/bin/env python3
import asyncio
from sqlalchemy import select, delete
from app.database.database import AsyncSessionLocal
from app.models.user import User, Role

async def delete_super_admin():
    confirm = input("This will PERMANENTLY delete the Super Admin. Type 'DELETE' to confirm: ")
    if confirm != "DELETE":
        print("Aborted.")
        return

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).where(User.role == Role.super_admin))
        super_admin = result.scalar_one_or_none()
        if not super_admin:
            print("No Super Admin found.")
            return

        await db.execute(delete(User).where(User.id == super_admin.id))
        await db.commit()
        print("Super Admin deleted.")

if __name__ == "__main__":
    asyncio.run(delete_super_admin())