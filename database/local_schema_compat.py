"""Phase 30 database compatibility helpers.

Production PostgreSQL remains migration-driven, while this helper keeps local
and test SQLite databases compatible with the Phase 30 contract.
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
    with get_connection() as conn:
        if not _is_sqlite(conn):
            ensure_phase30_profitability_schema(conn)
            return

        with conn.cursor() as cur:
            table_columns = {
                "quotations": {"sales_id": "INTEGER", "approval_status": "TEXT DEFAULT 'Draft'"},
                "bookings": {"sales_id": "INTEGER", "approval_status": "TEXT DEFAULT 'Draft'", "carrier_booking_no": "TEXT"},
                "invoices": {"approval_status": "TEXT DEFAULT 'Draft'"},
                "bills_of_lading": {
                    "tenant_id": "TEXT DEFAULT 'default'",
                    "approval_status": "TEXT DEFAULT 'Draft'",
                    "consol_no": "TEXT",
                    "consol_seq": "INTEGER DEFAULT 1",
                    "bl_type": "TEXT DEFAULT 'BL'",
                    "delivery_agent": "TEXT",
                    "pre_carriage_by": "TEXT",
                    "freight_payable_at": "TEXT",
                    "place_of_issue": "TEXT",
                    "number_of_originals": "INTEGER DEFAULT 3",
                },
                "job_costs": {"tenant_id": "TEXT DEFAULT 'default'", "cost_status": "TEXT DEFAULT 'ESTIMATED'"},
                "profit_sheets": {"tenant_id": "TEXT DEFAULT 'default'"},
            }
            for table, cols in table_columns.items():
                cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,))
                if not cur.fetchone():
                    continue
                existing = _columns(cur, table)
                for column, ddl in cols.items():
                    if column not in existing:
                        cur.execute(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}")

            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS charge_master (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tenant_id TEXT DEFAULT 'default',
                    charge_code TEXT NOT NULL,
                    description TEXT NOT NULL,
                    category TEXT,
                    default_basis TEXT,
                    default_unit TEXT,
                    default_currency TEXT DEFAULT 'USD',
                    is_active INTEGER DEFAULT 1,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE (tenant_id, charge_code)
                )
                """
            )
            cur.execute("CREATE INDEX IF NOT EXISTS idx_charge_master_active ON charge_master(tenant_id, is_active)")
            cur.executemany(
                """
                INSERT OR IGNORE INTO charge_master
                (tenant_id, charge_code, description, category, default_basis, default_unit, default_currency)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    ("default", "OF", "Ocean Freight", "Freight", "Shipment", "SHPMT", "USD"),
                    ("default", "THC", "Terminal Handling Charge", "Origin", "Container", "CTR", "USD"),
                    ("default", "DOC", "Documentation", "Origin", "Shipment", "SHPMT", "USD"),
                    ("default", "CUS", "Customs Clearance", "Customs", "Shipment", "SHPMT", "THB"),
                    ("default", "TRK", "Trucking", "Transport", "Trip", "TRIP", "THB"),
                    ("default", "CFS", "CFS Handling", "Handling", "CBM", "CBM", "USD"),
                    ("default", "AIR", "Air Freight", "Freight", "KG", "KG", "USD"),
                    ("default", "INS", "Insurance", "Other", "Shipment", "SHPMT", "THB"),
                ],
            )
            conn.commit()
