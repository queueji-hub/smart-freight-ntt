"""Quotation write service that keeps master IDs and charge IDs canonical."""
from __future__ import annotations

from typing import Any, Dict, List

from database.connection import get_connection
from managers.quotation_manager import create_quotation as _legacy_create_quotation
from managers.quotation_manager import update_quotation as _legacy_update_quotation
from managers.quotation_manager import delete_quotation as _legacy_delete_quotation
from managers.quotation_manager import set_quotation_status as _legacy_set_quotation_status
from managers.ssot_write_adapter import sync_quotation_master_ids
from managers.tenant_context import get_current_tenant_id
from managers.charge_master_manager import list_charges


def _normalize_items(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not items:
        return []
    try:
        charges = list_charges(active_only=True)
    except Exception:
        charges = []
    by_code = {str(c.get("charge_code") or "").upper(): c for c in charges}
    by_description = {str(c.get("description") or "").strip().lower(): c for c in charges}
    normalized: List[Dict[str, Any]] = []
    for idx, raw in enumerate(items, 1):
        item = dict(raw or {})
        code = str(item.get("charge_code") or "").strip().upper()
        description = str(item.get("description") or "").strip()
        master = by_code.get(code) if code else by_description.get(description.lower())
        if master:
            item["charge_code"] = code or master.get("charge_code")
            if not item.get("description"):
                item["description"] = master.get("description")
            if not item.get("basis"):
                item["basis"] = master.get("default_basis")
            if not item.get("unit"):
                item["unit"] = master.get("default_unit") or "SHPMT"
            if not item.get("currency"):
                item["currency"] = master.get("default_currency") or "USD"
        else:
            if not item.get("unit"):
                item["unit"] = "SHPMT"
            if not item.get("currency"):
                item["currency"] = "USD"
            if not item.get("description"):
                item["description"] = code or "Freight Charge"
        normalized.append(item)
    return normalized


def _assert_customer_scope(customer_id: Any) -> None:
    if not customer_id:
        return
    try:
        tenant = get_current_tenant_id() or "default"
        with get_connection() as conn, conn.cursor() as cur:
            cur.execute("SELECT 1 FROM customers WHERE id=%s AND (tenant_id=%s OR tenant_id IS NULL OR tenant_id='') LIMIT 1", (customer_id, tenant))
            row = cur.fetchone()
            if row is None:
                # If table has records for tenant, verify customer existence
                cur.execute("SELECT COUNT(*) FROM customers WHERE (tenant_id=%s OR tenant_id IS NULL OR tenant_id='')", (tenant,))
                cnt_row = cur.fetchone()
                cnt = cnt_row[0] if cnt_row else 0
                if cnt > 0:
                    raise ValueError("Customer does not belong to the current tenant.")
    except ValueError:
        raise
    except Exception:
        pass


def _enrich_customer_data(data: Dict[str, Any], customer_id: Any) -> Dict[str, Any]:
    enriched = dict(data)
    if not customer_id:
        return enriched
    try:
        tenant = get_current_tenant_id() or "default"
        with get_connection() as conn, conn.cursor() as cur:
            cur.execute("SELECT company_name, address, billing_address, contact_person, tel, email FROM customers WHERE id=%s AND (tenant_id=%s OR tenant_id IS NULL OR tenant_id='default') LIMIT 1", (customer_id, tenant))
            row = cur.fetchone()
            if row:
                cust = dict(row)
                if not (enriched.get("customer_name") or "").strip():
                    enriched["customer_name"] = cust.get("company_name", "")
                if not (enriched.get("customer_address") or "").strip():
                    enriched["customer_address"] = (cust.get("address") or cust.get("billing_address") or "").strip()
                if not (enriched.get("attention") or "").strip() and cust.get("contact_person"):
                    enriched["attention"] = cust.get("contact_person")
                if not (enriched.get("tel") or "").strip() and cust.get("tel"):
                    enriched["tel"] = cust.get("tel")
                if not (enriched.get("customer_email") or "").strip() and cust.get("email"):
                    enriched["customer_email"] = cust.get("email")
    except Exception:
        pass
    return enriched


def create_quotation_ssot(data: Dict[str, Any], items: List[Dict[str, Any]]) -> str:
    customer_id = data.get("customer_id")
    sales_id = data.get("sales_id")
    if customer_id is None:
        raise ValueError("customer_id is required for new quotations.")
    _assert_customer_scope(customer_id)
    enriched_data = _enrich_customer_data(data, customer_id)
    normalized_items = _normalize_items(items)
    quotation_no = _legacy_create_quotation(enriched_data, normalized_items)
    sync_quotation_master_ids(quotation_no, customer_id=customer_id, sales_id=sales_id)
    return quotation_no


def update_quotation_ssot(quotation_no: str, data: Dict[str, Any], items: List[Dict[str, Any]]) -> None:
    customer_id = data.get("customer_id")
    sales_id = data.get("sales_id")
    if customer_id is None:
        raise ValueError("customer_id is required for quotation updates.")
    _assert_customer_scope(customer_id)
    enriched_data = _enrich_customer_data(data, customer_id)
    normalized_items = _normalize_items(items)
    _legacy_update_quotation(quotation_no, enriched_data, normalized_items)
    sync_quotation_master_ids(quotation_no, customer_id=customer_id, sales_id=sales_id)


def delete_quotation_ssot(quotation_no: str) -> bool:
    """Deletes quotation and its associated items atomically."""
    return _legacy_delete_quotation(quotation_no)


def set_quotation_status_ssot(quotation_no: str, status: str) -> None:
    """Updates quotation status."""
    _legacy_set_quotation_status(quotation_no, status)
