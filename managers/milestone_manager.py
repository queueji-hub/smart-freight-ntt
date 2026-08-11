from managers.tenant_context import get_current_tenant_id
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

def add_milestone(shipment_id: int, job_no: str, code: str, name: str, event_date: Optional[str] = None, location: Optional[str] = None, remark: Optional[str] = None) -> int:
    tenant_id = get_current_tenant_id()
    if not shipment_id and job_no:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT id FROM shipments WHERE job_no = %s AND tenant_id = %s", (job_no, tenant_id))
                row = cur.fetchone()
                if row:
                    shipment_id = row['id']

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO shipment_milestones (shipment_id, tenant_id, milestone_code, milestone_name, planned_date, actual_date, remarks, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING id
            """, (shipment_id, tenant_id, code, name, event_date, event_date, f"{location} - {remark}" if location else remark, "Completed" if event_date else "Pending"))
            row = cur.fetchone()
            conn.commit()
            return row['id'] if row else None

def update_milestone(milestone_id: int, event_date: Optional[str] = None, location: Optional[str] = None, remark: Optional[str] = None) -> bool:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE shipment_milestones SET actual_date=%s, remarks=%s, status=%s WHERE id=%s
            """, (event_date, f"{location} - {remark}" if location else remark, "Completed" if event_date else "Pending", milestone_id))
            conn.commit()
            return cur.rowcount > 0

def list_milestones(job_no: str) -> List[Dict]:
    tenant_id = get_current_tenant_id()
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT sm.*
                FROM shipment_milestones sm
                JOIN shipments s ON sm.shipment_id = s.id
                WHERE s.job_no = %s AND s.tenant_id = %s
                ORDER BY sm.planned_date ASC, sm.id ASC
            """, (job_no, tenant_id))
            return [dict(r) for r in cur.fetchall()]

def delete_milestone(milestone_id: int, job_no: str) -> bool:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                DELETE FROM shipment_milestones WHERE id=%s
            """, (milestone_id,))
            conn.commit()
            return cur.rowcount > 0

def init_milestones_for_shipment(shipment_id: int, job_no: str, job_type: str) -> None:
    tenant_id = get_current_tenant_id()
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) as cnt FROM shipment_milestones WHERE shipment_id=%s AND tenant_id=%s", (shipment_id, tenant_id))
            row = cur.fetchone()
            if row and row['cnt'] > 0: return
            
            milestones = STANDARD_MILESTONES_SI if job_type == "SI" else STANDARD_MILESTONES_SE
            for code, name_en, name_th in milestones:
                cur.execute("""
                    INSERT INTO shipment_milestones (shipment_id, tenant_id, milestone_code, milestone_name, status)
                    VALUES (%s, %s, %s, %s, %s)
                """, (shipment_id, tenant_id, code, f"{name_en} ({name_th})", "Pending"))
            conn.commit()

def get_progress_percentage(shipment_id: int) -> int:
    tenant_id = get_current_tenant_id()
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN actual_date IS NOT NULL THEN 1 ELSE 0 END) as completed
                FROM shipment_milestones WHERE shipment_id=%s AND tenant_id=%s
            """, (shipment_id, tenant_id))
            row = cur.fetchone()
            
            if not row or row['total'] == 0: return 0
            completed = row['completed'] or 0
            return int(round(completed * 100 / row['total']))