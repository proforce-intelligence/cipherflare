# app/core/roles.py
from enum import Enum

class Role(str, Enum):
    super_admin = "super_admin"      # Full system control
    admin       = "admin"            # Manage monitors, alerts, own users
    role_user   = "role_user"        # Standard monitoring users
    viewer      = "viewer"           # Read-only access