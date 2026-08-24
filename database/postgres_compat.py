"""Idempotent PostgreSQL compatibility repairs for Phase 30 databases.

All repairs are additive: existing data is preserved. The helpers are intended
for legacy/preview databases that may have received application code before the
corresponding schema migrations.
"""
from __future__ import annotations


def _add_columns(cur, table: str, columns: dict[str, str]) -> None:
    for column, ddl in columns.items():
        cur.execute(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {column} {ddl}")


def _safe_commit(conn) -> None:
    if hasattr(conn, "commit") and callable(getattr(conn, "commit")):
        try:
            conn.commit()
        except Exception:
            pass


def ensure_phase30_quotation_schema(conn) -> None:
    """Ensure all quotation and quotation item columns exist in PostgreSQL."""
    with conn.cursor() as cur:
        columns = {
            "customer_id": "INTEGER",
            "customer_name": "TEXT",
            "customer_address": "TEXT",
            "customer_email": "TEXT",
            "sales_id": "INTEGER",
            "salesperson": "TEXT",
            "status": "TEXT DEFAULT 'Draft'",
            "approval_status": "TEXT DEFAULT 'Draft'",
            "tenant_id": "TEXT DEFAULT 'default'",
            "job_type": "TEXT",
            "service_type": "TEXT",
            "incoterm": "TEXT",
            "freight_term": "TEXT",
            "carrier": "TEXT",
            "pol": "TEXT",
            "pod": "TEXT",
            "origin": "TEXT",
            "destination": "TEXT",
            "commodity": "TEXT",
            "hs_code": "TEXT",
            "quantity": "NUMERIC(15,2) DEFAULT 0",
            "package_type": "TEXT",
            "weight_kg": "NUMERIC(15,2) DEFAULT 0",
            "volume_cbm": "NUMERIC(15,2) DEFAULT 0",
            "container_type": "TEXT",
            "container_quantity": "INTEGER DEFAULT 0",
            "is_dg": "BOOLEAN DEFAULT FALSE",
            "subject": "TEXT",
            "terms_conditions": "TEXT",
            "created_by": "TEXT",
            "updated_by": "TEXT",
        }
        _add_columns(cur, "quotations", columns)
        item_columns = {
            "charge_code": "TEXT",
            "basis": "TEXT",
            "quantity": "NUMERIC(15,3) DEFAULT 1",
            "unit_rate": "NUMERIC(15,2) DEFAULT 0",
            "amount": "NUMERIC(15,2) DEFAULT 0",
        }
        _add_columns(cur, "quotation_items", item_columns)
        try:
            cur.execute("UPDATE quotations SET tenant_id='default' WHERE tenant_id IS NULL OR btrim(tenant_id)=''")
            cur.execute("UPDATE quotations SET status='Draft' WHERE status IS NULL OR btrim(status)=''")
            cur.execute("UPDATE quotations SET approval_status='Draft' WHERE approval_status IS NULL OR btrim(approval_status)=''")
        except Exception:
            pass
    _safe_commit(conn)


def ensure_phase30_shipment_schema(conn) -> None:
    """Ensure all required shipment columns exist in PostgreSQL."""
    with conn.cursor() as cur:
        columns = {
            "status": "TEXT DEFAULT 'Proceed'",
            "job_type": "TEXT",
            "booking_no": "TEXT",
            "customer_id": "INTEGER",
            "customer_name": "TEXT",
            "notify_party": "TEXT",
            "sales_person": "TEXT",
            "operations_owner": "TEXT",
            "customer_reference": "TEXT",
            "quotation_no": "TEXT",
            "shipper": "TEXT",
            "consignee": "TEXT",
            "cargo_type": "TEXT",
            "carrier": "TEXT",
            "place_of_receipt": "TEXT",
            "pol": "TEXT",
            "transshipment_port": "TEXT",
            "pod": "TEXT",
            "place_of_delivery": "TEXT",
            "final_destination": "TEXT",
            "origin_country": "TEXT",
            "destination_country": "TEXT",
            "etd": "DATE",
            "eta": "DATE",
            "actual_departure": "DATE",
            "actual_arrival": "DATE",
            "mbl_no": "TEXT",
            "hbl_no": "TEXT",
            "bl_no": "TEXT",
            "invoice_no": "TEXT",
            "vessel": "TEXT",
            "voyage": "TEXT",
            "mother_vessel": "TEXT",
            "mother_voyage": "TEXT",
            "feeder_vessel": "TEXT",
            "feeder_voyage": "TEXT",
            "incoterm": "TEXT",
            "service_type": "TEXT",
            "freight_term": "TEXT",
            "commodity": "TEXT",
            "hs_code": "TEXT",
            "package_type": "TEXT",
            "package_quantity": "INTEGER DEFAULT 0",
            "gross_weight": "NUMERIC(15,2) DEFAULT 0",
            "net_weight": "NUMERIC(15,2) DEFAULT 0",
            "cbm": "NUMERIC(15,2) DEFAULT 0",
            "chargeable_weight": "NUMERIC(15,2) DEFAULT 0",
            "is_dg": "BOOLEAN DEFAULT FALSE",
            "is_temp_controlled": "BOOLEAN DEFAULT FALSE",
            "special_cargo_remarks": "TEXT",
            "customs_declaration_no": "TEXT",
            "customs_status": "TEXT",
            "customs_broker": "TEXT",
            "customs_clearance_date": "DATE",
            "customer_paid": "BOOLEAN DEFAULT FALSE",
            "remark": "TEXT",
            "reporting_date": "DATE",
            "reporting_month": "TEXT",
            "reporting_year": "TEXT",
            "financial_status": "TEXT DEFAULT 'OPEN'",
            "document_status": "TEXT DEFAULT 'PENDING'",
            "mode": "TEXT",
            "closed_at": "TIMESTAMP",
            "closed_by": "TEXT",
            "created_by": "TEXT",
            "updated_by": "TEXT",
            "financial_locked": "BOOLEAN DEFAULT FALSE",
            "handover_to_accounting_at": "TIMESTAMP",
            "handover_by": "TEXT",
            "tenant_id": "TEXT DEFAULT 'default'",
        }
        _add_columns(cur, "shipments", columns)
        try:
            cur.execute("UPDATE shipments SET tenant_id='default' WHERE tenant_id IS NULL OR btrim(tenant_id)=''")
        except Exception:
            pass
    _safe_commit(conn)


def ensure_phase30_salesperson_schema(conn) -> None:
    """Create/upgrade salespersons table."""
    with conn.cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS salespersons (
                id SERIAL PRIMARY KEY,
                tenant_id TEXT DEFAULT 'default',
                sales_code VARCHAR(20) NOT NULL,
                name TEXT NOT NULL,
                email TEXT,
                phone TEXT,
                commission_rate NUMERIC(5,2) DEFAULT 0,
                remarks TEXT,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE (tenant_id, sales_code)
            )
            """
        )
        _add_columns(cur, "salespersons", {
            "tenant_id": "TEXT DEFAULT 'default'",
            "sales_code": "VARCHAR(20)",
            "name": "TEXT",
            "email": "TEXT",
            "phone": "TEXT",
            "commission_rate": "NUMERIC(5,2) DEFAULT 0",
            "remarks": "TEXT",
            "is_active": "BOOLEAN DEFAULT TRUE",
            "created_at": "TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
            "updated_at": "TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
        })
        try:
            cur.execute("CREATE INDEX IF NOT EXISTS idx_salespersons_active ON salespersons(tenant_id, is_active)")
        except Exception:
            pass
    _safe_commit(conn)


def ensure_phase30_charge_master_schema(conn) -> None:
    """Create/upgrade charge_master table."""
    with conn.cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS charge_master (
                id SERIAL PRIMARY KEY,
                tenant_id TEXT DEFAULT 'default',
                charge_code TEXT NOT NULL,
                description TEXT NOT NULL,
                category TEXT,
                default_basis TEXT,
                default_unit TEXT,
                default_currency TEXT DEFAULT 'USD',
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE (tenant_id, charge_code)
            )
            """
        )
        _add_columns(cur, "charge_master", {
            "tenant_id": "TEXT DEFAULT 'default'",
            "charge_code": "TEXT",
            "description": "TEXT",
            "category": "TEXT",
            "default_basis": "TEXT",
            "default_unit": "TEXT",
            "default_currency": "TEXT DEFAULT 'USD'",
            "is_active": "BOOLEAN DEFAULT TRUE",
            "created_at": "TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
            "updated_at": "TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
        })
        cur.execute("UPDATE charge_master SET tenant_id='default' WHERE tenant_id IS NULL OR btrim(tenant_id)=''")
        cur.execute("UPDATE charge_master SET is_active=TRUE WHERE is_active IS NULL")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_charge_master_active ON charge_master(tenant_id, is_active)")
    _safe_commit(conn)


def ensure_phase30_master_data_schema(conn) -> None:
    """Create/upgrade master data tables (ports, parties, rates)."""
    with conn.cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS ports (
                id SERIAL PRIMARY KEY,
                tenant_id TEXT NOT NULL DEFAULT 'default',
                port_code VARCHAR(5) NOT NULL,
                unlocode VARCHAR(5),
                port_name TEXT NOT NULL,
                city TEXT,
                country_code VARCHAR(2),
                country_name TEXT,
                timezone TEXT,
                port_type TEXT DEFAULT 'PORT',
                is_active BOOLEAN NOT NULL DEFAULT TRUE,
                remarks TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE (tenant_id, port_code)
            )
            """
        )
        cur.execute("CREATE INDEX IF NOT EXISTS idx_ports_tenant_active ON ports(tenant_id, is_active)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_ports_tenant_name ON ports(tenant_id, port_name)")

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS business_parties (
                id SERIAL PRIMARY KEY,
                tenant_id TEXT NOT NULL DEFAULT 'default',
                party_code VARCHAR(5) NOT NULL,
                legal_name TEXT NOT NULL,
                display_name TEXT,
                short_name TEXT,
                tax_id TEXT,
                branch_no TEXT,
                registration_no TEXT,
                billing_address TEXT,
                country_code VARCHAR(2),
                phone TEXT,
                email TEXT,
                website TEXT,
                is_active BOOLEAN NOT NULL DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE (tenant_id, party_code)
            )
            """
        )
        cur.execute("CREATE INDEX IF NOT EXISTS idx_parties_tenant_active ON business_parties(tenant_id, is_active)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_parties_tenant_name ON business_parties(tenant_id, legal_name)")

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS party_roles (
                id SERIAL PRIMARY KEY,
                tenant_id TEXT NOT NULL DEFAULT 'default',
                party_id INTEGER NOT NULL,
                role_type TEXT NOT NULL,
                is_active BOOLEAN NOT NULL DEFAULT TRUE,
                UNIQUE (tenant_id, party_id, role_type)
            )
            """
        )
        cur.execute("CREATE INDEX IF NOT EXISTS idx_party_roles_lookup ON party_roles(tenant_id, role_type, is_active)")

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS party_finance_profiles (
                id SERIAL PRIMARY KEY,
                tenant_id TEXT NOT NULL DEFAULT 'default',
                party_id INTEGER NOT NULL,
                credit_limit NUMERIC(18,2) DEFAULT 0,
                credit_currency VARCHAR(3) DEFAULT 'THB',
                credit_days INTEGER DEFAULT 0,
                payment_term_code TEXT,
                tax_id TEXT,
                vat_registered BOOLEAN DEFAULT FALSE,
                withholding_tax BOOLEAN DEFAULT FALSE,
                bank_name TEXT,
                bank_account_name TEXT,
                bank_account_no TEXT,
                swift_code TEXT,
                active BOOLEAN DEFAULT TRUE,
                UNIQUE (tenant_id, party_id)
            )
            """
        )

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS rate_cards (
                id SERIAL PRIMARY KEY,
                tenant_id TEXT NOT NULL DEFAULT 'default',
                rate_no TEXT NOT NULL,
                carrier_id INTEGER,
                origin_port_id INTEGER,
                destination_port_id INTEGER,
                mode TEXT NOT NULL,
                service_type TEXT,
                equipment_type TEXT,
                currency VARCHAR(3) DEFAULT 'USD',
                valid_from DATE,
                valid_to DATE,
                status TEXT DEFAULT 'ACTIVE',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE (tenant_id, rate_no)
            )
            """
        )

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS rate_card_lines (
                id SERIAL PRIMARY KEY,
                tenant_id TEXT NOT NULL DEFAULT 'default',
                rate_card_id INTEGER NOT NULL,
                charge_id INTEGER,
                basis TEXT,
                minimum NUMERIC(18,2) DEFAULT 0,
                rate NUMERIC(18,2) DEFAULT 0,
                currency VARCHAR(3) DEFAULT 'USD'
            )
            """
        )

        cur.execute("ALTER TABLE bookings ADD COLUMN IF NOT EXISTS mother_vessel TEXT")
        cur.execute("ALTER TABLE bookings ADD COLUMN IF NOT EXISTS booking_date DATE")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_bookings_tenant_booking_date ON bookings(tenant_id, booking_date)")
    _safe_commit(conn)


def ensure_phase30_profitability_schema(conn) -> None:
    """Create/upgrade profitability tables required by profit_manager."""
    with conn.cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS job_costs (
                id SERIAL PRIMARY KEY,
                shipment_id INTEGER NOT NULL,
                tenant_id TEXT DEFAULT 'default',
                cost_type TEXT NOT NULL,
                category TEXT,
                description TEXT,
                supplier TEXT,
                quantity NUMERIC(15,2) DEFAULT 1,
                unit_price NUMERIC(15,2) DEFAULT 0,
                amount NUMERIC(15,2) DEFAULT 0,
                currency TEXT DEFAULT 'THB',
                exchange_rate NUMERIC(10,5) DEFAULT 1,
                amount_thb NUMERIC(15,2) DEFAULT 0,
                cost_status TEXT DEFAULT 'ESTIMATED',
                remark TEXT,
                created_by TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        _add_columns(cur, "job_costs", {
            "tenant_id": "TEXT DEFAULT 'default'",
            "cost_status": "TEXT DEFAULT 'ESTIMATED'",
            "billable_to_customer": "BOOLEAN DEFAULT TRUE",
            "matched_charge_code": "TEXT",
            "vendor_invoice_no": "TEXT",
            "payout_status": "TEXT DEFAULT 'UNPAID'",
        })
        _add_columns(cur, "shipments", {
            "financial_locked": "BOOLEAN DEFAULT FALSE",
            "handover_to_accounting_at": "TIMESTAMP",
            "handover_by": "TEXT",
            "mother_vessel": "TEXT",
            "mother_voyage": "TEXT",
            "feeder_vessel": "TEXT",
            "feeder_voyage": "TEXT",
        })
        cur.execute("UPDATE job_costs SET tenant_id='default' WHERE tenant_id IS NULL OR btrim(tenant_id)=''")
        cur.execute("UPDATE job_costs SET cost_status='ESTIMATED' WHERE cost_status IS NULL OR btrim(cost_status)=''")

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS profit_sheets (
                id SERIAL PRIMARY KEY,
                shipment_id INTEGER NOT NULL,
                tenant_id TEXT DEFAULT 'default',
                sheet_no TEXT UNIQUE NOT NULL,
                total_ar NUMERIC(15,2) DEFAULT 0,
                total_ap NUMERIC(15,2) DEFAULT 0,
                net_profit NUMERIC(15,2) DEFAULT 0,
                profit_margin NUMERIC(5,2) DEFAULT 0,
                prepared_by TEXT,
                reviewed_by TEXT,
                reviewed_at TIMESTAMP,
                approved_by TEXT,
                approved_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        _add_columns(cur, "profit_sheets", {"tenant_id": "TEXT DEFAULT 'default'"})
        cur.execute("UPDATE profit_sheets SET tenant_id='default' WHERE tenant_id IS NULL OR btrim(tenant_id)=''")

        cur.execute("CREATE INDEX IF NOT EXISTS idx_job_costs_tenant_shipment ON job_costs(tenant_id, shipment_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_job_costs_tenant_status ON job_costs(tenant_id, cost_type, cost_status)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_profit_sheets_tenant_shipment ON profit_sheets(tenant_id, shipment_id)")
    _safe_commit(conn)


def ensure_phase30_bl_schema(conn) -> None:
    """Create/upgrade B/L header schema required by the Phase 30 B/L workspace."""
    with conn.cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS bills_of_lading (
                id SERIAL PRIMARY KEY,
                tenant_id TEXT DEFAULT 'default',
                bl_no TEXT,
                job_no TEXT,
                shipment_id INTEGER,
                booking_no TEXT,
                consol_no TEXT,
                consol_seq INTEGER DEFAULT 1,
                shipper TEXT,
                consignee TEXT,
                notify_party TEXT,
                delivery_agent TEXT,
                pre_carriage_by TEXT,
                place_of_receipt TEXT,
                port_of_loading TEXT,
                port_of_discharge TEXT,
                place_of_delivery TEXT,
                final_destination TEXT,
                vessel TEXT,
                voyage TEXT,
                etd DATE,
                eta DATE,
                bl_date DATE,
                place_of_issue TEXT,
                number_of_originals INTEGER DEFAULT 3,
                freight_term TEXT,
                freight_payable_at TEXT,
                marks_numbers TEXT,
                package_qty NUMERIC(15,2) DEFAULT 0,
                package_type TEXT,
                description_of_goods TEXT,
                gross_weight NUMERIC(15,3) DEFAULT 0,
                measurement_cbm NUMERIC(15,3) DEFAULT 0,
                hs_code TEXT,
                remarks TEXT,
                special_instructions TEXT,
                bl_type TEXT DEFAULT 'BL',
                status TEXT DEFAULT 'Draft',
                approval_status TEXT DEFAULT 'Draft',
                created_by TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        columns = {
            "tenant_id": "TEXT DEFAULT 'default'",
            "bl_no": "TEXT",
            "job_no": "TEXT",
            "shipment_id": "INTEGER",
            "booking_no": "TEXT",
            "consol_no": "TEXT",
            "consol_seq": "INTEGER DEFAULT 1",
            "shipper": "TEXT",
            "consignee": "TEXT",
            "notify_party": "TEXT",
            "delivery_agent": "TEXT",
            "pre_carriage_by": "TEXT",
            "place_of_receipt": "TEXT",
            "port_of_loading": "TEXT",
            "port_of_discharge": "TEXT",
            "place_of_delivery": "TEXT",
            "final_destination": "TEXT",
            "vessel": "TEXT",
            "voyage": "TEXT",
            "etd": "DATE",
            "eta": "DATE",
            "bl_date": "DATE",
            "place_of_issue": "TEXT",
            "number_of_originals": "INTEGER DEFAULT 3",
            "freight_term": "TEXT",
            "freight_payable_at": "TEXT",
            "marks_numbers": "TEXT",
            "package_qty": "NUMERIC(15,2) DEFAULT 0",
            "package_type": "TEXT",
            "description_of_goods": "TEXT",
            "gross_weight": "NUMERIC(15,3) DEFAULT 0",
            "measurement_cbm": "NUMERIC(15,3) DEFAULT 0",
            "hs_code": "TEXT",
            "remarks": "TEXT",
            "special_instructions": "TEXT",
            "bl_type": "TEXT DEFAULT 'BL'",
            "status": "TEXT DEFAULT 'Draft'",
            "approval_status": "TEXT DEFAULT 'Draft'",
            "created_by": "TEXT",
            "created_at": "TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
            "updated_at": "TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
        }
        _add_columns(cur, "bills_of_lading", columns)
        cur.execute("UPDATE bills_of_lading SET tenant_id='default' WHERE tenant_id IS NULL OR btrim(tenant_id)=''")
        cur.execute("UPDATE bills_of_lading SET bl_type='BL' WHERE bl_type IS NULL OR btrim(bl_type)=''")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_bills_of_lading_tenant_job ON bills_of_lading(tenant_id, job_no)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_bills_of_lading_tenant_consol ON bills_of_lading(tenant_id, consol_no)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_bills_of_lading_tenant_created ON bills_of_lading(tenant_id, created_at DESC)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_bills_of_lading_tenant_bl_no ON bills_of_lading(tenant_id, bl_no)")
    _safe_commit(conn)


def ensure_phase30_approval_schema(conn) -> None:
    """Ensure approval_status and tenant column constraints are updated across all core document tables."""
    with conn.cursor() as cur:
        for table in ["quotations", "bookings", "invoices", "bills_of_lading"]:
            try:
                _add_columns(cur, table, {"approval_status": "TEXT DEFAULT 'Draft'"})
                cur.execute(f"UPDATE {table} SET approval_status='Draft' WHERE approval_status IS NULL OR btrim(approval_status)=''")
            except Exception:
                pass
        try:
            cur.execute("ALTER TABLE audit_logs ALTER COLUMN tenant_id TYPE TEXT USING tenant_id::TEXT")
        except Exception:
            pass
        try:
            cur.execute("ALTER TABLE audit_logs ALTER COLUMN entity_id TYPE TEXT USING entity_id::TEXT")
        except Exception:
            pass
    _safe_commit(conn)

