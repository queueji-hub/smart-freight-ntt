import hashlib
from typing import Optional, Dict, Any
from database.connection import get_connection

# ... (Include your PERMISSIONS and ROLE_LABELS dictionaries here as before) ...

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def can(role: str, module: str, action: str = "r") -> bool:
    perms = PERMISSIONS.get(role, {})
    granted = perms.get(module, "")
    if action == "r": return "r" in granted or "w" in granted
    if action == "w": return "w" in granted
    return False

def can_read(role: str, module: str) -> bool:
    return can(role, module, "r")

def can_write(role: str, module: str) -> bool:
    return can(role, module, "w")

def authenticate(username: str, password: str) -> Optional[Dict[str, Any]]:
    # Clear the logic to ensure it's not crashing here
    pwd_hash = hash_password(password)
    with get_connection() as conn:
        with conn.cursor() as cursor:
            # Note: Ensure your database table is "users"
            query = "SELECT id, username, full_name, email, role FROM users WHERE username=%s AND password_hash=%s"
            cursor.execute(query, (username.strip().lower(), pwd_hash))
            user = cursor.fetchone()
            return dict(user) if user else None