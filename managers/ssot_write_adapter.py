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


def _is_sqlite_connection(conn: Any) -> bool:
    return type(conn).__name__ == "SQLiteConnAdapter"


def _column_exists(cur, table: str, column: str, sqlite: bool = False) -> bool:
    if sqlite:
        cur.execute(f"PRAGMA table_info({table})")
        rows = cur.fetchall()
        return any(str(row.get("name")) == column for row in rows)

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


def _sanitize_id(key: str, val: Any, tenant: str = "default") -> Optional[int]:
    if val is None:
        return None
    if isinstance(val, int):
        return val
    s = str(val).strip()
    if s.isdigit():
        return int(s)
    if s.startswith("u_") and s[2:].isdigit():
        try:
            from managers.salesperson_manager import resolve_salesperson_id
            res = resolve_salesperson_id(s, tenant)
            if res is not None:
                return res
        except Exception:
            pass
        return int(s[2:])
    return None


def persist_master_ids(table: str, document_key: str, document_value: Any, values: Dict[str, Any]) -> bool:
    """Persist supported master IDs when the current DB schema exposes the columns."""
    allowed = _ALLOWED.get(table, set())
    tenant_id = get_current_tenant_id()
    candidate = {}
    for k in allowed:
        v = values.get(k)
        if v is not None:
            clean_v = _sanitize_id(k, v, tenant_id)
            if clean_v is not None:
                candidate[k] = clean_v

    if not candidate:
        return False

    with get_connection() as conn:
        with conn.cursor() as cur:
            sqlite = _is_sqlite_connection(conn)
            writable = {k: v for k, v in candidate.items() if _column_exists(cur, table, k, sqlite=sqlite)}
            if not writable:
                return False

            sets = ", ".join(f"{key}=%s" for key in writable)
            params = list(writable.values()) + [document_value, tenant_id]
            cur.execute(
                f"UPDATE {table} SET {sets} WHERE {document_key}=%s AND (tenant_id=%s OR tenant_id IS NULL OR tenant_id='default')",
                params,
            )
            updated = cur.rowcount > 0
        conn.commit()
    return updated


def sync_quotation_master_ids(quotation_no: str, customer_id: Any = None, sales_id: Any = None) -> bool:
    return persist_master_ids(
        "quotations", "quotation_no", quotation_no,
        {"customer_id": customer_id, "sales_id": sales_id},
    )


def sync_booking_master_ids(booking_no: str, customer_id: Any = None, sales_id: Any = None) -> bool:
    return persist_master_ids(
        "bookings", "booking_no", booking_no,
        {"customer_id": customer_id, "sales_id": sales_id},
    )


def sync_invoice_master_ids(invoice_no: str, customer_id: Any = None) -> bool:
    return persist_master_ids(
        "invoices", "doc_no", invoice_no,
        {"customer_id": customer_id},
    )
