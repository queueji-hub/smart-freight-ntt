import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from database.connection import get_connection

SESSION_TIMEOUT_HOURS = 24

def create_session(user_id: int) -> str:
    """Create a new session token."""
    token = secrets.token_urlsafe(32)
    expires = datetime.now() + timedelta(hours=SESSION_TIMEOUT_HOURS)
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO sessions (token, user_id, expires_at) VALUES (%s, %s, %s)",
            (token, user_id, expires)
        )
        conn.commit()
    return token

def get_user_by_token(token: str) -> Optional[Dict[str, Any]]:
    """Validate token and return user info."""
    if not token: return None
    
    with get_connection() as conn:
        # ดึงข้อมูล user และวันหมดอายุ
        row = conn.execute("""
            SELECT s.expires_at, u.id, u.username, u.full_name, u.email, u.role
            FROM sessions s
            JOIN users u ON u.id = s.user_id
            WHERE s.token = %s
        """, (token,)).fetchone()
        
        if not row or row["expires_at"] < datetime.now():
            return None
        
        return {
            "id": row["id"],
            "username": row["username"],
            "full_name": row["full_name"],
            "email": row["email"],
            "role": row["role"],
        }

def delete_session(token: str) -> None:
    """Invalidate a session token (logout)."""
    if not token: return
    with get_connection() as conn:
        conn.execute("DELETE FROM sessions WHERE token=%s", (token,))
        conn.commit()

def cleanup_expired_sessions() -> int:
    """Remove all expired sessions."""
    with get_connection() as conn:
        cur = conn.execute("DELETE FROM sessions WHERE expires_at < %s", (datetime.now(),))
        conn.commit()
        return cur.rowcount