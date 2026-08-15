"""Small additive PostgreSQL compatibility repair for legacy preview databases.

This module only creates missing Phase 30 profitability tables/columns and indexes.
It is intentionally idempotent and does not delete or rewrite existing data.
"""
from __future__ import annotations


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
        cur.execute("ALTER TABLE job_costs ADD COLUMN IF NOT EXISTS tenant_id TEXT DEFAULT 'default'")
        cur.execute("ALTER TABLE job_costs ADD COLUMN IF NOT EXISTS cost_status TEXT DEFAULT 'ESTIMATED'")
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
        cur.execute("ALTER TABLE profit_sheets ADD COLUMN IF NOT EXISTS tenant_id TEXT DEFAULT 'default'")
        cur.execute("UPDATE profit_sheets SET tenant_id='default' WHERE tenant_id IS NULL OR btrim(tenant_id)=''")
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_job_costs_tenant_shipment ON job_costs(tenant_id, shipment_id)"
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_job_costs_tenant_status ON job_costs(tenant_id, cost_type, cost_status)"
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_profit_sheets_tenant_shipment ON profit_sheets(tenant_id, shipment_id)"
        )
    conn.commit()
