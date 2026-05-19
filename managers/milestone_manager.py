"""Milestone management for shipment tracking."""
from typing import List, Dict, Any, Optional
from datetime import datetime
from database.connection import get_connection


# Standard milestones for sea export (CargoWise-like codes)
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


def get_standard_milestones(job_type: str) -> List[tuple]:
    """Return the standard milestone template based on job type."""
    if job_type == "SI":
        return STANDARD_MILESTONES_SI
    # Default to SE template for SE/AE/TE/AI/TI
    return STANDARD_MILESTONES_SE


def add_milestone(shipment_id: int, code: str, name: str,
                  occurred_at: Optional[str] = None,
                  note: Optional[str] = None) -> int:
    """Add a milestone to a shipment."""
    with get_connection() as conn:
        cur = conn.execute("""
            INSERT INTO shipment_milestones
            (shipment_id, milestone_code, milestone_name, occurred_at, note)
            VALUES (?, ?, ?, ?, ?)
        """, (shipment_id, code, name, occurred_at, note))
        return cur.lastrowid


def list_milestones(shipment_id: int) -> List[Dict[str, Any]]:
    """List all milestones for a shipment, ordered by occurred_at."""
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT * FROM shipment_milestones
            WHERE shipment_id = ?
            ORDER BY 
              CASE WHEN occurred_at IS NULL THEN 1 ELSE 0 END,
              occurred_at ASC, id ASC
        """, (shipment_id,)).fetchall()
        return [dict(r) for r in rows]


def update_milestone(milestone_id: int, occurred_at: Optional[str] = None,
                     note: Optional[str] = None) -> bool:
    """Update a milestone's timestamp and note."""
    with get_connection() as conn:
        cur = conn.execute("""
            UPDATE shipment_milestones
            SET occurred_at=?, note=?
            WHERE id=?
        """, (occurred_at, note, milestone_id))
        return cur.rowcount > 0


def delete_milestone(milestone_id: int) -> bool:
    with get_connection() as conn:
        cur = conn.execute(
            "DELETE FROM shipment_milestones WHERE id=?", (milestone_id,)
        )
        return cur.rowcount > 0


def init_milestones_for_shipment(shipment_id: int, job_type: str) -> None:
    """Create standard milestone placeholders for a new shipment."""
    with get_connection() as conn:
        # Check if any milestones already exist
        existing = conn.execute(
            "SELECT COUNT(*) FROM shipment_milestones WHERE shipment_id=?",
            (shipment_id,)
        ).fetchone()[0]
        
        if existing > 0:
            return
        
        for code, name_en, _name_th in get_standard_milestones(job_type):
            conn.execute("""
                INSERT INTO shipment_milestones
                (shipment_id, milestone_code, milestone_name, occurred_at)
                VALUES (?, ?, ?, NULL)
            """, (shipment_id, code, name_en))


def get_progress_percentage(shipment_id: int) -> int:
    """Calculate % of completed milestones."""
    with get_connection() as conn:
        total = conn.execute(
            "SELECT COUNT(*) FROM shipment_milestones WHERE shipment_id=?",
            (shipment_id,)
        ).fetchone()[0]
        if total == 0:
            return 0
        completed = conn.execute(
            "SELECT COUNT(*) FROM shipment_milestones "
            "WHERE shipment_id=? AND occurred_at IS NOT NULL",
            (shipment_id,)
        ).fetchone()[0]
        return int(round(completed * 100 / total))
