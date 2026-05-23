"""Shipment (Job Control Sheet) CRUD operations."""
from typing import List, Dict, Any, Optional
from database.connection import get_connection
from managers.job_number import generate_job_number


# All editable fields (excluding auto-generated id, job_no, job_type, timestamps)
SHIPMENT_FIELDS = [
    "booking_id", "booking_no",
    "customer_id", "customer_name",
    "shipper", "consignee", "notify_party",
    "brand", "commodity", "combine_commodity",
    "cargo_type", "full_or_half",
    "pick_up_date", "stuffing_date", "return_date", "etd", "eta",
    "container_no", "seal_no", "container_size",
    "weight_origin", "weight_port",
    "carrier", "m_vessel", "feeder",
    "pol", "por", "pod", "final_destination", "transhipment_port",
    "bl_no", "bl_status", "closing_time",
    "overnight_trucking", "status",
    "invoice_no", "customer_paid",
    "dn_type", "dn_no", "remark", "created_by",
]

VALID_STATUS = ("Proceed", "Finished", "Closed", "Canceled")


def create_shipment(data: Dict[str, Any], company_prefix: str = None) -> str:
    """Create a shipment record. Auto-generates job_no."""
    job_type = data["job_type"]
    job_no = generate_job_number(
        job_type,
        data.get("etd") or data.get("pick_up_date"),
        company_prefix
    )
    
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
    """Update fields of a shipment by job_no."""
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
    customer_id: Optional[int] = None,
    limit: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """List shipments with optional filters."""
    sql = "SELECT * FROM shipments WHERE 1=1"
    params = []
    if job_type:
        sql += " AND job_type=?"; params.append(job_type)
    if status:
        sql += " AND status=?"; params.append(status)
    if carrier:
        sql += " AND carrier=?"; params.append(carrier)
    if customer_id:
        sql += " AND customer_id=?"; params.append(customer_id)
    sql += " ORDER BY etd DESC, id DESC"
    if limit:
        sql += f" LIMIT {int(limit)}"
    
    with get_connection() as conn:
        rows = conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]


def clone_shipment(source_job_no: str) -> Optional[str]:
    """Duplicate an existing shipment as a new draft."""
    src = get_shipment(source_job_no)
    if not src:
        return None
    # Strip identifiers, mark as new draft
    clone_data = {k: v for k, v in src.items()
                  if k not in ("id", "job_no", "created_at", "updated_at",
                               "invoice_no", "customer_paid")}
    clone_data["status"] = "Proceed"
    clone_data["remark"] = f"Cloned from {source_job_no}\n" + (src.get("remark") or "")
    return create_shipment(clone_data)


def get_dashboard_stats() -> Dict[str, Any]:
    """Aggregated stats for dashboard KPIs."""
    with get_connection() as conn:
        # แก้ไขการดึงข้อมูลโดยใช้ Alias (AS cnt) และแปลงเป็น dict เพื่อกัน KeyError
        def fetch_count(query: str) -> int:
            row = conn.execute(query).fetchone()
            return dict(row).get("cnt", 0) if row else 0

        total = fetch_count("SELECT COUNT(*) AS cnt FROM shipments")
        proceed = fetch_count("SELECT COUNT(*) AS cnt FROM shipments WHERE status='Proceed'")
        finished = fetch_count("SELECT COUNT(*) AS cnt FROM shipments WHERE status='Finished'")
        closed = fetch_count("SELECT COUNT(*) AS cnt FROM shipments WHERE status='Closed'")
        canceled = fetch_count("SELECT COUNT(*) AS cnt FROM shipments WHERE status='Canceled'")
        
        by_type = conn.execute(
            "SELECT job_type, COUNT(*) as c FROM shipments GROUP BY job_type"
        ).fetchall()
        
        by_carrier = conn.execute(
            "SELECT carrier, COUNT(*) as c FROM shipments "
            "WHERE carrier IS NOT NULL AND carrier!='' "
            "GROUP BY carrier ORDER BY c DESC LIMIT 10"
        ).fetchall()
        
        by_month = conn.execute(
            "SELECT strftime('%Y-%m', etd) as ym, COUNT(*) as c FROM shipments "
            "WHERE etd IS NOT NULL GROUP BY ym ORDER BY ym"
        ).fetchall()
    
    return {
        "total": total,
        "proceed": proceed,
        "finished": finished,
        "closed": closed,
        "canceled": canceled,
        "by_type": [dict(r) for r in by_type],
        "by_carrier": [dict(r) for r in by_carrier],
        "by_month": [dict(r) for r in by_month],
    }