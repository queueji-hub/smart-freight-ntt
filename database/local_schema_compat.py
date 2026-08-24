"""Phase 30 database compatibility helpers.

Production PostgreSQL remains migration-driven, while this helper keeps local
and test SQLite databases compatible with the Phase 30 contract.
"""
from __future__ import annotations

from database.connection import get_connection
from database.postgres_compat import (
    ensure_phase30_quotation_schema,
    ensure_phase30_shipment_schema,
    ensure_phase30_salesperson_schema,
    ensure_phase30_profitability_schema,
    ensure_phase30_master_data_schema,
    ensure_phase30_charge_master_schema,
    ensure_phase30_bl_schema,
    ensure_phase30_approval_schema,
)


def _is_sqlite(conn) -> bool:
    return type(conn).__name__ == "SQLiteConnAdapter"


def _columns(cur, table: str) -> set[str]:
    cur.execute(f"PRAGMA table_info({table})")
    return {str(row[1]) for row in cur.fetchall()}


def ensure_phase30_local_schema() -> None:
    with get_connection() as conn:
        if not _is_sqlite(conn):
            ensure_phase30_quotation_schema(conn)
            ensure_phase30_shipment_schema(conn)
            ensure_phase30_salesperson_schema(conn)
            ensure_phase30_charge_master_schema(conn)
            ensure_phase30_master_data_schema(conn)
            ensure_phase30_profitability_schema(conn)
            ensure_phase30_bl_schema(conn)
            ensure_phase30_approval_schema(conn)
            return

        with conn.cursor() as cur:
            table_columns = {
                "quotations": {"sales_id": "INTEGER", "approval_status": "TEXT DEFAULT 'Draft'", "shipper": "TEXT", "consignee": "TEXT"},
                "quotation_items": {"charge_code": "TEXT", "basis": "TEXT", "quantity": "REAL DEFAULT 1", "unit_rate": "REAL DEFAULT 0", "amount": "REAL DEFAULT 0"},
                "bookings": {"sales_id": "INTEGER", "approval_status": "TEXT DEFAULT 'Draft'", "carrier_booking_no": "TEXT", "mother_vessel": "TEXT", "m_vessel": "TEXT", "mother_voyage": "TEXT", "m_voyage": "TEXT", "feeder_vessel": "TEXT", "feeder_voyage": "TEXT", "booking_date": "TEXT"},
                "shipments": {"service_type": "TEXT", "mother_vessel": "TEXT", "mother_voyage": "TEXT", "feeder_vessel": "TEXT", "feeder_voyage": "TEXT", "financial_locked": "INTEGER DEFAULT 0", "handover_to_accounting_at": "TEXT", "handover_by": "TEXT", "mbl_no": "TEXT", "hbl_no": "TEXT"},
                "invoices": {"approval_status": "TEXT DEFAULT 'Draft'"},
                "bills_of_lading": {"tenant_id": "TEXT DEFAULT 'default'", "approval_status": "TEXT DEFAULT 'Draft'", "consol_no": "TEXT", "consol_seq": "INTEGER DEFAULT 1", "bl_type": "TEXT DEFAULT 'BL'", "delivery_agent": "TEXT", "pre_carriage_by": "TEXT", "freight_payable_at": "TEXT", "place_of_issue": "TEXT", "number_of_originals": "INTEGER DEFAULT 3"},
                "job_costs": {"tenant_id": "TEXT DEFAULT 'default'", "cost_status": "TEXT DEFAULT 'ESTIMATED'", "billable_to_customer": "INTEGER DEFAULT 1", "matched_charge_code": "TEXT", "vendor_invoice_no": "TEXT", "payout_status": "TEXT DEFAULT 'UNPAID'"},
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

            for ddl in [
                "CREATE TABLE IF NOT EXISTS salespersons (id INTEGER PRIMARY KEY AUTOINCREMENT, tenant_id TEXT DEFAULT 'default', sales_code TEXT NOT NULL, name TEXT NOT NULL, email TEXT, phone TEXT, commission_rate REAL DEFAULT 0, remarks TEXT, is_active INTEGER DEFAULT 1, created_at TEXT DEFAULT CURRENT_TIMESTAMP, updated_at TEXT DEFAULT CURRENT_TIMESTAMP, UNIQUE(tenant_id, sales_code))",
                "CREATE TABLE IF NOT EXISTS ports (id INTEGER PRIMARY KEY AUTOINCREMENT, tenant_id TEXT DEFAULT 'default', port_code TEXT NOT NULL, unlocode TEXT, port_name TEXT NOT NULL, city TEXT, country_code TEXT, country_name TEXT, timezone TEXT, port_type TEXT DEFAULT 'PORT', is_active INTEGER DEFAULT 1, remarks TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP, updated_at TEXT DEFAULT CURRENT_TIMESTAMP, UNIQUE(tenant_id, port_code))",
                "CREATE TABLE IF NOT EXISTS business_parties (id INTEGER PRIMARY KEY AUTOINCREMENT, tenant_id TEXT DEFAULT 'default', party_code TEXT NOT NULL, legal_name TEXT NOT NULL, display_name TEXT, short_name TEXT, tax_id TEXT, branch_no TEXT, registration_no TEXT, billing_address TEXT, country_code TEXT, phone TEXT, email TEXT, website TEXT, is_active INTEGER DEFAULT 1, created_at TEXT DEFAULT CURRENT_TIMESTAMP, updated_at TEXT DEFAULT CURRENT_TIMESTAMP, UNIQUE(tenant_id, party_code))",
                "CREATE TABLE IF NOT EXISTS party_roles (id INTEGER PRIMARY KEY AUTOINCREMENT, tenant_id TEXT DEFAULT 'default', party_id INTEGER NOT NULL, role_type TEXT NOT NULL, is_active INTEGER DEFAULT 1, UNIQUE(tenant_id, party_id, role_type))",
                "CREATE TABLE IF NOT EXISTS party_finance_profiles (id INTEGER PRIMARY KEY AUTOINCREMENT, tenant_id TEXT DEFAULT 'default', party_id INTEGER NOT NULL, credit_limit REAL DEFAULT 0, credit_currency TEXT DEFAULT 'THB', credit_days INTEGER DEFAULT 0, payment_term_code TEXT, tax_id TEXT, vat_registered INTEGER DEFAULT 0, withholding_tax INTEGER DEFAULT 0, bank_name TEXT, bank_account_name TEXT, bank_account_no TEXT, swift_code TEXT, active INTEGER DEFAULT 1, UNIQUE(tenant_id, party_id))",
                "CREATE TABLE IF NOT EXISTS rate_cards (id INTEGER PRIMARY KEY AUTOINCREMENT, tenant_id TEXT DEFAULT 'default', rate_no TEXT NOT NULL, carrier_id INTEGER, origin_port_id INTEGER, destination_port_id INTEGER, mode TEXT NOT NULL, service_type TEXT, equipment_type TEXT, currency TEXT DEFAULT 'USD', valid_from TEXT, valid_to TEXT, status TEXT DEFAULT 'ACTIVE', created_at TEXT DEFAULT CURRENT_TIMESTAMP, UNIQUE(tenant_id, rate_no))",
                "CREATE TABLE IF NOT EXISTS rate_card_lines (id INTEGER PRIMARY KEY AUTOINCREMENT, tenant_id TEXT DEFAULT 'default', rate_card_id INTEGER NOT NULL, charge_id INTEGER, basis TEXT, minimum REAL DEFAULT 0, rate REAL DEFAULT 0, currency TEXT DEFAULT 'USD')",
            ]:
                cur.execute(ddl)

            cur.execute("""CREATE TABLE IF NOT EXISTS charge_master (id INTEGER PRIMARY KEY AUTOINCREMENT, tenant_id TEXT DEFAULT 'default', charge_code TEXT NOT NULL, description TEXT NOT NULL, category TEXT, default_basis TEXT, default_unit TEXT, default_currency TEXT DEFAULT 'USD', is_active INTEGER DEFAULT 1, created_at TEXT DEFAULT CURRENT_TIMESTAMP, updated_at TEXT DEFAULT CURRENT_TIMESTAMP, UNIQUE (tenant_id, charge_code))""")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_charge_master_active ON charge_master(tenant_id, is_active)")
            cur.executemany("INSERT OR IGNORE INTO charge_master (tenant_id, charge_code, description, category, default_basis, default_unit, default_currency) VALUES (?, ?, ?, ?, ?, ?, ?)", [
                ("default", "OF", "Ocean Freight", "Freight", "Shipment", "SHPMT", "USD"),
                ("default", "THC", "Terminal Handling Charge", "Origin", "Container", "CTR", "USD"),
                ("default", "DOC", "Documentation", "Origin", "Shipment", "SHPMT", "USD"),
                ("default", "CUS", "Customs Clearance", "Customs", "Shipment", "SHPMT", "THB"),
                ("default", "TRK", "Trucking", "Transport", "Trip", "TRIP", "THB"),
                ("default", "CFS", "CFS Handling", "Handling", "CBM", "CBM", "USD"),
                ("default", "AIR", "Air Freight", "Freight", "KG", "KG", "USD"),
                ("default", "INS", "Insurance", "Other", "Shipment", "SHPMT", "THB"),
            ])
            conn.commit()
