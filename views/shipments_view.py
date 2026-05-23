"""Shipment / Job Control management."""
from typing import List, Dict, Any, Optional
from database.connection import get_connection

def _ensure_table():
    """Ensure the shipments table exists with correct schema."""
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
                notify_party TEXT,
                cargo_type TEXT,
                commodity TEXT,
                carrier TEXT,
                m_vessel TEXT,
                feeder TEXT,
                pol TEXT,
                por TEXT,
                pod TEXT,
                final_destination TEXT,
                transhipment_port TEXT,
                container_no TEXT,
                seal_no TEXT,
                container_size TEXT,
                etd DATE,
                eta DATE,
                pick_up_date DATE,
                stuffing_date DATE,
                return_date DATE,
                closing_time TEXT,
                bl_no TEXT,
                invoice_no TEXT,
                dn_no TEXT,
                customer_paid INTEGER DEFAULT 0,
                remark TEXT,
                created_by TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

def create_shipment(data: Dict[str, Any]) -> str:
    """Create new shipment and return generated job_no."""
    _ensure_table()
    from managers.job_number import generate_job_number
    job_no = generate_job_number(data.get("job_type", "SE"), data.get("created_at"))
    
    # ดึงรายชื่อคอลัมน์จากข้อมูลที่ส่งมา
    fields = [k for k in data.keys()]
    values = [data[k] for k in fields]
    
    fields.append("job_no")
    values.append(job_no)
    
    cols = ",".join(fields)
    placeholders = ",".join(["%s"] * len(fields))
    
    with get_connection() as conn:
        conn.execute(f"INSERT INTO shipments ({cols}) VALUES ({placeholders})", tuple(values))
    return job_no

def list_shipments(job_type: str = None, status: str = None) -> List[Dict[str, Any]]:
    """List shipments with filters."""
    _ensure_table()
    sql = "SELECT * FROM shipments WHERE 1=1"
    params = []
    if job_type: sql += " AND job_type=%s"; params.append(job_type)
    if status: sql += " AND status=%s"; params.append(status)
    
    with get_connection() as conn:
        rows = conn.execute(sql, params).fetchall()
        return [dict(r) if hasattr(r, 'keys') else {k: v for k, v in zip(['id', 'job_no', 'status', 'job_type', 'booking_no', 'customer_name', 'shipper', 'consignee', 'notify_party', 'cargo_type', 'commodity', 'carrier', 'm_vessel', 'feeder', 'pol', 'por', 'pod', 'final_destination', 'transhipment_port', 'container_no', 'seal_no', 'container_size', 'etd', 'eta', 'pick_up_date', 'stuffing_date', 'return_date', 'closing_time', 'bl_no', 'invoice_no', 'dn_no', 'customer_paid', 'remark', 'created_by', 'created_at', 'updated_at'], r)} for r in rows]

def get_shipment(job_no: str) -> Optional[Dict[str, Any]]:
    """Get single shipment details."""
    _ensure_table()
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM shipments WHERE job_no=%s", (job_no,)).fetchone()
    return dict(row) if row and hasattr(row, 'keys') else None

def update_shipment(job_no: str, data: Dict[str, Any]) -> bool:
    """Update shipment details."""
    _ensure_table()
    sets = [f"{k}=%s" for k in data.keys()]
    params = list(data.values())
    params.append(job_no)
    
    with get_connection() as conn:
        conn.execute(f"UPDATE shipments SET {', '.join(sets)}, updated_at=CURRENT_TIMESTAMP WHERE job_no=%s", params)
    return True

def delete_shipment(job_no: str) -> bool:
    """Delete shipment."""
    _ensure_table()
    with get_connection() as conn:
        conn.execute("DELETE FROM shipments WHERE job_no=%s", (job_no,))
    return True

def clone_shipment(source_job_no: str) -> Optional[str]:
    """Duplicate shipment."""
    src = get_shipment(source_job_no)
    if not src: return None
    # ลบข้อมูลที่ไม่ต้องการโคลน
    clone_data = {k: v for k, v in src.items() if k not in ("id", "job_no", "created_at", "updated_at", "invoice_no", "customer_paid")}
    clone_data["status"] = "Proceed"
    clone_data["remark"] = f"Cloned from {source_job_no}\n" + (src.get("remark") or "")
    return create_shipment(clone_data)

def get_dashboard_stats() -> Dict[str, Any]:
    """Aggregated stats for dashboard."""
    _ensure_table()
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
        
    return {
        'total': row[0] or 0,
        'proceed': row[1] or 0,
        'finished': row[2] or 0,
        'closed': row[3] or 0,
        'canceled': row[4] or 0
    }