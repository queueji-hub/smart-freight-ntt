"""Authentication & Role-Based Access Control."""
import hashlib
from typing import Optional, Dict, Any
from database.connection import get_connection


# ===== Role Permissions =====
# CS and Operation share identical permissions - they form the "ops team"
_OPS_PERMS = {
    "dashboard": "r", "crm": "rw", "quotation": "rw",
    "booking": "rw", "shipment": "rw", "billing": "r",
    "reports": "r",
}

PERMISSIONS = {
    "admin": {
        "dashboard": "rw", "crm": "rw", "quotation": "rw",
        "booking": "rw", "shipment": "rw", "billing": "rw",
        "reports": "rw", "users": "rw",
    },
    "sales": {
        "dashboard": "r", "crm": "rw", "quotation": "rw",
        "booking": "r", "shipment": "r", "billing": "r",
        "reports": "r",
    },
    "cs": _OPS_PERMS,
    "operation": _OPS_PERMS,
    "accounting": {
        "dashboard": "r", "crm": "r", "quotation": "r",
        "booking": "r", "shipment": "r", "billing": "rw",
        "reports": "r",
    },
}

ROLE_LABELS = {
    "admin": "👑 Admin",
    "sales": "💼 Sales",
    "cs": "📞 Customer Service",
    "operation": "🚢 Operation",
    "accounting": "💰 Accounting",
}


def hash_password(password: str) -> str:
    """Simple SHA256 hash. For production use bcrypt/argon2."""
    return hashlib.sha256(password.encode()).hexdigest()


def authenticate(username: str, password: str) -> Optional[Dict[str, Any]]:
    """Verify username/password. Returns user dict or None."""
    if not username or not password:
        return None
    
    pwd_hash = hash_password(password)
    with get_connection() as conn:
        with conn.cursor() as cursor:  # 👈 ใช้ cursor เสมอ
            # Try with is_active filter first; fall back if column missing
            try:
                # 👈 ปรับเครื่องหมายเงื่อนไขเป็น %s สำหรับ PostgreSQL
                cursor.execute(
                    "SELECT id, username, full_name, email, role FROM users "
                    "WHERE username=%s AND password_hash=%s AND is_active=1",
                    (username.strip().lower(), pwd_hash)
                )
                row = cursor.fetchone()
            except Exception:
                # 👈 ปรับเครื่องหมายเงื่อนไขเป็น %s สำหรับ PostgreSQL
                cursor.execute(
                    "SELECT id, username, full_name, email, role FROM users "
                    "WHERE username=%s AND password_hash=%s",
                    (username.strip().lower(), pwd_hash)
                )
                row = cursor.fetchone()
    
    return dict(row) if row else None


def can(role: str, module: str, action: str = "r") -> bool:
    """Check permission. action: 'r' (read) or 'w' (write).
    'rw' permission allows both read and write."""
    perms = PERMISSIONS.get(role, {})
    granted = perms.get(module, "")
    if action == "r":
        return "r" in granted or "w" in granted
    if action == "w":
        return "w" in granted
    return False


def can_read(role: str, module: str) -> bool:
    return can(role, module, "r")


def can_write(role: str, module: str) -> bool:
    return can(role, module, "w")


def list_users() -> list:
    """Return all users."""
    with get_connection() as conn:
        with conn.cursor() as cursor:  # 👈 यूज़ cursor
            cursor.execute(
                "SELECT id, username, full_name, email, role, is_active, created_at "
                "FROM users ORDER BY username"
            )
            rows = cursor.fetchall()
    return [dict(r) for r in rows]


def create_user(username: str, password: str, full_name: str,
                email: str, role: str) -> int:
    """Create a new user. Returns the new user id."""
    if role not in PERMISSIONS:
        raise ValueError(f"Invalid role: {role}")
    
    pwd_hash = hash_password(password)
    with get_connection() as conn:
        with conn.cursor() as cursor:  # 👈 ใช้ cursor และเปลี่ยน ? เป็น %s
            cursor.execute(
                "INSERT INTO users (username, password_hash, full_name, email, role) "
                "VALUES (%s,%s,%s,%s,%s) RETURNING id", # 👈 ใช้ RETURNING id สไตล์ PostgreSQL
                (username.strip().lower(), pwd_hash, full_name, email, role)
            )
            # ดึงค่า id ที่เพิ่ง Insert สำเร็จออกมา
            new_id = cursor.fetchone()["id"] if hasattr(cursor, "fetchone") else cursor.fetchone()[0]
            conn.commit() # บันทึกการเปลี่ยนแปลงลงฐานข้อมูลหลัก
            return new_id


def update_user_password(user_id: int, new_password: str) -> bool:
    """Change user password."""
    pwd_hash = hash_password(new_password)
    with get_connection() as conn:
        with conn.cursor() as cursor:  # 👈 ใช้ cursor และเปลี่ยน ? เป็น %s
            cursor.execute("UPDATE users SET password_hash=%s WHERE id=%s",
                           (pwd_hash, user_id))
            conn.commit()
    return True


def log_activity(user_id: int, username: str, action: str,
                 entity_type: str = None, entity_id: str = None,
                 details: str = None) -> None:
    """Record user activity."""
    with get_connection() as conn:
        with conn.cursor() as cursor:  # 👈 ใช้ cursor และเปลี่ยน ? เป็น %s
            cursor.execute(
                "INSERT INTO activity_logs (user_id, username, action, "
                "entity_type, entity_id, details) VALUES (%s,%s,%s,%s,%s,%s)",
                (user_id, username, action, entity_type, entity_id, details)
            )
            conn.commit()