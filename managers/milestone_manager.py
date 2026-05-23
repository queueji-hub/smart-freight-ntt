"""Milestone management for shipment tracking."""
from typing import List, Dict, Any, Optional
from database.connection import get_connection

# Standard milestones (remains same)
STANDARD_MILESTONES_SE = [
    ("BKD", "Booking Confirmed", "การจองยืนยันแล้ว"),
    ("PUC", "Pick-up Container", "รับตู้"),
    ("STF", "Stuffed at Origin", "บรรจุตู้สินค้า"),
    ("RTN", "Container Returned", "คืนตู้ที่ลานเรือ"),
    ("CCL", "Customs Cleared", "ผ่านพิธีการศุลกากร"),
    ("ETD", "Vessel Departed", "เรือออกจากท่าต้นทาง"),
    ("ITT", "In Transit", "อยู่ระหว่างขนส่ง"),
    ("ETA", "Vessel Arrived", "เรือถึงท่าปลายทาง"),
    ("DLV", "Delivered", "ส่งมอบลูกค้าแล้ว"),
]

STANDARD_MILESTONES_SI = [
    ("BKD", "Booking Confirmed", "การจองยืนยันแล้ว"),
    ("ETD", "Vessel Departed Origin", "เรือออกจากท่าต้นทาง"),
    ("ITT", "In Transit", "อยู่ระหว่างขนส่ง"),
    ("ETA", "Vessel Arrived Thailand", "เรือถึงท่าไทย"),
    ("DSC", "Container Discharged", "เปิดตู้ที่ลานเรือ"),
    ("CCL", "Customs Cleared", "ผ่านพิธีการศุลกากร"),
    ("PUC", "Container Pick-up", "รับตู้จากท่า"),
    ("DLV", "Delivered to Consignee", "ส่งมอบลูกค้าแล้ว"),
]

def _ensure_table():
    """Ensure shipment_milestones table exists."""
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS shipment_milestones (
                id SERIAL PRIMARY KEY,
                shipment_id INTEGER NOT NULL,
                milestone_code TEXT NOT NULL,
                milestone_name TEXT NOT NULL,
                occurred_at TIMESTAMP,
                note TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

def get_standard_milestones(job_type: str) -> List[tuple]:
    return STANDARD_MILESTONES_SI if job_type == "SI" else STANDARD_MILESTONES_SE

def add_milestone(shipment_id: int, code: str, name: str, occurred_at: Optional[str] = None, note: Optional[str] = None) -> int:
    _ensure_table()
    with get_connection() as conn:
        cur = conn.execute("""
            INSERT INTO shipment_milestones (shipment_id, milestone_code, milestone_name, occurred_at, note)
            VALUES (%s, %s, %s, %s, %s) RETURNING id
        """, (shipment_id, code, name, occurred_at, note))
        return cur.fetchone()[0]

def list_milestones(shipment_id: int) -> List[Dict[str, Any]]:
    _ensure_table()
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT * FROM shipment_milestones
            WHERE shipment_id = %s
            ORDER BY (occurred_at IS NULL), occurred_at ASC, id ASC
        """, (shipment_id,)).fetchall()
        return [dict(r) for r in rows]

def update_milestone(milestone_id: int, occurred_at: Optional[str] = None, note: Optional[str] = None) -> bool:
    _ensure_table()
    with get_connection() as conn:
        cur = conn.execute("""
            UPDATE shipment_milestones SET occurred_at=%s, note=%s WHERE id=%s
        """, (occurred_at, note, milestone_id))
        return cur.rowcount > 0

def delete_milestone(milestone_id: int) -> bool:
    _ensure_table()
    with get_connection() as conn:
        cur = conn.execute("DELETE FROM shipment_milestones WHERE id=%s", (milestone_id,))
        return cur.rowcount > 0

def init_milestones_for_shipment(shipment_id: int, job_type: str) -> None:
    _ensure_table()
    with get_connection() as conn:
        existing = conn.execute("SELECT COUNT(*) FROM shipment_milestones WHERE shipment_id=%s", (shipment_id,)).fetchone()[0]
        if existing > 0: return
        
        for code, name_en, _name_th in get_standard_milestones(job_type):
            conn.execute("""
                INSERT INTO shipment_milestones (shipment_id, milestone_code, milestone_name, occurred_at)
                VALUES (%s, %s, %s, NULL)
            """, (shipment_id, code, name_en))

def get_progress_percentage(shipment_id: int) -> int:
    _ensure_table()
    with get_connection() as conn:
        total = conn.execute("SELECT COUNT(*) FROM shipment_milestones WHERE shipment_id=%s", (shipment_id,)).fetchone()[0]
        if total == 0: return 0
        completed = conn.execute("SELECT COUNT(*) FROM shipment_milestones WHERE shipment_id=%s AND occurred_at IS NOT NULL", (shipment_id,)).fetchone()[0]
        return int(round(completed * 100 / total))