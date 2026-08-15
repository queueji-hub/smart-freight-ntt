"""Write-layer adapters that preserve legacy text fields while making IDs canonical.

This module is intentionally additive. It lets new UI workspaces persist master-data IDs
without requiring an immediate destructive migration of legacy text columns.
"""
from __future__ import annotations

from typing import Any, Dict

from database.connection import get_connection
from managers.tenant_context import get_current_tenant_id

_ALLOWED = {
    "quotations": {"customer_id", "sales_id"},
    "bookings": {"customer_id", "sales_id"},
    "invoices": {"customer_id"},
}


def _column_exists(cur, table: str, column: str) -> bool:
    cur.execute(
        """
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = current_schema()
          AND table_name = %s
          AND column_name = %s
        LIMIT 1
        """,
        (table, column),
    )
    return cur.fetchone() is not None


def persist_master_ids(table: str, document_key: str, document_value: Any, values: Dict[str, Any]) -> bool:
    """Persist supported master IDs when the current DB schema exposes the columns.

    Returns True when at least one ID was written. Missing columns are treated as a
    backward-compatible no-op so old environments continue to function until the
    additive migration is applied.
    """
    allowed = _ALLOWED.get(table, set())
    candidate = {k: values.get(k) for k in allowed if values.get(k) is not None}
    if not candidate:
        return False

    tenant_id = get_current_tenant_id()
    with get_connection() as conn:
        with conn.cursor() as cur:
            writable = {k: v for k, v in candidate.items() if _column_exists(cur, table, k)}
            if not writable:
                return False

            sets = ", ".join(f"{key}=%s" for key in writable)
            params = list(writable.values()) + [document_value, tenant_id]
            cur.execute(
                f"UPDATE {table} SET {sets} WHERE {document_key}=%s AND tenant_id=%s",
                params,
            )
            updated = cur.rowcount > 0
        conn.commit()
    return updated


def sync_quotation_master_ids(quotation_no: str, customer_id: Any = None, sales_id: Any = None) -> bool:
    return persist_master_ids(
        "quotations",
        "quotation_no",
        quotation_no,
        {"customer_id": customer_id, "sales_id": sales_id},
    )


def sync_booking_master_ids(booking_no: str, customer_id: Any = None, sales_id: Any = None) -> bool:
    return persist_master_ids(
        "bookings",
        "booking_no",
        booking_no,
        {"customer_id": customer_id, "sales_id": sales_id},
    )


def sync_invoice_master_ids(invoice_no: str, customer_id: Any = None) -> bool:
    return persist_master_ids(
        "invoices",
        "doc_no",
        invoice_no,
        {"customer_id": customer_id},
    )
