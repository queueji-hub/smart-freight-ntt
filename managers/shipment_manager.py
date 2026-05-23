from typing import List, Dict, Any, Optional
from database.connection import get_connection
from managers.job_number import generate_job_number

# ระบุ Fields ทั้งหมดที่ตาราง shipments ของคุณมี เพื่อป้องกัน SQL Injection
SHIPMENT_FIELDS = [
    "status", "job_type", "booking_no", "customer_name", "shipper", 
    "consignee", "cargo_type", "carrier", "pol", "pod", "etd", "eta", 
    "bl_no", "invoice_no", "customer_paid", "remark", "created_by"
]

def _ensure_table():
    """สร้างตารางถ้ายังไม่มี เพื่อป้องกัน Error เวลา Query"""
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS shipments (
                id SERIAL PRIMARY KEY,
                job_no TEXT UNIQUE NOT NULL,
                status TEXT DEFAULT 'Proceed',
                job_type TEXT,
                booking_no TEXT,
                customer_name TEXT,
                shipper TEXT,
                consignee TEXT,
                cargo_type TEXT,
                carrier TEXT,
                pol TEXT,
                pod TEXT,
                etd DATE,
                eta DATE,
                bl_no TEXT,
                invoice_no TEXT,
                customer_paid INTEGER DEFAULT 0,
                remark TEXT,
                created_by TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()

def create_shipment(data: Dict[str, Any], company_prefix: str = None) -> str:
    """Create a shipment record."""
    job_type = data.get("job_type", "SE")
    job_no = generate_job_number(
        job_type, data.get("etd") or data.get("pick_up_date"), company_prefix
    )
    
    cols = ["job_no", "job_type"] + [f for f in SHIPMENT_FIELDS if f in data]
    placeholders = ",".join(["%s"] * len(cols))
    values = [job_no, job_type] + [data.get(f) for f in SHIPMENT_FIELDS if f in data]
    
    with get_connection() as conn:
        conn.execute(f"INSERT INTO shipments ({','.join(cols)}) VALUES ({placeholders})", values)
        conn.commit()
    return job_no

def update_shipment(job_no: str, updates: Dict[str, Any]) -> bool:
    """Update shipment and ensure changes are committed."""
    allowed = [f for f in updates.keys() if f in SHIPMENT_FIELDS]
    if not allowed: return False
    
    set_clause = ", ".join([f"{f}=%s" for f in allowed]) + ", updated_at=CURRENT_TIMESTAMP"
    values = [updates[f] for f in allowed] + [job_no]
    
    with get_connection() as conn:
        cur = conn.execute(f"UPDATE shipments SET {set_clause} WHERE job_no=%s", values)
        conn.commit()
        return cur.rowcount > 0

def list_shipments(status: str = None, limit: int = 100) -> List[Dict]:
    """Retrieve list of shipments."""
    with get_connection() as conn:
        query = "SELECT * FROM shipments"
        params = []
        if status:
            query += " WHERE status = %s"
            params.append(status)
        query += " ORDER BY created_at DESC LIMIT %s"
        params.append(limit)
        
        cur = conn.execute(query, params)
        return [dict(row) for row in cur.fetchall()]

def get_dashboard_stats() -> Dict[str, Any]:
    """Retrieve shipment status counts."""
    _ensure_table() # มั่นใจว่าตารางมีอยู่
    with get_connection() as conn:
        query = """
            SELECT 
                COUNT(*) as total, 
                SUM(CASE WHEN status = 'Proceed' THEN 1 ELSE 0 END) as proceed,
                SUM(CASE WHEN status = 'Finished' THEN 1 ELSE 0 END) as finished,
                SUM(CASE WHEN status = 'Closed' THEN 1 ELSE 0 END) as closed,
                SUM(CASE WHEN status = 'Canceled' THEN 1 ELSE 0 END) as canceled
            FROM shipments
        """
        row = conn.execute(query).fetchone()
        return dict(row) if row else {}