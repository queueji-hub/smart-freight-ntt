from typing import List, Dict, Any, Optional
from database.connection import get_connection
from managers.job_number import generate_job_number

# =========================
# CONFIG
# =========================

SHIPMENT_FIELDS = [
    "status", "job_type", "booking_no", "customer_name",
    "shipper", "consignee", "cargo_type", "carrier",
    "pol", "pod", "etd", "eta",
    "bl_no", "invoice_no",
    "customer_paid",
    "remark",
    "created_by", "updated_by"
]

STATUS_FLOW = ["Proceed", "In Transit", "Arrived", "Finished", "Closed", "Canceled"]


# =========================
# TABLE INIT (SAFE)
# =========================

def init_shipments_table():
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
            updated_by TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)
        conn.commit()


# =========================
# CREATE JOB
# =========================

def create_shipment(data: Dict[str, Any], company_prefix: str = None) -> str:
    job_no = generate_job_number(
        data.get("job_type", "SE"),
        data.get("etd"),
        company_prefix
    )

    data = {k: v for k, v in data.items() if k in SHIPMENT_FIELDS}

    cols = ["job_no"] + list(data.keys())
    vals = [job_no] + list(data.values())

    placeholders = ", ".join(["%s"] * len(cols))
    columns = ", ".join(cols)

    with get_connection() as conn:
        conn.execute(
            f"INSERT INTO shipments ({columns}) VALUES ({placeholders})",
            tuple(vals)
        )
        conn.commit()

    return job_no


# =========================
# LIST JOBS
# =========================

def list_shipments(status: Optional[str] = None, limit: int = 200) -> List[Dict]:
    sql = "SELECT * FROM shipments WHERE 1=1"
    params = []

    if status:
        sql += " AND status = %s"
        params.append(status)

    sql += " ORDER BY created_at DESC LIMIT %s"
    params.append(limit)

    with get_connection() as conn:
        rows = conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]


# =========================
# GET SINGLE JOB
# =========================

def get_shipment(job_no: str) -> Optional[Dict]:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM shipments WHERE job_no = %s",
            (job_no,)
        ).fetchone()

        return dict(row) if row else None


# =========================
# UPDATE JOB (SAFE PATCH)
# =========================

def update_shipment(job_no: str, data: Dict[str, Any]) -> bool:
    allowed = {k: v for k, v in data.items() if k in SHIPMENT_FIELDS}

    if not allowed:
        return False

    sets = ", ".join([f"{k}=%s" for k in allowed.keys()])
    values = list(allowed.values())

    values.append(job_no)

    with get_connection() as conn:
        cur = conn.execute(
            f"""
            UPDATE shipments
            SET {sets},
                updated_at = CURRENT_TIMESTAMP
            WHERE job_no = %s
            """,
            tuple(values)
        )
        conn.commit()

        return cur.rowcount > 0


# =========================
# DELETE JOB (SOFT SAFE OPTION)
# =========================

def delete_shipment(job_no: str) -> bool:
    with get_connection() as conn:
        conn.execute(
            "DELETE FROM shipments WHERE job_no = %s",
            (job_no,)
        )
        conn.commit()

    return True


# =========================
# DASHBOARD STATS
# =========================

def get_dashboard_stats() -> Dict[str, Any]:
    with get_connection() as conn:
        row = conn.execute("""
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN status='Proceed' THEN 1 ELSE 0 END) as proceed,
                SUM(CASE WHEN status='Finished' THEN 1 ELSE 0 END) as finished,
                SUM(CASE WHEN status='Closed' THEN 1 ELSE 0 END) as closed,
                SUM(CASE WHEN status='Canceled' THEN 1 ELSE 0 END) as canceled
            FROM shipments
        """).fetchone()

        return dict(row) if row else {}


# =========================
# ROUTER ENTRYPOINT ALIAS
# =========================
def render():
    """Delegates UI rendering to views.shipment_view"""
    from views.shipment_view import render as render_shipment
    render_shipment()