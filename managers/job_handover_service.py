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


def build_job_payload(quotation: Dict[str, Any], user: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    if not quotation:
        raise ValueError("Quotation data is required.")
    quotation_no = str(quotation.get("quotation_no") or "").strip()
    if not quotation_no:
        raise ValueError("Quotation number is required.")
    customer_id = quotation.get("customer_id")
    if customer_id is None:
        raise ValueError("Quotation customer_id is required before handover.")
    status = str(quotation.get("approval_status") or quotation.get("status") or "Draft").strip().lower()
    if status not in {"approved", "accepted"}:
        raise ValueError("Only approved quotations can be handed over to Operations.")

    return {
        "status": "Proceed",
        "job_type": quotation.get("job_type"),
        "customer_id": customer_id,
        "customer_name": quotation.get("customer_name"),
        "sales_person": quotation.get("salesperson"),
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
