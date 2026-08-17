"""Business-safe preflight checks before document approval or official issue."""
from __future__ import annotations

from typing import Any, Dict, List


def _has(record: Dict[str, Any], *keys: str) -> bool:
    for key in keys:
        value = record.get(key)
        if value is not None and str(value).strip() not in {"", "None", "nan"}:
            return True
    return False


def validate_document(entity: str, record: Dict[str, Any]) -> List[str]:
    """Return user-facing blocking messages; empty list means ready."""
    entity = str(entity or "").strip().lower()
    errors: List[str] = []

    if entity == "quotation":
        if not _has(record, "customer_id", "customer_name"):
            errors.append("Customer is required.")
        if not _has(record, "sales_id", "salesperson"):
            errors.append("Sales is required.")
        if not _has(record, "pol", "port_of_loading"):
            errors.append("POL is required.")
        if not _has(record, "pod", "port_of_discharge"):
            errors.append("POD is required.")
        if not _has(record, "validity_date"):
            errors.append("Valid Until is required.")

    elif entity == "booking":
        if not _has(record, "customer_id", "customer_name"):
            errors.append("Customer is required.")
        if not _has(record, "pol", "port_of_loading"):
            errors.append("POL is required.")
        if not _has(record, "pod", "port_of_discharge"):
            errors.append("POD is required.")
        if not _has(record, "etd"):
            errors.append("ETD is required.")
        if not _has(record, "eta"):
            errors.append("ETA is required.")
        if not _has(record, "cargo_type", "mode"):
            errors.append("Cargo type is required.")

    elif entity == "invoice":
        if not _has(record, "customer_id", "customer_name"):
            errors.append("Bill To Customer is required.")
        if not _has(record, "invoice_date", "doc_date", "issue_date"):
            errors.append("Issue Date is required.")
        if not _has(record, "currency"):
            errors.append("Currency is required.")

    elif entity == "bl":
        if not _has(record, "shipper"):
            errors.append("Shipper is required.")
        if not _has(record, "consignee"):
            errors.append("Consignee is required.")
        if not _has(record, "pol", "port_of_loading"):
            errors.append("POL is required.")
        if not _has(record, "pod", "port_of_discharge"):
            errors.append("POD is required.")

    return errors
