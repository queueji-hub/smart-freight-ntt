"""Shipment (Job Control Sheet) CRUD operations."""
from typing import List, Dict, Any, Optional
from database.connection import get_connection
from managers.job_number import generate_job_number

SHIPMENT_FIELDS = [
    "booking_id", "booking_no", "customer_id", "customer_name",
    "shipper", "consignee", "notify_party", "brand", "commodity", 
    "combine_commodity", "cargo_type", "full_or_half", "pick_up_date", 
    "stuffing_date", "return_date", "etd", "eta", "container_no", 
    "seal_no", "container_size", "weight_origin", "weight_port", 
    "carrier", "m_vessel", "feeder", "pol", "por", "pod", 
    "final_destination", "transhipment_port", "bl_no", "bl_status", 
    "closing_time", "overnight_trucking", "status", "invoice_no", 
    "customer_paid", "dn_type", "dn_no", "remark", "created_by",
]

def _ensure_table():
    """Ensure the shipments table exists."""
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS shipments (
                id SERIAL PRIMARY KEY,
                job_no TEXT UNIQUE NOT NULL,
                job_type TEXT NOT NULL,
                booking_id TEXT, booking_no TEXT, customer_id INTEGER, customer_name TEXT,
                shipper TEXT, consignee TEXT, notify_party TEXT, brand TEXT, commodity TEXT,
                combine_commodity TEXT, cargo_type TEXT, full_or_half TEXT, pick_up_date DATE,
                stuffing_date DATE, return_date DATE, etd DATE, eta DATE, container_no TEXT,
                seal_no TEXT, container_size TEXT, weight_origin NUMERIC(10,2), weight_port NUMERIC(10,2),
                carrier TEXT, m_vessel TEXT, feeder TEXT, pol TEXT, por TEXT, pod TEXT,
                final_destination TEXT, transhipment_port TEXT, bl_no TEXT, bl_status TEXT,
                closing_time TIMESTAMP, overnight_trucking BOOLEAN, status TEXT, invoice_no TEXT,
                customer_paid BOOLEAN, dn_type TEXT, dn_no TEXT, remark TEXT, created_by TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

def create_shipment(data: Dict[str, Any], company_prefix: str = None) -> str:
    _ensure_table()
    job_type = data["job_type"]
    job_no = generate_job_number(job_type, data.get("etd") or data.get("pick_up_date"), company_prefix)
    
    cols = ["job_no", "job_type"] + SHIPMENT_FIELDS
    values = [job_no, job_type] + [data.get(f) for f in SHIPMENT_FIELDS]
    placeholders = ",".join(["%s"] * len(cols))
    
    with get_connection() as conn:
        conn.execute(f"INSERT INTO shipments ({','.join(cols)}) VALUES ({placeholders})", values)
    return job_no

def update_shipment(job_no: str, updates: Dict[str, Any]) -> bool:
    allowed = [f for f in updates.keys() if f in SHIPMENT_FIELDS]
    if not allowed: return False
    
    set_clause = ", ".join(f"{f}=%s" for f in allowed)
    values = [updates[f] for f in allowed]
    values.append(job_no)
    
    with get_connection() as conn:
        cur = conn.execute(f"UPDATE shipments SET {set_clause}, updated_at=CURRENT_TIMESTAMP WHERE job_no=%s", values)
        return cur.rowcount > 0

def get_shipment(job_no: str) -> Optional[Dict[str, Any]]:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM shipments WHERE job_no=%s", (job_no,)).fetchone()
        return dict(row) if row else None

def list_shipments(job_type: str = None, status: str = None, limit: int = None) -> List[Dict[str, Any]]:
    sql = "SELECT * FROM shipments WHERE 1=1"
    params = []
    if job_type: sql += " AND job_type=%s"; params.append(job_type)
    if status: sql += " AND status=%s"; params.append(status)
    sql += " ORDER BY etd DESC, id DESC"
    if limit: sql += f" LIMIT {int(limit)}"
    
    with get_connection() as conn:
        rows = conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]

def get_dashboard_stats() -> Dict[str, Any]:
    """Aggregated stats for dashboard with safe defaults."""
    with get_connection() as conn:
        # 1. ดึงข้อมูลสถานะและจำนวนงาน
        rows = conn.execute("SELECT status, COUNT(*) as c FROM shipments GROUP BY status").fetchall()
        
        # 2. แปลงข้อมูลเป็น Dict (รองรับทั้ง dict และ tuple)
        stats_data = {}
        for r in rows:
            if isinstance(r, dict):
                status_key = str(r.get('status', 'unknown')).lower()
                stats_data[status_key] = r.get('c', 0)
            else:
                status_key = str(r[0]).lower()
                stats_data[status_key] = r[1]

        # 3. คำนวณยอดรวมและคืนค่าพร้อม Key ที่หน้า Dashboard ต้องการ
        total = sum(stats_data.values())
        return {
            "total": total,
            "proceed": stats_data.get('proceed', 0),
            "pending": stats_data.get('pending', 0),
            "completed": stats_data.get('completed', 0),
            "by_type": [dict(r) for r in conn.execute("SELECT job_type, COUNT(*) as c FROM shipments GROUP BY job_type").fetchall()],
            "by_month": [dict(r) for r in conn.execute("SELECT TO_CHAR(etd, 'YYYY-MM') as ym, COUNT(*) as c FROM shipments WHERE etd IS NOT NULL GROUP BY ym ORDER BY ym").fetchall()]
        }