"""Additive PostgreSQL compatibility repairs for legacy/preview databases."""
from __future__ import annotations


def ensure_phase30_profitability_schema(conn) -> None:
    with conn.cursor() as cur:
        cur.execute("CREATE TABLE IF NOT EXISTS job_costs (id SERIAL PRIMARY KEY, shipment_id INTEGER NOT NULL, tenant_id TEXT DEFAULT 'default', cost_type TEXT NOT NULL, category TEXT, description TEXT, supplier TEXT, quantity NUMERIC(15,2) DEFAULT 1, unit_price NUMERIC(15,2) DEFAULT 0, amount NUMERIC(15,2) DEFAULT 0, currency TEXT DEFAULT 'THB', exchange_rate NUMERIC(10,5) DEFAULT 1, amount_thb NUMERIC(15,2) DEFAULT 0, cost_status TEXT DEFAULT 'ESTIMATED', remark TEXT, created_by TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
        cur.execute("ALTER TABLE job_costs ADD COLUMN IF NOT EXISTS tenant_id TEXT DEFAULT 'default'")
        cur.execute("ALTER TABLE job_costs ADD COLUMN IF NOT EXISTS cost_status TEXT DEFAULT 'ESTIMATED'")
        cur.execute("UPDATE job_costs SET tenant_id='default' WHERE tenant_id IS NULL OR btrim(tenant_id)=''")
        cur.execute("UPDATE job_costs SET cost_status='ESTIMATED' WHERE cost_status IS NULL OR btrim(cost_status)=''")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_job_costs_tenant_shipment ON job_costs(tenant_id, shipment_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_job_costs_tenant_status ON job_costs(tenant_id, cost_type, cost_status)")
        cur.execute("CREATE TABLE IF NOT EXISTS profit_sheets (id SERIAL PRIMARY KEY, shipment_id INTEGER NOT NULL, tenant_id TEXT DEFAULT 'default', sheet_no TEXT UNIQUE NOT NULL, total_ar NUMERIC(15,2) DEFAULT 0, total_ap NUMERIC(15,2) DEFAULT 0, net_profit NUMERIC(15,2) DEFAULT 0, profit_margin NUMERIC(5,2) DEFAULT 0, prepared_by TEXT, reviewed_by TEXT, reviewed_at TIMESTAMP, approved_by TEXT, approved_at TIMESTAMP, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
        cur.execute("ALTER TABLE profit_sheets ADD COLUMN IF NOT EXISTS tenant_id TEXT DEFAULT 'default'")
        cur.execute("UPDATE profit_sheets SET tenant_id='default' WHERE tenant_id IS NULL OR btrim(tenant_id)=''")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_profit_sheets_tenant_shipment ON profit_sheets(tenant_id, shipment_id)")
    conn.commit()


def ensure_phase30_bl_schema(conn) -> None:
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS bills_of_lading (
                id SERIAL PRIMARY KEY, tenant_id TEXT DEFAULT 'default', bl_no TEXT, job_no TEXT, shipment_id INTEGER,
                booking_no TEXT, consol_no TEXT, consol_seq INTEGER DEFAULT 1,
                shipper TEXT, consignee TEXT, notify_party TEXT, delivery_agent TEXT, pre_carriage_by TEXT,
                place_of_receipt TEXT, port_of_loading TEXT, port_of_discharge TEXT, place_of_delivery TEXT,
                final_destination TEXT, vessel TEXT, voyage TEXT, etd DATE, eta DATE, bl_date DATE,
                place_of_issue TEXT, number_of_originals INTEGER DEFAULT 3, freight_term TEXT,
                freight_payable_at TEXT, marks_numbers TEXT, package_qty NUMERIC(15,2) DEFAULT 0, package_type TEXT,
                description_of_goods TEXT, gross_weight NUMERIC(15,3) DEFAULT 0, measurement_cbm NUMERIC(15,3) DEFAULT 0,
                hs_code TEXT, remarks TEXT, special_instructions TEXT, bl_type TEXT DEFAULT 'BL',
                status TEXT DEFAULT 'Draft', approval_status TEXT DEFAULT 'Draft', created_by TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        columns = {
            "tenant_id":"TEXT DEFAULT 'default'", "bl_no":"TEXT", "job_no":"TEXT", "shipment_id":"INTEGER", "booking_no":"TEXT",
            "consol_no":"TEXT", "consol_seq":"INTEGER DEFAULT 1", "shipper":"TEXT", "consignee":"TEXT", "notify_party":"TEXT",
            "delivery_agent":"TEXT", "pre_carriage_by":"TEXT", "place_of_receipt":"TEXT", "port_of_loading":"TEXT",
            "port_of_discharge":"TEXT", "place_of_delivery":"TEXT", "final_destination":"TEXT", "vessel":"TEXT", "voyage":"TEXT",
            "etd":"DATE", "eta":"DATE", "bl_date":"DATE", "place_of_issue":"TEXT", "number_of_originals":"INTEGER DEFAULT 3",
            "freight_term":"TEXT", "freight_payable_at":"TEXT", "marks_numbers":"TEXT", "package_qty":"NUMERIC(15,2) DEFAULT 0",
            "package_type":"TEXT", "description_of_goods":"TEXT", "gross_weight":"NUMERIC(15,3) DEFAULT 0", "measurement_cbm":"NUMERIC(15,3) DEFAULT 0",
            "hs_code":"TEXT", "remarks":"TEXT", "special_instructions":"TEXT", "bl_type":"TEXT DEFAULT 'BL'", "status":"TEXT DEFAULT 'Draft'",
            "approval_status":"TEXT DEFAULT 'Draft'", "created_by":"TEXT", "created_at":"TIMESTAMP DEFAULT CURRENT_TIMESTAMP", "updated_at":"TIMESTAMP DEFAULT CURRENT_TIMESTAMP"
        }
        for column, ddl in columns.items():
            cur.execute(f"ALTER TABLE bills_of_lading ADD COLUMN IF NOT EXISTS {column} {ddl}")
        cur.execute("UPDATE bills_of_lading SET tenant_id='default' WHERE tenant_id IS NULL OR btrim(tenant_id)=''")
        cur.execute("UPDATE bills_of_lading SET bl_type='BL' WHERE bl_type IS NULL OR btrim(bl_type)=''")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_bills_of_lading_tenant_job ON bills_of_lading(tenant_id, job_no)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_bills_of_lading_tenant_consol ON bills_of_lading(tenant_id, consol_no)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_bills_of_lading_tenant_created ON bills_of_lading(tenant_id, created_at DESC)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_bills_of_lading_tenant_bl_no ON bills_of_lading(tenant_id, bl_no)")
    conn.commit()
