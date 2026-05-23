from typing import List, Dict, Any, Optional
from database.connection import get_connection
from managers.job_number import generate_job_number

def create_shipment(data: Dict[str, Any], company_prefix: str = None) -> str:
    """Create a shipment record with proper transaction commit."""
    job_type = data["job_type"]
    job_no = generate_job_number(
        job_type, data.get("etd") or data.get("pick_up_date"), company_prefix
    )
    
    cols = ["job_no", "job_type"] + SHIPMENT_FIELDS
    placeholders = ",".join(["%s"] * len(cols))
    values = [job_no, job_type] + [data.get(f) for f in SHIPMENT_FIELDS]
    
    with get_connection() as conn:
        conn.execute(f"INSERT INTO shipments ({','.join(cols)}) VALUES ({placeholders})", values)
        conn.commit()
    return job_no

def update_shipment(job_no: str, updates: Dict[str, Any]) -> bool:
    """Update shipment and ensure changes are committed."""
    allowed = [f for f in updates.keys() if f in SHIPMENT_FIELDS]
    if not allowed: return False
    
    set_clause = ", ".join(f"{f}=%s" for f in allowed) + ", updated_at=CURRENT_TIMESTAMP"
    values = [updates[f] for f in allowed] + [job_no]
    
    with get_connection() as conn:
        cur = conn.execute(f"UPDATE shipments SET {set_clause} WHERE job_no=%s", values)
        conn.commit()
        return cur.rowcount > 0

def get_dashboard_stats() -> Dict[str, Any]:
    """Retrieve shipment status counts."""
    with get_connection() as conn:
        query = """
            SELECT 
                COUNT(*) as total, 
                SUM(CASE WHEN status = 'Pending' THEN 1 ELSE 0 END) as pending,
                SUM(CASE WHEN status = 'Proceed' THEN 1 ELSE 0 END) as active,
                SUM(CASE WHEN status = 'Finished' THEN 1 ELSE 0 END) as completed
            FROM shipments
        """
        result = conn.execute(query).fetchone()
        return dict(result)