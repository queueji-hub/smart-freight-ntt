from typing import Dict, Any, List, Optional
from database.connection import get_connection
from managers.tenant_context import get_current_tenant_id

def create_regulatory_submission(data: Dict[str, Any]) -> int:
    tenant_id = get_current_tenant_id()
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO regulatory_submissions (
                    tenant_id, submission_type, country, authority, 
                    job_no, hbl_no, mbl_no, container_no, 
                    submission_reference, submission_date, cut_off_date, 
                    submitted_by, status, response, error_msg, version
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (
                tenant_id,
                data.get("submission_type"),
                data.get("country"),
                data.get("authority"),
                data.get("job_no"),
                data.get("hbl_no"),
                data.get("mbl_no"),
                data.get("container_no"),
                data.get("submission_reference"),
                data.get("submission_date"),
                data.get("cut_off_date"),
                data.get("submitted_by"),
                data.get("status", "DRAFT"),
                data.get("response"),
                data.get("error_msg"),
                data.get("version", 1)
            ))
            row = cur.fetchone()
            conn.commit()
            return row['id']

def get_submission(submission_id: int) -> Optional[Dict[str, Any]]:
    tenant_id = get_current_tenant_id()
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM regulatory_submissions WHERE id=%s AND tenant_id=%s", 
                        (submission_id, tenant_id))
            row = cur.fetchone()
            if row:
                return dict(row)
            return None

def update_submission_status(submission_id: int, status: str, response: str = None, error_msg: str = None) -> bool:
    tenant_id = get_current_tenant_id()
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE regulatory_submissions 
                SET status=%s, response=%s, error_msg=%s, updated_at=CURRENT_TIMESTAMP 
                WHERE id=%s AND tenant_id=%s
            """, (status, response, error_msg, submission_id, tenant_id))
            conn.commit()
            return cur.rowcount > 0

def list_submissions_by_job(job_no: str) -> List[Dict[str, Any]]:
    tenant_id = get_current_tenant_id()
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM regulatory_submissions WHERE job_no=%s AND tenant_id=%s ORDER BY updated_at DESC", 
                        (job_no, tenant_id))
            rows = cur.fetchall()
            return [dict(r) for r in rows]
