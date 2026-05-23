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

def add_milestone(shipment_id: int, code: str, occurred_at=None, 
                  location: str = None, note: str = None, created_by: str = None) -> int:
    """Record a milestone for a shipment."""
    name = MILESTONE_NAMES.get(code, code)
    occurred_at = occurred_at or datetime.now()
    
    with get_connection() as conn:
        cur = conn.execute("""
            INSERT INTO shipment_milestones
            (shipment_id, milestone_code, milestone_name, occurred_at, location, note, created_by)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (shipment_id, code, name, occurred_at, location, note, created_by))
        
        result = cur.fetchone()
        conn.commit()
        return result['id'] if result else 0

def get_milestones(shipment_id: int) -> List[Dict[str, Any]]:
    """Get all milestones for a shipment, ordered by date."""
    with get_connection() as conn:
        return list(conn.execute("""
            SELECT * FROM shipment_milestones
            WHERE shipment_id=%s ORDER BY occurred_at ASC, id ASC
        """, (shipment_id,)).fetchall())

def get_latest_status(shipment_id: int) -> Optional[Dict[str, Any]]:
    """Get the most recent milestone for a shipment efficiently."""
    with get_connection() as conn:
        cursor = conn.execute("""
            SELECT * FROM shipment_milestones
            WHERE shipment_id=%s 
            ORDER BY occurred_at DESC, id DESC LIMIT 1
        """, (shipment_id,))
        return cursor.fetchone()

def delete_milestone(milestone_id: int) -> bool:
    with get_connection() as conn:
        conn.execute("DELETE FROM shipment_milestones WHERE id=%s", (milestone_id,))
        conn.commit()
        return True