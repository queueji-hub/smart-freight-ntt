"""Shipment (Job Control Sheet) CRUD operations."""
from typing import List, Dict, Any, Optional
from database.connection import get_connection
from managers.job_number import generate_job_number


SHIPMENT_FIELDS = [
    "booking_no", "customer_name", "brand", "commodity", "combine_commodity",
    "full_or_half", "pick_up_date", "stuffing_date", "return_date", "etd", "eta",
    "container_no", "seal_no", "container_size", "weight_origin", "weight_port",
    "carrier", "pol", "pod", "bl_status", "overnight_trucking", "status",
    "invoice_no", "customer_paid", "dn_type", "dn_no", "remark",
]


def create_shipment(data: Dict[str, Any]) -> str:
    """Create a shipment record. Auto-generates job_no.
    Returns the generated job_no."""
    job_type = data["job_type"]
    job_no = generate_job_number(job_type, data.get("etd") or data.get("pick_up_date"))
    
    cols = ["job_no", "job_type"] + SHIPMENT_FIELDS
    values = [job_no, job_type] + [data.get(f) for f in SHIPMENT_FIELDS]
    placeholders = ",".join("?" * len(cols))
    
    with get_connection() as conn:
        conn.execute(
            f"INSERT INTO shipments ({','.join(cols)}) VALUES ({placeholders})",
            values,
        )
    return job_no


def update_shipment(job_no: str, updates: Dict[str, Any]) -> bool:
    """Update fields of a shipment by job_no. Returns True on success."""
    allowed = [f for f in updates.keys() if f in SHIPMENT_FIELDS]
    if not allowed:
        return False
    
    set_clause = ", ".join(f"{f}=?" for f in allowed)
    set_clause += ", updated_at=CURRENT_TIMESTAMP"
    values = [updates[f] for f in allowed] + [job_no]
    
    with get_connection() as conn:
        cur = conn.execute(
            f"UPDATE shipments SET {set_clause} WHERE job_no=?", values
        )
        return cur.rowcount > 0


def delete_shipment(job_no: str) -> bool:
    """Delete a shipment by job_no."""
    with get_connection() as conn:
        cur = conn.execute("DELETE FROM shipments WHERE job_no=?", (job_no,))
        return cur.rowcount > 0


def get_shipment(job_no: str) -> Optional[Dict[str, Any]]:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM shipments WHERE job_no=?", (job_no,)
        ).fetchone()
        return dict(row) if row else None


def list_shipments(
    job_type: Optional[str] = None,
    status: Optional[str] = None,
    carrier: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """List all shipments with optional filters."""
    sql = "SELECT * FROM shipments WHERE 1=1"
    params = []
    if job_type:
        sql += " AND job_type=?"
        params.append(job_type)
    if status:
        sql += " AND status=?"
        params.append(status)
    if carrier:
        sql += " AND carrier=?"
        params.append(carrier)
    sql += " ORDER BY etd DESC, id DESC"
    
    with get_connection() as conn:
        rows = conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]


def get_dashboard_stats() -> Dict[str, Any]:
    """Aggregated stats for dashboard KPIs."""
    with get_connection() as conn:
        total = conn.execute("SELECT COUNT(*) FROM shipments").fetchone()[0]
        in_progress = conn.execute(
            "SELECT COUNT(*) FROM shipments WHERE status='In-Progress'"
        ).fetchone()[0]
        finished = conn.execute(
            "SELECT COUNT(*) FROM shipments WHERE status='Finished'"
        ).fetchone()[0]
        cancelled = conn.execute(
            "SELECT COUNT(*) FROM shipments WHERE status='Cancelled'"
        ).fetchone()[0]
        
        by_type = conn.execute(
            "SELECT job_type, COUNT(*) c FROM shipments GROUP BY job_type"
        ).fetchall()
        by_carrier = conn.execute(
            "SELECT carrier, COUNT(*) c FROM shipments "
            "WHERE carrier IS NOT NULL AND carrier!='' "
            "GROUP BY carrier ORDER BY c DESC LIMIT 10"
        ).fetchall()
        by_month = conn.execute(
            "SELECT strftime('%Y-%m', etd) ym, COUNT(*) c FROM shipments "
            "WHERE etd IS NOT NULL GROUP BY ym ORDER BY ym"
        ).fetchall()
        by_pod = conn.execute(
            "SELECT pod, COUNT(*) c FROM shipments "
            "WHERE pod IS NOT NULL AND pod!='' "
            "GROUP BY pod ORDER BY c DESC LIMIT 10"
        ).fetchall()
    
    return {
        "total": total,
        "in_progress": in_progress,
        "finished": finished,
        "cancelled": cancelled,
        "by_type": [dict(r) for r in by_type],
        "by_carrier": [dict(r) for r in by_carrier],
        "by_month": [dict(r) for r in by_month],
        "by_pod": [dict(r) for r in by_pod],
    }
