from typing import List, Dict, Any, Optional
from database.connection import get_connection

# Standard milestones (Keeping as constants)
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

def add_milestone(shipment_id: int, code: str, name: str, occurred_at: Optional[str] = None, note: Optional[str] = None) -> int:
    with get_connection() as conn:
        cur = conn.execute("""
            INSERT INTO shipment_milestones (shipment_id, milestone_code, milestone_name, occurred_at, note)
            VALUES (%s, %s, %s, %s, %s) RETURNING id
        """, (shipment_id, code, name, occurred_at, note))
        conn.commit()
        return cur.fetchone()['id']

def update_milestone(milestone_id: int, occurred_at: Optional[str] = None, note: Optional[str] = None) -> bool:
    with get_connection() as conn:
        cur = conn.execute("""
            UPDATE shipment_milestones SET occurred_at=%s, note=%s WHERE id=%s
        """, (occurred_at, note, milestone_id))
        conn.commit()
        return cur.rowcount > 0

def init_milestones_for_shipment(shipment_id: int, job_type: str) -> None:
    with get_connection() as conn:
        # ใช้ fetchone เพื่อเช็คว่ามีอยู่แล้วหรือยัง
        row = conn.execute("SELECT COUNT(*) as cnt FROM shipment_milestones WHERE shipment_id=%s", (shipment_id,)).fetchone()
        if row['cnt'] > 0: return
        
        milestones = STANDARD_MILESTONES_SI if job_type == "SI" else STANDARD_MILESTONES_SE
        for code, name_en, name_th in milestones:
            conn.execute("""
                INSERT INTO shipment_milestones (shipment_id, milestone_code, milestone_name, occurred_at)
                VALUES (%s, %s, %s, NULL)
            """, (shipment_id, code, f"{name_en} ({name_th})"))
        conn.commit()

def get_progress_percentage(shipment_id: int) -> int:
    with get_connection() as conn:
        row = conn.execute("""
            SELECT 
                COUNT(*) as total,
                COUNT(*) FILTER (WHERE occurred_at IS NOT NULL) as completed
            FROM shipment_milestones WHERE shipment_id=%s
        """, (shipment_id,)).fetchone()
        
        if row['total'] == 0: return 0
        return int(round(row['completed'] * 100 / row['total']))