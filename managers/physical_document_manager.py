from typing import Dict, Any, List, Optional
from database.connection import get_connection
from managers.tenant_context import get_current_tenant_id

def register_physical_document(data: Dict[str, Any]) -> int:
    tenant_id = get_current_tenant_id()
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO physical_documents (
                    tenant_id, job_no, document_type, is_original, 
                    quantity, received_from, received_date, storage_location, 
                    barcode, remarks
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (
                tenant_id,
                data.get("job_no"),
                data.get("document_type"),
                data.get("is_original", True),
                data.get("quantity", 1),
                data.get("received_from"),
                data.get("received_date"),
                data.get("storage_location"),
                data.get("barcode"),
                data.get("remarks")
            ))
            row = cur.fetchone()
            conn.commit()
            return row['id']

def release_physical_document(doc_id: int, released_to: str, courier_name: str = None, tracking_no: str = None) -> bool:
    tenant_id = get_current_tenant_id()
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE physical_documents 
                SET released_to=%s, released_date=CURRENT_TIMESTAMP, 
                    courier_name=%s, tracking_no=%s
                WHERE id=%s AND tenant_id=%s
            """, (released_to, courier_name, tracking_no, doc_id, tenant_id))
            conn.commit()
            return cur.rowcount > 0

def update_custody_status(doc_id: int, status: str) -> bool:
    tenant_id = get_current_tenant_id()
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE physical_documents 
                SET storage_location=%s
                WHERE id=%s AND tenant_id=%s
            """, (status, doc_id, tenant_id))
            conn.commit()
            return cur.rowcount > 0

def list_physical_documents_by_job(job_no: str) -> List[Dict[str, Any]]:
    tenant_id = get_current_tenant_id()
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM physical_documents WHERE job_no=%s AND tenant_id=%s ORDER BY id DESC", 
                        (job_no, tenant_id))
            rows = cur.fetchall()
            return [dict(r) for r in rows]

def list_custody_records() -> List[Dict[str, Any]]:
    tenant_id = get_current_tenant_id()
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT *, storage_location as status, storage_location as custodian FROM physical_documents WHERE tenant_id=%s ORDER BY id DESC", 
                        (tenant_id,))
            rows = cur.fetchall()
            return [dict(r) for r in rows]
