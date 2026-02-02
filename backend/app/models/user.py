from sqlalchemy import (
    Column,
    String,
    DateTime,
    ForeignKey,
    JSON,
    Boolean,
    Enum,
)
from sqlalchemy.orm import relationship, declarative_base
from datetime import datetime
from sqlalchemy.sql import func
from app.core.roles import Role

from uuid import uuid4  # Use this directly for generating UUID strings
import enum


# Create the declarative base
Base = declarative_base()


class Role(str, enum.Enum):
    super_admin = "super_admin"
    admin = "admin"
    role_user = "role_user"


class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(Enum(Role), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
   

    # Self-referential foreign key using String(36)
    parent_admin_id = Column(String(36), ForeignKey("users.id"), nullable=True)

    # Relationships: self-referential (admin creates users)
    created_users = relationship(
        "User",
        back_populates="creator",
        foreign_keys=[parent_admin_id],  # Explicit foreign key
        remote_side=[id]                 # Tells SQLAlchemy which is the "parent" side
    )
    creator = relationship(
        "User",
        back_populates="created_users",
        remote_side=[parent_admin_id]
    )


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    action = Column(String, nullable=False)
    details = Column(JSON)
    timestamp = Column(DateTime, default=datetime.utcnow)


class LoginLog(Base):
    __tablename__ = "login_logs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"))
    ip_address = Column(String)
    user_agent = Column(String)
    timestamp = Column(DateTime, default=datetime.utcnow)
    success = Column(Boolean)