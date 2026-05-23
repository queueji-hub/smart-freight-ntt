import hashlib
from typing import Optional, Dict, Any, List
from database.connection import get_connection

# --- Configuration ---
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
    "cs": {"dashboard": "r", "crm": "rw", "quotation": "rw", "booking": "rw", "shipment": "rw", "billing": "r", "reports": "r"},
    "operation": {"dashboard": "r", "crm": "rw", "quotation": "rw", "booking": "rw", "shipment": "rw", "billing": "r", "reports": "r"},
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

# --- Auth Functions ---
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
    pwd_hash = hash_password(password)
    with get_connection() as conn:
        # ใช้ %s สำหรับ Postgres
        query = "SELECT id, username, full_name, email, role FROM users WHERE username=%s AND password_hash=%s"
        result = conn.execute(query, (username.strip().lower(), pwd_hash)).fetchone()
        return dict(result) if result else None

# --- User Management Functions (ที่ขาดหายไป) ---
def list_users() -> List[Dict]:
    with get_connection() as conn:
        rows = conn.execute("SELECT id, username, full_name, email, role FROM users").fetchall()
        return [dict(row) for row in rows]

def create_user(username, password, role, full_name, email):
    pwd_hash = hash_password(password)
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO users (username, password_hash, role, full_name, email) VALUES (%s, %s, %s, %s, %s)",
            (username.strip().lower(), pwd_hash, role, full_name, email)
        )

def update_user_password(username, new_password):
    pwd_hash = hash_password(new_password)
    with get_connection() as conn:
        conn.execute("UPDATE users SET password_hash = %s WHERE username = %s", (pwd_hash, username.strip().lower()))