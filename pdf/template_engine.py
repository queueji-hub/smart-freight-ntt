from typing import Dict, Any, List, Optional
from database.connection import get_connection
from managers.tenant_context import get_current_tenant_id

def create_template(data: Dict[str, Any]) -> int:
    tenant_id = get_current_tenant_id()
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO document_templates (
                    tenant_id, template_code, template_name, document_type, 
                    version, status, effective_date, language, paper_size, 
                    is_official_form, external_submission_required, created_by
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (
                tenant_id,
                data.get("template_code"),
                data.get("template_name"),
                data.get("document_type"),
                data.get("version", 1),
                data.get("status", "DRAFT"),
                data.get("effective_date"),
                data.get("language", "EN"),
                data.get("paper_size", "A4"),
                data.get("is_official_form", False),
                data.get("external_submission_required", False),
                data.get("created_by")
            ))
            row = cur.fetchone()
            conn.commit()
            return row['id']

def get_template(template_code: str, version: int = None) -> Optional[Dict[str, Any]]:
    tenant_id = get_current_tenant_id()
    with get_connection() as conn:
        with conn.cursor() as cur:
            if version:
                cur.execute("SELECT * FROM document_templates WHERE tenant_id=%s AND template_code=%s AND version=%s", 
                            (tenant_id, template_code, version))
            else:
                cur.execute("SELECT * FROM document_templates WHERE tenant_id=%s AND template_code=%s ORDER BY version DESC LIMIT 1", 
                            (tenant_id, template_code))
            row = cur.fetchone()
            if row:
                return dict(row)
            return None

def update_template_status(template_id: int, status: str, approved_by: str = None) -> bool:
    tenant_id = get_current_tenant_id()
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("UPDATE document_templates SET status=%s, approved_by=%s WHERE id=%s AND tenant_id=%s", 
                        (status, approved_by, template_id, tenant_id))
            conn.commit()
            return cur.rowcount > 0

def generate_document_from_template(template_code: str, payload: Dict[str, Any]) -> str:
    """
    Placeholder for actual PDF generation logic tied to a template.
    Will route to specific generation modules (e.g. bl_pdf, booking_pdf) based on template_code.
    Returns path to generated file or binary string.
    """
    template = get_template(template_code)
    if not template:
        raise ValueError(f"Template {template_code} not found or active.")
        
    if template.get("is_official_form") and template.get("external_submission_required"):
        # We don't fabricate official forms like AMS or ACI here, we just create a tracking record
        return f"[EXTERNAL_FORM_REQUIRED] Use Regulatory Manager to track {template_code}."
        
    return f"/tmp/generated_{template_code}_{payload.get('job_no', 'unknown')}.pdf"
