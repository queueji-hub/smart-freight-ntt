"""Local-only SQLite compatibility for the Phase 30 data contract.

Production PostgreSQL changes remain migration-driven. This helper only adds
missing compatibility columns to existing local SQLite tables and does not
create new business tables.
"""
from __future__ import annotations

from database.connection import get_connection


def _is_sqlite(conn) -> bool:
    return type(conn).__name__ == "SQLiteConnAdapter"


def _columns(cur, table: str) -> set[str]:
    cur.execute(f"PRAGMA table_info({table})")
    return {str(row[1]) for row in cur.fetchall()}


def ensure_phase30_local_schema() -> None:
    """Add missing compatibility columns to an existing local SQLite database."""
    with get_connection() as conn:
        if not _is_sqlite(conn):
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
