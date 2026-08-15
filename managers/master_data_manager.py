"""Lightweight database-backed master-data lookups for operational views.

Dedicated master tables can be introduced later; until then the selectors are
fed from existing normalized records instead of allowing arbitrary free text.
"""
from typing import Any, Dict, List
from database.connection import get_connection
from managers.tenant_context import get_current_tenant_id


def list_sales_users() -> List[Dict[str, Any]]:
    """Return active sales-capable users across boolean/integer legacy schemas."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, username, full_name, email, role
                FROM users
                WHERE LOWER(COALESCE(is_active::text, '0')) IN ('1','true','t')
                  AND LOWER(COALESCE(role, '')) IN ('sales','admin','manager')
                ORDER BY LOWER(COALESCE(full_name, username))
            """)
            return [dict(r) for r in cur.fetchall()]


def list_distinct_job_values(column: str) -> List[str]:
    """Union existing Shipment + Booking values for a safe selector.

    This is a compatibility lookup until dedicated normalized master tables are
    fully migrated. Only approved fields can be queried.
    """
    allowed = {"pol", "pod", "carrier", "liner", "vessel", "transshipment_port"}
    if column not in allowed:
        raise ValueError("Unsupported master-data column")
    tenant = get_current_tenant_id()
    with get_connection() as conn:
        with conn.cursor() as cur:
            booking_col = "transhipment_port" if column == "transshipment_port" else column
            if column in {"vessel", "liner"}:
                shipment_sql = f"SELECT {column} AS value FROM shipments WHERE tenant_id=%s AND {column} IS NOT NULL AND TRIM({column})<>''"
                booking_sql = f"SELECT {column} AS value FROM bookings WHERE tenant_id=%s AND {column} IS NOT NULL AND TRIM({column})<>''"
            else:
                shipment_sql = f"SELECT {column} AS value FROM shipments WHERE tenant_id=%s AND {column} IS NOT NULL AND TRIM({column})<>''"
                booking_sql = f"SELECT {booking_col} AS value FROM bookings WHERE tenant_id=%s AND {booking_col} IS NOT NULL AND TRIM({booking_col})<>''"
            cur.execute(
                f"SELECT DISTINCT value FROM ({shipment_sql} UNION ALL {booking_sql}) x ORDER BY value LIMIT 500",
                (tenant, tenant),
            )
            return [str(r['value']) for r in cur.fetchall() if r.get('value')]
