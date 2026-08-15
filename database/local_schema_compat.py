"""Phase 30 database compatibility helpers.

Production PostgreSQL remains migration-driven, but this helper also performs a
small idempotent profitability repair for legacy preview databases that missed
the original table-creation migration. No destructive changes are performed.
"""
from __future__ import annotations

from database.connection import get_connection
from database.postgres_compat import ensure_phase30_profitability_schema


def _is_sqlite(conn) -> bool:
    return type(conn).__name__ == "SQLiteConnAdapter"


def _columns(cur, table: str) -> set[str]:
    cur.execute(f"PRAGMA table_info({table})")
    return {str(row[1]) for row in cur.fetchall()}


def ensure_phase30_local_schema() -> None:
    """Repair lightweight Phase 30 schema differences for local/preview runtime."""
    with get_connection() as conn:
        if not _is_sqlite(conn):
            # The preview PostgreSQL database can pre-date Phase 30 table creation.
            # Keep the repair additive and idempotent so startup can self-heal this
            # specific runtime blocker until the production migration is applied.
            ensure_phase30_profitability_schema(conn)
            return

        with conn.cursor() as cur:
            table_columns = {
                "quotations": {
                    "sales_id": "INTEGER",
                    "approval_status": "TEXT DEFAULT 'Draft'",
                },
                "bookings": {
                    "sales_id": "INTEGER",
                    "approval_status": "TEXT DEFAULT 'Draft'",
                    "carrier_booking_no": "TEXT",
                },
                "invoices": {
                    "approval_status": "TEXT DEFAULT 'Draft'",
                },
                "bills_of_lading": {
                    "tenant_id": "TEXT DEFAULT 'default'",
                    "approval_status": "TEXT DEFAULT 'Draft'",
                },
                "job_costs": {
                    "tenant_id": "TEXT DEFAULT 'default'",
                    "cost_status": "TEXT DEFAULT 'ESTIMATED'",
                },
                "profit_sheets": {
                    "tenant_id": "TEXT DEFAULT 'default'",
                },
            }
            for table, cols in table_columns.items():
                cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,))
                if not cur.fetchone():
                    continue
                existing = _columns(cur, table)
                for column, ddl in cols.items():
                    if column not in existing:
                        cur.execute(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}")
            conn.commit()
