"""Session token management - persists login across full page reloads.

Tokens are stored in DB and passed via URL query param.
This allows HTML <a href> navigation while keeping users logged in.
"""
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from database.connection import get_connection


SESSION_TIMEOUT_HOURS = 24


def _ensure_sessions_table():
    """Create sessions table if it doesn't exist."""
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                token TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                expires_at TIMESTAMP NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id)")


def create_session(user_id: int) -> str:
    """Create a new session token. Returns the token string."""
    _ensure_sessions_table()
    token = secrets.token_urlsafe(32)
    expires = datetime.now() + timedelta(hours=SESSION_TIMEOUT_HOURS)
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO sessions (token, user_id, expires_at) VALUES (?, ?, ?)",
            (token, user_id, expires.isoformat())
        )
    return token


def get_user_by_token(token: str) -> Optional[Dict[str, Any]]:
    """Validate token and return user info. None if invalid/expired."""
    if not token:
        return None
    
    _ensure_sessions_table()
    with get_connection() as conn:
        # Clean up expired sessions occasionally
        try:
            conn.execute(
                "DELETE FROM sessions WHERE expires_at < ?",
                (datetime.now().isoformat(),)
            )
        except Exception:
            pass
        
        try:
            row = conn.execute("""
                SELECT s.expires_at, u.id, u.username, u.full_name, u.email, u.role
                FROM sessions s
                JOIN users u ON u.id = s.user_id
                WHERE s.token = ?
            """, (token,)).fetchone()
        except Exception:
            return None
        
        if not row:
            return None
        
        # Check expiry
        try:
            exp = datetime.fromisoformat(row["expires_at"])
            if exp < datetime.now():
                return None
        except Exception:
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
    if not token:
        return
    _ensure_sessions_table()
    with get_connection() as conn:
        conn.execute("DELETE FROM sessions WHERE token=?", (token,))


def cleanup_expired_sessions() -> int:
    """Remove all expired sessions. Returns number deleted."""
    _ensure_sessions_table()
    with get_connection() as conn:
        cur = conn.execute(
            "DELETE FROM sessions WHERE expires_at < ?",
            (datetime.now().isoformat(),)
        )
        return cur.rowcount
