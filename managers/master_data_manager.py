"""Lightweight master-data lookups used by operational views.

The view layer should select IDs from master data instead of persisting
free-text copies where a canonical master already exists.
"""
from typing import Any, Dict, List

from database.connection import get_connection
from managers.tenant_context import get_current_tenant_id


def list_sales_users() -> List[Dict[str, Any]]:
    """Return active sales/admin users available to the current tenant."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, username, full_name, email, role
                FROM users
                WHERE is_active = TRUE
                  AND LOWER(COALESCE(role, '')) IN ('sales', 'admin', 'manager')
                ORDER BY LOWER(COALESCE(full_name, username))
                """
            )
            rows = cur.fetchall()
            return [dict(r) for r in rows]


def list_distinct_job_values(column: str) -> List[str]:
    """Return existing values for a safe allow-listed shipment master field.

    This is intentionally a transitional helper until dedicated Ports/Carriers/
    Vessels master tables are introduced. It prevents the UI from inventing
    values while keeping the current schema unchanged.
    """
    allowed = {"pol", "pod", "carrier", "vessel", "transshipment_port"}
    if column not in allowed:
        raise ValueError("Unsupported master-data column")

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"""
                SELECT DISTINCT {column} AS value
                FROM shipments
                WHERE tenant_id = %s
                  AND {column} IS NOT NULL
                  AND TRIM({column}) <> ''
                ORDER BY {column}
                LIMIT 500
                """,
                (get_current_tenant_id(),),
            )
            return [str(row["value"]) for row in cur.fetchall() if row.get("value")]
