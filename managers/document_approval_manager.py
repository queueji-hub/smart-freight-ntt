from typing import Dict, Tuple
from database.connection import get_connection
from managers.tenant_context import get_current_tenant_id
from core.document_preflight import validate_document

APPROVAL_STATES = ("Draft", "Pending Approval", "Approved")
TABLES: Dict[str, Tuple[str, str]] = {
    "quotation": ("quotations", "quotation_no"),
    "booking": ("bookings", "booking_no"),
    "invoice": ("invoices", "doc_no"),
    "bl": ("bills_of_lading", "bl_no"),
}

APPROVER_ROLES = {
    "quotation": {"admin"},
    "booking": {"admin", "operation"},
    "bl": {"admin", "operation"},
    "invoice": {"admin", "accounting"},
}

EDITOR_ROLES = {
    "quotation": {"admin", "sales"},
    "booking": {"admin", "sales", "operation"},
    "bl": {"admin", "operation"},
    "invoice": {"admin", "accounting"},
}


def _table(entity: str) -> Tuple[str, str]:
    entity = str(entity or "").strip().lower()
    try:
        return TABLES[entity]
    except KeyError as exc:
        raise ValueError(f"Unsupported approval entity: {entity}") from exc


def _role(user_or_role) -> str:
    if isinstance(user_or_role, dict):
        return str(user_or_role.get("role", "")).strip().lower()
    return str(user_or_role or "").strip().lower()


def _fetch_record(entity: str, doc_no: str) -> Dict:
    table, key = _table(entity)
    tenant = get_current_tenant_id()
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"SELECT * FROM {table} WHERE {key}=%s AND tenant_id=%s LIMIT 1",
                (doc_no, tenant),
            )
            row = cur.fetchone()
    return dict(row) if row else {}


def _assert_preflight(entity: str, doc_no: str) -> None:
    record = _fetch_record(entity, doc_no)
    if not record:
        raise ValueError(f"{entity} '{doc_no}' not found")
    errors = validate_document(entity, record)
    if errors:
        raise ValueError("Document is not ready: " + " ".join(errors))


def get_approval_status(entity: str, doc_no: str) -> str:
    table, key = _table(entity)
    tenant = get_current_tenant_id()
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"SELECT approval_status FROM {table} WHERE {key}=%s AND tenant_id=%s LIMIT 1",
                (doc_no, tenant),
            )
            row = cur.fetchone()
    value = (row.get("approval_status") if isinstance(row, dict) else row[0]) if row else "Draft"
    return value if value in APPROVAL_STATES else "Draft"


def set_approval_status(entity: str, doc_no: str, status: str) -> None:
    if status not in APPROVAL_STATES:
        raise ValueError("Invalid approval status")
    table, key = _table(entity)
    tenant = get_current_tenant_id()
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"UPDATE {table} SET approval_status=%s WHERE {key}=%s AND tenant_id=%s",
                (status, doc_no, tenant),
            )
            if cur.rowcount == 0:
                raise ValueError(f"{entity} '{doc_no}' not found")
        conn.commit()


def transition_document(entity: str, doc_no: str, target_status: str, user) -> str:
    """Tenant-safe state machine: Draft -> Pending Approval -> Approved."""
    entity = str(entity or "").strip().lower()
    target_status = str(target_status or "").strip()
    current = get_approval_status(entity, doc_no)
    role = _role(user)

    if target_status == "Pending Approval":
        if current != "Draft":
            raise ValueError(f"Cannot submit {entity} from status '{current}'")
        if role not in EDITOR_ROLES.get(entity, set()):
            raise PermissionError("You do not have permission to submit this document for approval.")
        _assert_preflight(entity, doc_no)
    elif target_status == "Approved":
        if current != "Pending Approval":
            raise ValueError(f"Cannot approve {entity} from status '{current}'")
        if role not in APPROVER_ROLES.get(entity, set()):
            raise PermissionError("You do not have permission to approve this document.")
        _assert_preflight(entity, doc_no)
    elif target_status == "Draft":
        if role not in EDITOR_ROLES.get(entity, set()):
            raise PermissionError("You do not have permission to return this document to Draft.")
        if current not in {"Draft", "Pending Approval"}:
            raise ValueError(f"Cannot return {entity} from status '{current}' to Draft")
    else:
        raise ValueError("Unsupported approval transition")

    set_approval_status(entity, doc_no, target_status)
    return target_status


def submit_for_approval(entity: str, doc_no: str, user) -> str:
    return transition_document(entity, doc_no, "Pending Approval", user)


def approve_document(entity: str, doc_no: str, user) -> str:
    return transition_document(entity, doc_no, "Approved", user)


def can_approve(entity: str, user) -> bool:
    role = _role(user)
    entity = str(entity or "").strip().lower()
    return role in APPROVER_ROLES.get(entity, set())


def can_issue_official_pdf(entity: str, doc_no: str) -> bool:
    return get_approval_status(entity, doc_no) == "Approved"
