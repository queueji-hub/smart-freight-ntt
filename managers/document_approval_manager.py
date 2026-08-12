from typing import Dict, Tuple
from database.connection import get_connection
from managers.tenant_context import get_current_tenant_id

APPROVAL_STATES = ("Draft", "Pending Approval", "Approved")
TABLES: Dict[str, Tuple[str, str]] = {
    "quotation": ("quotations", "quotation_no"),
    "booking": ("bookings", "booking_no"),
    "invoice": ("invoices", "doc_no"),
    "bl": ("bills_of_lading", "bl_no"),
}

def get_approval_status(entity: str, doc_no: str) -> str:
    table, key = TABLES[entity]
    tenant = get_current_tenant_id()
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(f"SELECT approval_status FROM {table} WHERE {key}=%s AND tenant_id=%s LIMIT 1", (doc_no, tenant))
            row = cur.fetchone()
    value = (row.get("approval_status") if isinstance(row, dict) else row[0]) if row else "Draft"
    return value if value in APPROVAL_STATES else "Draft"

def set_approval_status(entity: str, doc_no: str, status: str) -> None:
    if status not in APPROVAL_STATES:
        raise ValueError("Invalid approval status")
    table, key = TABLES[entity]
    tenant = get_current_tenant_id()
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(f"UPDATE {table} SET approval_status=%s WHERE {key}=%s AND tenant_id=%s", (status, doc_no, tenant))
            if cur.rowcount == 0:
                raise ValueError(f"{entity} '{doc_no}' not found")
        conn.commit()

def can_issue_official_pdf(entity: str, doc_no: str) -> bool:
    return get_approval_status(entity, doc_no) == "Approved"
