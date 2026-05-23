import bcrypt
from typing import Optional, Dict, Any, List
from database.connection import get_connection

# --- Configuration คงเดิมตามที่คุณวางแผนไว้ ---
PERMISSIONS = {
    "admin": {"dashboard": "rw", "crm": "rw", "quotation": "rw", "booking": "rw", "shipment": "rw", "billing": "rw", "reports": "rw", "users": "rw"},
    "sales": {"dashboard": "r", "crm": "rw", "quotation": "rw", "booking": "r", "shipment": "r", "billing": "r", "reports": "r"},
    "cs": {"dashboard": "r", "crm": "rw", "quotation": "rw", "booking": "rw", "shipment": "rw", "billing": "r", "reports": "r"},
    "operation": {"dashboard": "r", "crm": "rw", "quotation": "rw", "booking": "rw", "shipment": "rw", "billing": "r", "reports": "r"},
    "accounting": {"dashboard": "r", "crm": "r", "quotation": "r", "booking": "r", "shipment": "r", "billing": "rw", "reports": "r"},
}

# --- Auth Functions ---
def hash_password(password: str) -> str:
    """Hash password ด้วย bcrypt (ปลอดภัยกว่า SHA-256)"""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(password: str, hashed: str) -> bool:
    """ตรวจสอบ password เทียบกับ hash"""
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

def can(role: str, module: str, action: str = "r") -> bool:
    perms = PERMISSIONS.get(role, {})
    granted = perms.get(module, "")
    if action == "r": return "r" in granted or "w" in granted
    if action == "w": return "w" in granted
    return False

# --- Auth Logic ---
def authenticate(username: str, password: str) -> Optional[Dict[str, Any]]:
    with get_connection() as conn:
        query = "SELECT id, username, password_hash, full_name, email, role FROM users WHERE username=%s"
        cursor = conn.execute(query, (username.strip().lower(),))
        user = cursor.fetchone()
        
        if user and verify_password(password, user['password_hash']):
            # ส่งคืนข้อมูล user แต่ไม่ส่ง password_hash กลับไป
            user_data = dict(user)
            del user_data['password_hash']
            return user_data
    return None

# --- User Management ---
def list_users() -> List[Dict]:
    with get_connection() as conn:
        return list(conn.execute("SELECT id, username, full_name, email, role FROM users").fetchall())

def create_user(username, password, role, full_name, email):
    pwd_hash = hash_password(password)
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO users (username, password_hash, role, full_name, email) VALUES (%s, %s, %s, %s, %s)",
            (username.strip().lower(), pwd_hash, role, full_name, email)
        )
        conn.commit()

def update_user_password(username, new_password):
    pwd_hash = hash_password(new_password)
    with get_connection() as conn:
        conn.execute("UPDATE users SET password_hash = %s WHERE username = %s", (pwd_hash, username.strip().lower()))
        conn.commit()