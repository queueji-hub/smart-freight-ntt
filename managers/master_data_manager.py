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
    """Return active salespersons and sales-capable users."""
    try:
        from managers.salesperson_manager import list_salespersons
        sales_records = list_salespersons(active_only=False)
        if sales_records:
            return [
                {
                    "id": r["id"],
                    "username": r.get("sales_code") or str(r["id"]),
                    "full_name": f"{r.get('sales_code')} — {r.get('name')}".strip(" —") if r.get("sales_code") else r.get("name"),
                    "name": r.get("name"),
                    "sales_code": r.get("sales_code"),
                    "email": r.get("email"),
                    "role": "sales",
                }
                for r in sales_records if r.get("name")
            ]
    except Exception:
        pass

    with get_connection() as conn:
        with conn.cursor() as cur:
            is_sqlite = type(conn).__name__ == "SQLiteConnAdapter" or "sqlite" in str(type(conn)).lower()
            if is_sqlite:
                cur.execute("""
                    SELECT id, username, full_name, email, role
                    FROM users
                    WHERE (is_active = 1 OR is_active IS NULL)
                      AND LOWER(COALESCE(role, '')) IN ('sales','admin','manager','operation')
                    ORDER BY LOWER(COALESCE(full_name, username))
                """)
            else:
                cur.execute("""
                    SELECT id, username, full_name, email, role
                    FROM users
                    WHERE (is_active IS NOT FALSE)
                      AND LOWER(COALESCE(role, '')) IN ('sales','admin','manager','operation')
                    ORDER BY LOWER(COALESCE(full_name, username))
                """)
            return [
                {
                    "id": r["id"],
                    "username": r.get("username"),
                    "full_name": r.get("full_name") or r.get("username"),
                    "name": r.get("full_name") or r.get("username"),
                    "sales_code": (r.get("username") or "").upper()[:10],
                    "email": r.get("email"),
                    "role": r.get("role") or "sales",
                }
                for r in cur.fetchall()
            ]



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
