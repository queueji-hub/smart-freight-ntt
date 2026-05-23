"""User authentication and authorization management."""
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

# --- Internal Table Setup ---
def _ensure_users_table():
    """Ensure the users table exists with correct schema."""
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                full_name TEXT,
                email TEXT,
                role TEXT DEFAULT 'sales',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

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
    _ensure_users_table()
    pwd_hash = hash_password(password)
    with get_connection() as conn:
        query = "SELECT id, username, full_name, email, role FROM users WHERE username=%s AND password_hash=%s"
        result = conn.execute(query, (username.strip().lower(), pwd_hash)).fetchone()
        
    if not result: return None
    return dict(result) if hasattr(result, 'keys') else {k: v for k, v in zip(['id', 'username', 'full_name', 'email', 'role'], result)}

# --- User Management Functions ---
def list_users() -> List[Dict]:
    _ensure_users_table()
    with get_connection() as conn:
        rows = conn.execute("SELECT id, username, full_name, email, role FROM users").fetchall()
        return [dict(r) if hasattr(r, 'keys') else {k: v for k, v in zip(['id', 'username', 'full_name', 'email', 'role'], r)} for r in rows]

def create_user(username, password, role, full_name, email):
    _ensure_users_table()
    pwd_hash = hash_password(password)
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO users (username, password_hash, role, full_name, email) VALUES (%s, %s, %s, %s, %s)",
            (username.strip().lower(), pwd_hash, role, full_name, email)
        )

def update_user_password(username, new_password):
    _ensure_users_table()
    pwd_hash = hash_password(new_password)
    with get_connection() as conn:
        conn.execute("UPDATE users SET password_hash = %s WHERE username = %s", (pwd_hash, username.strip().lower()))