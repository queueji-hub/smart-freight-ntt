"""Phase 30 database compatibility helpers.

Production PostgreSQL remains migration-driven, while this helper keeps local
and test SQLite databases compatible with the Phase 30 contract.
"""
from __future__ import annotations

from database.connection import get_connection
from database.postgres_compat import (
    ensure_phase30_quotation_schema,
    ensure_phase30_booking_schema,
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
            ensure_phase30_booking_schema(conn)
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
                "quotations": {"sales_id": "INTEGER", "approval_status": "TEXT DEFAULT 'Draft'", "shipper": "TEXT", "consignee": "TEXT", "transhipment_port": "TEXT"},
                "quotation_items": {"charge_code": "TEXT", "basis": "TEXT", "quantity": "REAL DEFAULT 1", "unit_rate": "REAL DEFAULT 0", "amount": "REAL DEFAULT 0"},
                "bookings": {"sales_id": "INTEGER", "approval_status": "TEXT DEFAULT 'Draft'", "carrier_booking_no": "TEXT", "mother_vessel": "TEXT", "m_vessel": "TEXT", "mother_voyage": "TEXT", "m_voyage": "TEXT", "feeder_vessel": "TEXT", "feeder_voyage": "TEXT", "booking_date": "TEXT", "mode": "TEXT", "service_term": "TEXT", "service_type": "TEXT", "flight_no": "TEXT", "flight_date": "TEXT", "mawb_no": "TEXT", "hawb_no": "TEXT", "truck_type": "TEXT", "truck_plate": "TEXT", "driver_name": "TEXT", "driver_phone": "TEXT", "loading_date": "TEXT", "delivery_date": "TEXT", "chargeable_weight": "REAL DEFAULT 0", "is_locked": "INTEGER DEFAULT 0", "locked_by": "TEXT", "locked_at": "TEXT"},
                "shipments": {"service_type": "TEXT", "mother_vessel": "TEXT", "mother_voyage": "TEXT", "feeder_vessel": "TEXT", "feeder_voyage": "TEXT", "financial_locked": "INTEGER DEFAULT 0", "handover_to_accounting_at": "TEXT", "handover_by": "TEXT", "mbl_no": "TEXT", "hbl_no": "TEXT"},
                "invoices": {"approval_status": "TEXT DEFAULT 'Draft'", "service_type": "TEXT", "feeder_vessel": "TEXT", "vessel_voyage": "TEXT", "pol": "TEXT", "pod": "TEXT", "delivery_port": "TEXT", "mbl_mawb_no": "TEXT", "hbl_hawb_no": "TEXT", "master_job_no": "TEXT", "shipment_no": "TEXT", "tax_receipt_no": "TEXT", "csr_report_no": "TEXT", "total_advance": "REAL DEFAULT 0", "less_vat_sub": "REAL DEFAULT 0", "plus_wht_diff": "REAL DEFAULT 0", "amount_no_vat": "REAL DEFAULT 0", "amount_vat": "REAL DEFAULT 0", "vat_7_amount": "REAL DEFAULT 0", "wht_1_amount": "REAL DEFAULT 0", "wht_3_amount": "REAL DEFAULT 0", "diff_amount": "REAL DEFAULT 0", "net_payable": "REAL DEFAULT 0", "customer_address": "TEXT", "customer_tax_id": "TEXT", "customer_branch": "TEXT"},
                "invoice_items": {"charge_id": "TEXT", "pc_type": "TEXT DEFAULT 'PP-E'", "price": "REAL DEFAULT 0", "curr": "TEXT DEFAULT 'THB'", "exch_rate": "REAL DEFAULT 1", "unit": "TEXT DEFAULT 'M3'", "vat_rate": "REAL DEFAULT 7", "wht_rate": "REAL DEFAULT 0"},
                "invoice_payments": {"pay_by": "TEXT DEFAULT 'Bank Transfer'", "chq_no": "TEXT", "chq_date": "TEXT", "bank_name": "TEXT", "branch_name": "TEXT", "account_type": "TEXT", "wht_cert_no": "TEXT", "wht_cert_date": "TEXT", "wht_amount": "REAL DEFAULT 0"},
                "bills_of_lading": {"tenant_id": "TEXT DEFAULT 'default'", "approval_status": "TEXT DEFAULT 'Draft'", "consol_no": "TEXT", "consol_seq": "INTEGER DEFAULT 1", "bl_type": "TEXT DEFAULT 'BL'", "delivery_agent": "TEXT", "pre_carriage_by": "TEXT", "freight_payable_at": "TEXT", "place_of_issue": "TEXT", "number_of_originals": "INTEGER DEFAULT 3"},
                "job_costs": {"tenant_id": "TEXT DEFAULT 'default'", "party_id": "INTEGER", "line_no": "INTEGER DEFAULT 1", "unit": "TEXT DEFAULT 'UNIT'", "cost_status": "TEXT DEFAULT 'ESTIMATED'", "billable_to_customer": "INTEGER DEFAULT 1", "matched_charge_code": "TEXT", "vendor_invoice_no": "TEXT", "vendor_invoice_date": "TEXT", "payout_status": "TEXT DEFAULT 'UNPAID'", "billing_status": "TEXT DEFAULT 'UNBILLED'", "tax_type": "TEXT DEFAULT 'VAT 7%'", "vat_amount": "REAL DEFAULT 0", "wht_type": "TEXT DEFAULT 'None'", "wht_amount": "REAL DEFAULT 0", "net_amount": "REAL DEFAULT 0", "voucher_no": "TEXT", "invoice_no": "TEXT", "matched_ap_id": "INTEGER"},
                "ap_vouchers": {"tenant_id": "TEXT DEFAULT 'default'", "party_id": "INTEGER", "voucher_no": "TEXT", "voucher_type": "TEXT DEFAULT 'PAYMENT_VOUCHER'", "payment_type": "TEXT DEFAULT 'General Payment'", "service_type": "TEXT", "job_no": "TEXT", "ref_master_job_no": "TEXT", "ref_shipment_no": "TEXT", "ref_purchase_no": "TEXT", "vendor_id": "INTEGER", "supplier_name": "TEXT", "supplier_tax_id": "TEXT", "payee_name": "TEXT", "payee_tax_id": "TEXT", "vendor_invoice_refs": "TEXT", "invoice_no": "TEXT", "invoice_date": "TEXT", "due_date": "TEXT", "payment_date": "TEXT", "currency": "TEXT DEFAULT 'THB'", "exchange_rate": "REAL DEFAULT 1", "amount_no_vat": "REAL DEFAULT 0", "amount_vat": "REAL DEFAULT 0", "subtotal": "REAL DEFAULT 0", "tax": "REAL DEFAULT 0", "wht_total": "REAL DEFAULT 0", "less_vat_diff": "REAL DEFAULT 0", "plus_wht_diff": "REAL DEFAULT 0", "diff_amount": "REAL DEFAULT 0", "total": "REAL DEFAULT 0", "net_payable": "REAL DEFAULT 0", "paid_by": "TEXT DEFAULT 'Bank Transfer'", "paid_amount": "REAL DEFAULT 0", "chq_no": "TEXT", "chq_date": "TEXT", "bank_name": "TEXT", "branch_name": "TEXT", "supplier_tax_inv_no": "TEXT", "supplier_tax_inv_date": "TEXT", "supplier_tax_inv_branch": "TEXT", "supplier_tax_inv_base": "REAL DEFAULT 0", "supplier_tax_inv_vat": "REAL DEFAULT 0", "wht_cert_no": "TEXT", "wht_cert_date": "TEXT", "wht_pnd_type": "TEXT DEFAULT '53'", "wht_base_amount": "REAL DEFAULT 0", "wht_tax_amount": "REAL DEFAULT 0", "wht_payer_tax_id": "TEXT", "wht_payer_name": "TEXT", "status": "TEXT DEFAULT 'REQUESTED'", "remark": "TEXT", "created_by": "TEXT"},
                "profit_sheets": {"tenant_id": "TEXT DEFAULT 'default'"},
                "charge_master": {"default_tax_type": "TEXT DEFAULT 'VAT 7%'", "default_wht_type": "TEXT DEFAULT 'None'"},
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
                "CREATE TABLE IF NOT EXISTS ap_vouchers (id INTEGER PRIMARY KEY AUTOINCREMENT, tenant_id TEXT DEFAULT 'default', party_id INTEGER, voucher_no TEXT, voucher_type TEXT DEFAULT 'PAYMENT_VOUCHER', payment_type TEXT DEFAULT 'General Payment', service_type TEXT, job_no TEXT, ref_master_job_no TEXT, ref_shipment_no TEXT, ref_purchase_no TEXT, vendor_id INTEGER, supplier_name TEXT, supplier_tax_id TEXT, payee_name TEXT, payee_tax_id TEXT, vendor_invoice_refs TEXT, invoice_no TEXT, invoice_date TEXT, due_date TEXT, payment_date TEXT, currency TEXT DEFAULT 'THB', exchange_rate REAL DEFAULT 1, amount_no_vat REAL DEFAULT 0, amount_vat REAL DEFAULT 0, subtotal REAL DEFAULT 0, tax REAL DEFAULT 0, wht_total REAL DEFAULT 0, less_vat_diff REAL DEFAULT 0, plus_wht_diff REAL DEFAULT 0, diff_amount REAL DEFAULT 0, total REAL DEFAULT 0, net_payable REAL DEFAULT 0, paid_by TEXT DEFAULT 'Bank Transfer', paid_amount REAL DEFAULT 0, chq_no TEXT, chq_date TEXT, bank_name TEXT, branch_name TEXT, supplier_tax_inv_no TEXT, supplier_tax_inv_date TEXT, supplier_tax_inv_branch TEXT, supplier_tax_inv_base REAL DEFAULT 0, supplier_tax_inv_vat REAL DEFAULT 0, wht_cert_no TEXT, wht_cert_date TEXT, wht_pnd_type TEXT DEFAULT '53', wht_base_amount REAL DEFAULT 0, wht_tax_amount REAL DEFAULT 0, wht_payer_tax_id TEXT, wht_payer_name TEXT, status TEXT DEFAULT 'REQUESTED', remark TEXT, created_by TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP, updated_at TEXT DEFAULT CURRENT_TIMESTAMP)",
                "CREATE TABLE IF NOT EXISTS ap_voucher_items (id INTEGER PRIMARY KEY AUTOINCREMENT, tenant_id TEXT DEFAULT 'default', voucher_id INTEGER, service_id TEXT, service_text TEXT, amount REAL DEFAULT 0, vat_rate REAL DEFAULT 7, has_tax INTEGER DEFAULT 1, wht_rate REAL DEFAULT 0, pr_no TEXT, master_job TEXT, sort_order INTEGER DEFAULT 0, created_at TEXT DEFAULT CURRENT_TIMESTAMP)",
                "CREATE TABLE IF NOT EXISTS salespersons (id INTEGER PRIMARY KEY AUTOINCREMENT, tenant_id TEXT DEFAULT 'default', sales_code TEXT NOT NULL, name TEXT NOT NULL, email TEXT, phone TEXT, commission_rate REAL DEFAULT 0, remarks TEXT, is_active INTEGER DEFAULT 1, created_at TEXT DEFAULT CURRENT_TIMESTAMP, updated_at TEXT DEFAULT CURRENT_TIMESTAMP, UNIQUE(tenant_id, sales_code))",
                "CREATE TABLE IF NOT EXISTS ports (id INTEGER PRIMARY KEY AUTOINCREMENT, tenant_id TEXT DEFAULT 'default', port_code TEXT NOT NULL, unlocode TEXT, port_name TEXT NOT NULL, city TEXT, country_code TEXT, country_name TEXT, timezone TEXT, port_type TEXT DEFAULT 'PORT', is_active INTEGER DEFAULT 1, remarks TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP, updated_at TEXT DEFAULT CURRENT_TIMESTAMP, UNIQUE(tenant_id, port_code))",
                "CREATE TABLE IF NOT EXISTS business_parties (id INTEGER PRIMARY KEY AUTOINCREMENT, tenant_id TEXT DEFAULT 'default', party_code TEXT NOT NULL, legal_name TEXT NOT NULL, display_name TEXT, short_name TEXT, tax_id TEXT, branch_no TEXT, registration_no TEXT, billing_address TEXT, country_code TEXT, phone TEXT, email TEXT, website TEXT, is_active INTEGER DEFAULT 1, created_at TEXT DEFAULT CURRENT_TIMESTAMP, updated_at TEXT DEFAULT CURRENT_TIMESTAMP, UNIQUE(tenant_id, party_code))",
                "CREATE TABLE IF NOT EXISTS party_roles (id INTEGER PRIMARY KEY AUTOINCREMENT, tenant_id TEXT DEFAULT 'default', party_id INTEGER NOT NULL, role_type TEXT NOT NULL, is_active INTEGER DEFAULT 1, UNIQUE(tenant_id, party_id, role_type))",
                "CREATE TABLE IF NOT EXISTS party_finance_profiles (id INTEGER PRIMARY KEY AUTOINCREMENT, tenant_id TEXT DEFAULT 'default', party_id INTEGER NOT NULL, credit_limit REAL DEFAULT 0, credit_currency TEXT DEFAULT 'THB', credit_days INTEGER DEFAULT 0, payment_term_code TEXT, tax_id TEXT, vat_registered INTEGER DEFAULT 0, withholding_tax INTEGER DEFAULT 0, bank_name TEXT, bank_account_name TEXT, bank_account_no TEXT, swift_code TEXT, active INTEGER DEFAULT 1, UNIQUE(tenant_id, party_id))",
                "CREATE TABLE IF NOT EXISTS rate_cards (id INTEGER PRIMARY KEY AUTOINCREMENT, tenant_id TEXT DEFAULT 'default', rate_no TEXT NOT NULL, carrier_id INTEGER, origin_port_id INTEGER, destination_port_id INTEGER, mode TEXT NOT NULL, service_type TEXT, equipment_type TEXT, currency TEXT DEFAULT 'USD', valid_from TEXT, valid_to TEXT, status TEXT DEFAULT 'ACTIVE', created_at TEXT DEFAULT CURRENT_TIMESTAMP, UNIQUE(tenant_id, rate_no))",
                "CREATE TABLE IF NOT EXISTS rate_card_lines (id INTEGER PRIMARY KEY AUTOINCREMENT, tenant_id TEXT DEFAULT 'default', rate_card_id INTEGER NOT NULL, charge_id INTEGER, basis TEXT, minimum REAL DEFAULT 0, rate REAL DEFAULT 0, currency TEXT DEFAULT 'USD')",
            ]:
                cur.execute(ddl)

            cur.execute("""CREATE TABLE IF NOT EXISTS charge_master (id INTEGER PRIMARY KEY AUTOINCREMENT, tenant_id TEXT DEFAULT 'default', charge_code TEXT NOT NULL, description TEXT NOT NULL, category TEXT, default_basis TEXT, default_unit TEXT, default_currency TEXT DEFAULT 'USD', default_tax_type TEXT DEFAULT 'VAT 7%', default_wht_type TEXT DEFAULT 'None', is_active INTEGER DEFAULT 1, created_at TEXT DEFAULT CURRENT_TIMESTAMP, updated_at TEXT DEFAULT CURRENT_TIMESTAMP, UNIQUE (tenant_id, charge_code))""")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_charge_master_active ON charge_master(tenant_id, is_active)")
            cur.executemany("INSERT OR IGNORE INTO charge_master (tenant_id, charge_code, description, category, default_basis, default_unit, default_currency, default_tax_type, default_wht_type) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", [
                ("default", "OF", "Ocean Freight", "Ocean Freight Cost (สายเรือ)", "Container", "CTR", "USD", "Non-VAT", "None"),
                ("default", "THC-O", "Terminal Handling Charge Origin (THC)", "Port Terminal Cost (THC / ท่าเรือ)", "Container", "CTR", "THB", "VAT 7%", "WHT 1%"),
                ("default", "THC-D", "Terminal Handling Charge Destination (THC)", "Port Terminal Cost (THC / ท่าเรือ)", "Container", "CTR", "THB", "VAT 7%", "WHT 1%"),
                ("default", "CUS", "Customs Clearance & Formalities", "Customs Brokerage Cost (พิธีการศุลกากร)", "Shipment", "SHPT", "THB", "VAT 7%", "WHT 3%"),
                ("default", "TRK", "Inland Transport & Container Trucking", "Inland Transport / Trucking (รถหัวลาก/ขนส่ง)", "Trip", "TRIP", "THB", "VAT 7%", "WHT 1%"),
                ("default", "STO", "Port Storage & Demurrage Fee", "Port Storage / Demurrage / Detention", "Lot", "LOT", "THB", "VAT 7%", "None"),
                ("default", "DO", "Delivery Order (D/O) & Documentation", "Documentation / D/O Cost", "Bill of Lading", "BL", "THB", "VAT 7%", "WHT 3%"),
                ("default", "ADV-DUTY", "Customs Import Duty (เงินทดรองจ่ายภาษีศุลกากร)", "Advance Paid on Behalf (สำรองจ่าย)", "Shipment", "SHPT", "THB", "Advance", "None"),
                ("default", "CFS", "CFS Cargo Handling Fee", "Cargo Handling / CFS", "CBM", "CBM", "THB", "VAT 7%", "WHT 3%"),
                ("default", "AIR", "Air Freight Cargo", "Air Freight Cost (สายการบิน)", "Gross Weight", "KG", "USD", "Non-VAT", "None"),
                ("default", "FSC", "Fuel Surcharge (BAF/FAF)", "Surcharge & Fuel", "Container", "CTR", "USD", "Non-VAT", "None"),
                ("default", "SEC", "Port Security & Screening Fee", "Port Terminal Cost (THC / ท่าเรือ)", "Container", "CTR", "THB", "VAT 7%", "WHT 1%"),
                ("default", "INS", "Marine Cargo Insurance", "Insurance & Other", "Shipment", "SHPT", "THB", "Non-VAT", "None"),
            ])
            conn.commit()
