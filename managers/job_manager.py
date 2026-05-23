from typing import List, Dict, Any, Optional
from database.connection import get_connection
from managers.job_number import generate_job_number
from core.audit import log_action


# =========================================================
# JOB WORKFLOW STATUS
# =========================================================

JOB_STATUS = {
    "OPEN": "Open",
    "IN_PROGRESS": "In Progress",
    "IN_TRANSIT": "In Transit",
    "CLOSED": "Closed",
    "CANCELLED": "Cancelled"
}


# =========================================================
# CREATE JOB FROM BOOKING (MAIN FLOW)
# =========================================================

def create_job_from_booking(booking: Dict[str, Any], user: Dict[str, Any]) -> str:

    tenant_id = user["tenant_id"]

    job_no = generate_job_number(
        booking.get("job_type", "SE"),
        booking.get("etd"),
        tenant_id
    )

    with get_connection() as conn:

        conn.execute("""
            INSERT INTO jobs (
                tenant_id,
                job_no,
                job_type,
                booking_no,
                customer_name,
                shipper,
                consignee,
                cargo_type,
                carrier,
                pol,
                pod,
                etd,
                eta,
                status,
                created_by
            )
            VALUES (
                %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,
                %s,%s,%s,'OPEN',%s
            )
        """, (
            tenant_id,
            job_no,
            booking.get("job_type"),
            booking.get("booking_no"),
            booking.get("customer_name"),
            booking.get("shipper"),
            booking.get("consignee"),
            booking.get("cargo_type"),
            booking.get("carrier"),
            booking.get("pol"),
            booking.get("pod"),
            booking.get("etd"),
            booking.get("eta"),
            user["id"]
        ))

        conn.commit()

        log_action(
            user["id"],
            tenant_id,
            "job",
            job_no,
            "CREATE_FROM_BOOKING"
        )

        return job_no


# =========================================================
# GET JOB
# =========================================================

def get_job(job_no: str, tenant_id: str) -> Optional[Dict[str, Any]]:

    with get_connection() as conn:
        row = conn.execute("""
            SELECT *
            FROM jobs
            WHERE job_no=%s AND tenant_id=%s
        """, (job_no, tenant_id)).fetchone()

        return dict(row) if row else None


# =========================================================
# LIST JOBS
# =========================================================

def list_jobs(
    tenant_id: str,
    status: str = None,
    limit: int = 100
) -> List[Dict[str, Any]]:

    sql = """
        SELECT *
        FROM jobs
        WHERE tenant_id=%s
    """

    params = [tenant_id]

    if status:
        sql += " AND status=%s"
        params.append(status)

    sql += " ORDER BY created_at DESC LIMIT %s"
    params.append(limit)

    with get_connection() as conn:
        rows = conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]


# =========================================================
# UPDATE JOB (SAFE + WORKFLOW)
# =========================================================

def update_job(job_no: str, tenant_id: str, data: Dict[str, Any]) -> bool:

    allowed_fields = {
        "status",
        "etd",
        "eta",
        "pol",
        "pod",
        "carrier",
        "cargo_type",
        "remark"
    }

    sets = []
    params = []

    for key in allowed_fields:
        if key in data:
            sets.append(f"{key}=%s")
            params.append(data[key])

    if not sets:
        return False

    params.append(job_no)
    params.append(tenant_id)

    with get_connection() as conn:
        conn.execute(f"""
            UPDATE jobs
            SET {', '.join(sets)},
                updated_at=CURRENT_TIMESTAMP
            WHERE job_no=%s AND tenant_id=%s
        """, params)

        conn.commit()

        return True


# =========================================================
# WORKFLOW TRANSITION (SAFE STATE MACHINE)
# =========================================================

def change_job_status(job_no: str, tenant_id: str, new_status: str):

    valid = {"OPEN", "IN_PROGRESS", "IN_TRANSIT", "CLOSED", "CANCELLED"}

    if new_status not in valid:
        raise Exception("Invalid status")

    with get_connection() as conn:
        conn.execute("""
            UPDATE jobs
            SET status=%s,
                updated_at=CURRENT_TIMESTAMP
            WHERE job_no=%s AND tenant_id=%s
        """, (new_status, job_no, tenant_id))

        conn.commit()


# =========================================================
# DELETE JOB (SOFT DELETE RECOMMENDED)
# =========================================================

def delete_job(job_no: str, tenant_id: str) -> bool:

    with get_connection() as conn:
        conn.execute("""
            UPDATE jobs
            SET status='CANCELLED'
            WHERE job_no=%s AND tenant_id=%s
        """, (job_no, tenant_id))

        conn.commit()

        return True


# =========================================================
# DASHBOARD STATS (OPS VIEW)
# =========================================================

def get_job_dashboard_stats(tenant_id: str) -> Dict[str, Any]:

    with get_connection() as conn:
        row = conn.execute("""
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN status='OPEN' THEN 1 ELSE 0 END) as open,
                SUM(CASE WHEN status='IN_PROGRESS' THEN 1 ELSE 0 END) as progress,
                SUM(CASE WHEN status='IN_TRANSIT' THEN 1 ELSE 0 END) as transit,
                SUM(CASE WHEN status='CLOSED' THEN 1 ELSE 0 END) as closed
            FROM jobs
            WHERE tenant_id=%s
        """, (tenant_id,)).fetchone()

        return dict(row) if row else {}