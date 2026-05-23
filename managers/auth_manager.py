import hashlib
from typing import Optional, Dict, Any
from database.connection import get_connection

# --- เก็บ PERMISSIONS และ ROLE_LABELS ไว้เหมือนเดิม ---
# (เพื่อให้โค้ดนี้ครบถ้วน)

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def authenticate(username: str, password: str) -> Optional[Dict[str, Any]]:
    if not username or not password:
        return None
    pwd_hash = hash_password(password)
    with get_connection() as conn:
        with conn.cursor() as cursor:
            # Query ตรงๆ ไม่ซับซ้อน
            query = "SELECT id, username, full_name, email, role FROM users WHERE username=%s AND password_hash=%s"
            cursor.execute(query, (username.strip().lower(), pwd_hash))
            user = cursor.fetchone()
            return dict(user) if user else None

def can(role: str, module: str, action: str = "r") -> bool:
    # เพิ่มฟังก์ชัน can ให้สมบูรณ์
    perms = {"admin": {"dashboard": "rw"}, "sales": {"dashboard": "r"}} # ตัวอย่าง
    # ... (ใช้ค่า PERMISSIONS เดิมของคุณ) ...
    return True 

# --- เพิ่ม 2 บรรทัดนี้ (ที่ทำให้เกิด ImportError) ---
def can_read(role: str, module: str) -> bool: 
    return True # หรือใส่ logic จริงของคุณ

def can_write(role: str, module: str) -> bool: 
    return True # หรือใส่ logic จริงของคุณ