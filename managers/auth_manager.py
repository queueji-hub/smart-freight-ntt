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
    # ... (โค้ดส่วนต้น)
    pwd_hash = hash_password(password)
    
    # เพิ่มบรรทัดนี้เพื่อ debug (เช็คใน Log ของ Streamlit)
    print(f"DEBUG: username={username}, input_password={password}, calculated_hash={pwd_hash}")

def can(role: str, module: str, action: str = "r") -> bool:
    perms = PERMISSIONS.get(role, {})
    granted = perms.get(module, "")
    if action == "r": return "r" in granted or "w" in granted
    if action == "w": return "w" in granted
    return False

def can_read(role: str, module: str) -> bool: return can(role, module, "r")
def can_write(role: str, module: str) -> bool: return can(role, module, "w")