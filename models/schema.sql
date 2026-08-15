-- =====================================================
-- SMART FREIGHT NTT
-- CANONICAL POSTGRESQL PRODUCTION SCHEMA
-- =====================================================

-- This file remains the canonical baseline. Incremental production changes are
-- applied via database/migrations/*.sql.

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
);

CREATE INDEX IF NOT EXISTS idx_charge_master_active
    ON charge_master(tenant_id, is_active);

-- Existing production schema continues below through the migration chain.
