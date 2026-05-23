import hashlib
from typing import Optional, Dict, Any
from database.connection import get_connection

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
    return hashlib.sha256(password.encode()).hexdigest()

def authenticate(username: str, password: str) -> Optional[Dict[str, Any]]:
    if not username or not password:
        return None
    
    pwd_hash = hash_password(password)
    
    # 1. Debug: เช็กว่า Hash ที่โปรแกรมสร้างขึ้น ตรงกับที่อยู่ใน DB ไหม
    print(f"DEBUG: Attempting login for '{username.strip().lower()}'")
    print(f"DEBUG: Calculated Hash: {pwd_hash}")
    
    with get_connection() as conn:
        with conn.cursor() as cursor:
            # 2. Query ไปที่ฐานข้อมูลเพื่อเช็ก username และ password_hash
            query = "SELECT id, username, full_name, email, role FROM users WHERE username=%s AND password_hash=%s"
            cursor.execute(query, (username.strip().lower(), pwd_hash))
            user = cursor.fetchone()
            
            # 3. ถ้าเจอ User ให้ return ข้อมูล ถ้าไม่เจอ return None
            if user:
                return dict(user) if hasattr(user, 'keys') else user
            
            print(f"DEBUG: No user found with provided credentials.")
            return None

def can(role: str, module: str, action: str = "r") -> bool:
    perms = PERMISSIONS.get(role, {})
    granted = perms.get(module, "")
    if action == "r": return "r" in granted or "w" in granted
    if action == "w": return "w" in granted
    return False

def can_read(role: str, module: str) -> bool: return can(role, module, "r")
def can_write(role: str, module: str) -> bool: return can(role, module, "w")