"""Canonical Sales -> Operations handover from an approved quotation to a Job/Shipment."""
from __future__ import annotations

from typing import Any, Dict, Optional

from database.connection import get_connection
from managers.quotation_manager import get_quotation_by_no
from managers.shipment_manager import create_shipment
from managers.tenant_context import get_current_tenant_id


def _tenant() -> str:
    return str(get_current_tenant_id() or "default")


def _existing_job_for_quote(quotation_no: str) -> Optional[str]:
    tenant = _tenant()
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT job_no FROM shipments WHERE tenant_id=%s AND quotation_no=%s ORDER BY created_at DESC LIMIT 1",
            (tenant, quotation_no),
        )
        row = cur.fetchone()
        return str(row["job_no"]) if row else None


def _master_labels(customer_id: Any, sales_id: Any) -> tuple[Optional[str], Optional[str]]:
    """Resolve display labels from canonical master IDs for legacy snapshot columns."""
    tenant = _tenant()
    customer_name: Optional[str] = None
    sales_name: Optional[str] = None
    with get_connection() as conn, conn.cursor() as cur:
        if customer_id is not None:
            cur.execute(
                "SELECT company_name FROM customers WHERE tenant_id=%s AND id=%s LIMIT 1",
                (tenant, customer_id),
            )
            row = cur.fetchone()
            customer_name = str(row["company_name"]) if row and row.get("company_name") else None
        if sales_id is not None:
            cur.execute(
                "SELECT full_name, username FROM users WHERE tenant_id=%s AND id=%s LIMIT 1",
                (tenant, sales_id),
            )
            row = cur.fetchone()
            if row:
                sales_name = str(row.get("full_name") or row.get("username") or "") or None
    return customer_name, sales_name


def build_job_payload(quotation: Dict[str, Any], user: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    if not quotation:
        raise ValueError("Quotation data is required.")
    quotation_no = str(quotation.get("quotation_no") or "").strip()
    if not quotation_no:
        raise ValueError("Quotation number is required.")
    
    # Check approval status from either status or approval_status field
    status_raw = str(quotation.get("status") or "").strip().lower()
    app_status_raw = str(quotation.get("approval_status") or "").strip().lower()
    is_approved = any(s in {"approved", "accepted", "won", "active"} for s in (status_raw, app_status_raw))
    if not is_approved:
        raise ValueError("Only approved quotations can be handed over to Operations.")

    customer_id = quotation.get("customer_id")
    sales_id = quotation.get("sales_id")
    
    # Auto-resolve customer_id from customer_name if not directly stored on quotation record
    if customer_id is None and quotation.get("customer_name"):
        tenant = _tenant()
        with get_connection() as conn, conn.cursor() as cur:
            cur.execute(
                "SELECT id FROM customers WHERE company_name ILIKE %s AND (tenant_id=%s OR tenant_id IS NULL OR tenant_id='default') LIMIT 1",
                (str(quotation.get("customer_name")).strip(), tenant),
            )
            row = cur.fetchone()
            if row:
                customer_id = row[0] if isinstance(row, (tuple, list)) else row["id"]

    if customer_id is None:
        raise ValueError("Quotation customer_id is required before handover.")

    customer_name, sales_name = _master_labels(customer_id, sales_id)
    if not customer_name:
        customer_name = quotation.get("customer_name")
    if not sales_name:
        sales_name = quotation.get("salesperson") or quotation.get("sales_person")

    return {
        "status": "Proceed",
        "job_type": quotation.get("job_type"),
        "customer_id": customer_id,
        "customer_name": customer_name,
        "sales_id": sales_id,
        "sales_person": sales_name,
        "quotation_no": quotation_no,
        "service_type": quotation.get("service_type"),
        "pol": quotation.get("pol"),
        "pod": quotation.get("pod"),
        "incoterm": quotation.get("incoterm"),
        "commodity": quotation.get("commodity"),
        "freight_term": quotation.get("freight_term"),
        "remark": quotation.get("subject"),
        "created_by": (user or {}).get("id") or (user or {}).get("username"),
        "updated_by": (user or {}).get("id") or (user or {}).get("username"),
        "mode": quotation.get("mode") or quotation.get("service_type"),
    }


def handover_quotation_to_job(quotation_no: str, user: Optional[Dict[str, Any]] = None) -> str:
    quotation = get_quotation_by_no(quotation_no)
    if not quotation:
        raise ValueError("Quotation not found.")
    existing = _existing_job_for_quote(quotation_no)
    if existing:
        return existing
    payload = build_job_payload(quotation, user)
    return create_shipment(payload)
