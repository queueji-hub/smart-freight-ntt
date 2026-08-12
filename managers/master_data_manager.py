"""Lightweight database-backed master-data lookups for operational views.

Dedicated master tables can be introduced later; until then the selectors are
fed from existing normalized records instead of allowing arbitrary free text.
"""
from typing import Any, Dict, List
from database.connection import get_connection
from managers.tenant_context import get_current_tenant_id


def list_sales_users() -> List[Dict[str, Any]]:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, username, full_name, email, role
                FROM users
                WHERE is_active = TRUE
                  AND LOWER(COALESCE(role, '')) IN ('sales','admin','manager')
                ORDER BY LOWER(COALESCE(full_name, username))
            """)
            return [dict(r) for r in cur.fetchall()]


def list_distinct_job_values(column: str) -> List[str]:
    """Union existing Shipment + Booking values for a safe selector."""
    allowed = {"pol", "pod", "carrier", "vessel", "transshipment_port"}
    if column not in allowed:
        raise ValueError("Unsupported master-data column")
    tenant = get_current_tenant_id()
    with get_connection() as conn:
        with conn.cursor() as cur:
            # Booking schema uses transhipment_port spelling; vessel values are
            # intentionally consolidated with Mother Vessel / vessel values.
            booking_col = "transhipment_port" if column == "transshipment_port" else column
            if column == "vessel":
                shipment_sql = "SELECT vessel AS value FROM shipments WHERE tenant_id=%s AND vessel IS NOT NULL AND TRIM(vessel)<>''"
                booking_sql = "SELECT COALESCE(m_vessel, vessel) AS value FROM bookings WHERE tenant_id=%s AND COALESCE(m_vessel, vessel) IS NOT NULL AND TRIM(COALESCE(m_vessel, vessel))<>''"
            else:
                shipment_sql = f"SELECT {column} AS value FROM shipments WHERE tenant_id=%s AND {column} IS NOT NULL AND TRIM({column})<>''"
                booking_sql = f"SELECT {booking_col} AS value FROM bookings WHERE tenant_id=%s AND {booking_col} IS NOT NULL AND TRIM({booking_col})<>''"
            cur.execute(f"SELECT DISTINCT value FROM ({shipment_sql} UNION ALL {booking_sql}) x ORDER BY value LIMIT 500", (tenant, tenant))
            return [str(r['value']) for r in cur.fetchall() if r.get('value')]
