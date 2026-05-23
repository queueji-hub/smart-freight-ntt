"""Container tracking - milestones for container movements."""
from datetime import datetime
from typing import List, Dict, Any, Optional
from database.connection import get_connection

# Standard container milestones
MILESTONES = [
    ("BKD", "Booked", "📋"),
    ("CY_RCV", "Empty Container Received at CY", "📦"),
    ("STUFF", "Stuffing / Loading at Shipper", "🚚"),
    ("CY_RTN", "Loaded Container Returned to CY", "🏭"),
    ("LOAD", "Loaded on Vessel", "🚢"),
    ("DEP", "Vessel Departed POL", "⚓"),
    ("ARR", "Vessel Arrived POD", "🛳️"),
    ("DISC", "Discharged at POD", "📤"),
    ("CUST", "Customs Cleared", "✅"),
    ("DEL", "Delivered to Consignee", "🎯"),
    ("EMPTY", "Empty Returned", "♻️"),
]

MILESTONE_NAMES = {code: name for code, name, _ in MILESTONES}
MILESTONE_ICONS = {code: icon for code, _, icon in MILESTONES}

def _ensure_table():
    """Create shipment_milestones table if missing."""
    with get_connection() as conn:
        # 🟢 แก้ไข: ใช้ SERIAL PRIMARY KEY
        conn.execute("""
            CREATE TABLE IF NOT EXISTS shipment_milestones (
                id SERIAL PRIMARY KEY,
                shipment_id INTEGER NOT NULL,
                milestone_code TEXT NOT NULL,
                milestone_name TEXT NOT NULL,
                occurred_at TIMESTAMP,
                location TEXT,
                note TEXT,
                created_by TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

def add_milestone(shipment_id: int, code: str,
                  occurred_at=None, location: str = None,
                  note: str = None, created_by: str = None) -> int:
    """Record a milestone for a shipment."""
    _ensure_table()
    name = MILESTONE_NAMES.get(code, code)
    
    if occurred_at is None:
        occurred_at = datetime.now()
    
    with get_connection() as conn:
        # 🟢 แก้ไข: เปลี่ยน ? เป็น %s และใช้ RETURNING id ของ Postgres
        cur = conn.execute("""
            INSERT INTO shipment_milestones
            (shipment_id, milestone_code, milestone_name, occurred_at, location, note, created_by)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (shipment_id, code, name, occurred_at, location, note, created_by))
        
        result = cur.fetchone()
        return result[0] if result else 0

def get_milestones(shipment_id: int) -> List[Dict[str, Any]]:
    """Get all milestones for a shipment, ordered by date."""
    _ensure_table()
    with get_connection() as conn:
        # 🟢 แก้ไข: เปลี่ยน ? เป็น %s
        rows = conn.execute("""
            SELECT * FROM shipment_milestones
            WHERE shipment_id=%s ORDER BY occurred_at ASC, id ASC
        """, (shipment_id,)).fetchall()
    return [dict(r) for r in rows]

def delete_milestone(milestone_id: int) -> bool:
    _ensure_table()
    with get_connection() as conn:
        # 🟢 แก้ไข: เปลี่ยน ? เป็น %s
        cur = conn.execute(
            "DELETE FROM shipment_milestones WHERE id=%s", (milestone_id,))
        return cur.rowcount > 0

def get_latest_status(shipment_id: int) -> Optional[Dict[str, Any]]:
    """Get the most recent milestone for a shipment."""
    milestones = get_milestones(shipment_id)
    return milestones[-1] if milestones else None