import bcrypt
from typing import Optional, Dict, Any, List
from database.connection import get_connection

# --- Configuration ---
PERMISSIONS = {
    "admin": {"dashboard": "rw", "crm": "rw", "quotation": "rw", "booking": "rw", "shipment": "rw", "billing": "rw", "reports": "rw", "users": "rw"},
    "sales": {"dashboard": "r", "crm": "rw", "quotation": "rw", "booking": "r", "shipment": "r", "billing": "r", "reports": "r"},
    "cs": {"dashboard": "r", "crm": "rw", "quotation": "rw", "booking": "rw", "shipment": "rw", "billing": "r", "reports": "r"},
    "operation": {"dashboard": "r", "crm": "rw", "quotation": "rw", "booking": "rw", "shipment": "rw", "billing": "r", "reports": "r"},
    "accounting": {"dashboard": "r", "crm": "r", "quotation": "r", "booking": "r", "shipment": "r", "billing": "rw", "reports": "r"},
}

# --- เพิ่มตัวแปร ROLE_LABELS ที่หน้า Dashboard เรียกหา ---
ROLE_LABELS = {
    "admin": "Administrator",
    "sales": "Sales Executive",
    "cs": "Customer Service",
    "operation": "Operations",
    "accounting": "Accounting"
}

# --- Auth Helper Functions ---
def can_read(role: str, module: str) -> bool:
    """ตรวจสอบสิทธิ์การอ่าน (ที่หน้า Dashboard เรียกหา)"""
    return can(role, module, "r")

def can_write(role: str, module: str) -> bool:
    """ตรวจสอบสิทธิ์การเขียน"""
    return can(role, module, "w")

def can(role: str, module: str, action: str = "r") -> bool:
    perms = PERMISSIONS.get(role, {})
    granted = perms.get(module, "")
    if action == "r": return "r" in granted or "w" in granted
    if action == "w": return "w" in granted
    return False

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

dimport bcrypt
from typing import Optional, Dict, Any, List
from database.connection import get_connection

# --- Configuration ---
PERMISSIONS = {
    "admin": {"dashboard": "rw", "crm": "rw", "quotation": "rw", "booking": "rw", "shipment": "rw", "billing": "rw", "reports": "rw", "users": "rw"},
    "sales": {"dashboard": "r", "crm": "rw", "quotation": "rw", "booking": "r", "shipment": "r", "billing": "r", "reports": "r"},
    "cs": {"dashboard": "r", "crm": "rw", "quotation": "rw", "booking": "rw", "shipment": "rw", "billing": "r", "reports": "r"},
    "operation": {"dashboard": "r", "crm": "rw", "quotation": "rw", "booking": "rw", "shipment": "rw", "billing": "r", "reports": "r"},
    "accounting": {"dashboard": "r", "crm": "r", "quotation": "r", "booking": "r", "shipment": "r", "billing": "rw", "reports": "r"},
}

# --- เพิ่มตัวแปร ROLE_LABELS ที่หน้า Dashboard เรียกหา ---
ROLE_LABELS = {
    "admin": "Administrator",
    "sales": "Sales Executive",
    "cs": "Customer Service",
    "operation": "Operations",
    "accounting": "Accounting"
}

# --- Auth Helper Functions ---
def can_read(role: str, module: str) -> bool:
    """ตรวจสอบสิทธิ์การอ่าน (ที่หน้า Dashboard เรียกหา)"""
    return can(role, module, "r")

def can_write(role: str, module: str) -> bool:
    """ตรวจสอบสิทธิ์การเขียน"""
    return can(role, module, "w")

def can(role: str, module: str, action: str = "r") -> bool:
    perms = PERMISSIONS.get(role, {})
    granted = perms.get(module, "")
    if action == "r": return "r" in granted or "w" in granted
    if action == "w": return "w" in granted
    return False

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(password: str, hashed: str) -> bool:
    try:
        # กันค่า None หรือค่าว่าง
        if not hashed:
            print("❌ Password hash is empty")
            return False

        # ถ้า PostgreSQL คืน bytes มา
        if isinstance(hashed, bytes):
            hashed_bytes = hashed
        else:
            hashed_bytes = hashed.encode("utf-8")

        return bcrypt.checkpw(
            password.encode("utf-8"),
            hashed_bytes
        )

    except Exception as e:
        print(f"❌ Password verify failed: {e}")
        return False

# --- Database Auth Logic ---
def authenticate(username: str, password: str) -> Optional[Dict[str, Any]]:
    with get_connection() as conn:
        query = "SELECT id, username, password_hash, full_name, email, role FROM users WHERE username=%s"
        cursor = conn.execute(query, (username.strip().lower(),))
        user = cursor.fetchone()
        
        if user and verify_password(password, user['password_hash']):
            user_data = dict(user)
            del user_data['password_hash']
            return user_data
    return None

def list_users() -> List[Dict]:
    with get_connection() as conn:
        # ใช้ fetchall() เพื่อดึงผลลัพธ์มาเป็น List
        return [dict(r) for r in conn.execute("SELECT id, username, full_name, email, role FROM users").fetchall()]

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

# --- Database Auth Logic ---
def authenticate(username: str, password: str) -> Optional[Dict[str, Any]]:
    with get_connection() as conn:
        query = "SELECT id, username, password_hash, full_name, email, role FROM users WHERE username=%s"
        cursor = conn.execute(query, (username.strip().lower(),))
        user = cursor.fetchone()
        
        if user and verify_password(password, user['password_hash']):
            user_data = dict(user)
            del user_data['password_hash']
            return user_data
    return None

def list_users() -> List[Dict]:
    with get_connection() as conn:
        # ใช้ fetchall() เพื่อดึงผลลัพธ์มาเป็น List
        return [dict(r) for r in conn.execute("SELECT id, username, full_name, email, role FROM users").fetchall()]

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