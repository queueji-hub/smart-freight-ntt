"""Lightweight database-backed master-data lookups for operational views.

Dedicated master tables can be introduced later; until then the selectors are
fed from existing normalized records instead of allowing arbitrary free text.

The production database is still carrying some legacy schema variants, so
these helpers inspect the actual PostgreSQL columns before building SQL. This
prevents a missing legacy column (for example shipments.liner) from crashing
 the Booking UI while preserving tenant filtering where the table supports it.

Phase 30 preview deployment marker: schema-aware selector runtime fix is active.
"""
from typing import Any, Dict, List, Set

from database.connection import get_connection
from managers.tenant_context import get_current_tenant_id


_ALLOWED_JOB_FIELDS = {"pol", "pod", "carrier", "liner", "vessel", "transshipment_port"}
_TABLE_FIELD_MAP = {
    "shipments": {
        "pol": "pol",
        "pod": "pod",
        "carrier": "carrier",
        "vessel": "vessel",
    },
    "bookings": {
        "pol": "pol",
        "pod": "pod",
        "carrier": "carrier",
        "liner": "liner",
        "vessel": "vessel",
        "transshipment_port": "transhipment_port",
    },
}


_COLUMN_CACHE: Dict[str, Set[str]] = {}


def _existing_columns(cur, table: str) -> Set[str]:
    """Return columns visible in PostgreSQL for a known application table."""
    if table in _COLUMN_CACHE:
        return _COLUMN_CACHE[table]
    cur.execute(
        """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_schema = current_schema()
          AND table_name = %s
        """,
        (table,),
    )
    cols = {row["column_name"] for row in cur.fetchall()}
    if cols:
        _COLUMN_CACHE[table] = cols
    return cols


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

    Only columns that actually exist in each source table are queried. This is
    intentionally compatibility-oriented until dedicated master tables are
    fully migrated.
    """
    if column not in _ALLOWED_JOB_FIELDS:
        raise ValueError("Unsupported master-data column")

    tenant = get_current_tenant_id()

    with get_connection() as conn:
        with conn.cursor() as cur:
            selects: List[str] = []
            params: List[Any] = []

            for table, field_map in _TABLE_FIELD_MAP.items():
                source_column = field_map.get(column)
                if not source_column:
                    continue

                existing = _existing_columns(cur, table)
                if source_column not in existing:
                    continue

                predicates = [
                    f"{source_column} IS NOT NULL",
                    f"TRIM({source_column}::text) <> ''",
                ]

                # Legacy shipments may not have tenant_id. Bookings do in the
                # current baseline; apply isolation whenever the column exists.
                if "tenant_id" in existing:
                    predicates.insert(0, "tenant_id = %s")
                    params.append(tenant)

                selects.append(
                    f"SELECT {source_column}::text AS value FROM {table} "
                    f"WHERE {' AND '.join(predicates)}"
                )

            if not selects:
                return []

            sql = (
                "SELECT DISTINCT value "
                f"FROM ({' UNION ALL '.join(selects)}) x "
                "WHERE value IS NOT NULL AND TRIM(value) <> '' "
                "ORDER BY value LIMIT 500"
            )
            cur.execute(sql, tuple(params))
            return [str(row["value"]) for row in cur.fetchall() if row.get("value")]
