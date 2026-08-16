-- Master Data v1: ports, business parties, roles, finance profile, rate cards.
-- Additive/idempotent production contract.

CREATE TABLE IF NOT EXISTS ports (
    id SERIAL PRIMARY KEY, tenant_id TEXT NOT NULL DEFAULT 'default',
    port_code VARCHAR(5) NOT NULL, unlocode VARCHAR(5), port_name TEXT NOT NULL,
    city TEXT, country_code VARCHAR(2), country_name TEXT, timezone TEXT,
    port_type TEXT DEFAULT 'PORT', is_active BOOLEAN NOT NULL DEFAULT TRUE,
    remarks TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (tenant_id, port_code)
);
CREATE INDEX IF NOT EXISTS idx_ports_tenant_active ON ports(tenant_id, is_active);

CREATE TABLE IF NOT EXISTS business_parties (
    id SERIAL PRIMARY KEY, tenant_id TEXT NOT NULL DEFAULT 'default',
    party_code VARCHAR(5) NOT NULL, legal_name TEXT NOT NULL, display_name TEXT,
    short_name TEXT, tax_id TEXT, branch_no TEXT, registration_no TEXT,
    billing_address TEXT, country_code VARCHAR(2), phone TEXT, email TEXT, website TEXT,
    is_active BOOLEAN NOT NULL DEFAULT TRUE, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, UNIQUE (tenant_id, party_code)
);
CREATE INDEX IF NOT EXISTS idx_parties_tenant_active ON business_parties(tenant_id, is_active);
CREATE INDEX IF NOT EXISTS idx_parties_tenant_name ON business_parties(tenant_id, legal_name);

CREATE TABLE IF NOT EXISTS party_roles (
    id SERIAL PRIMARY KEY, tenant_id TEXT NOT NULL DEFAULT 'default', party_id INTEGER NOT NULL,
    role_type TEXT NOT NULL, is_active BOOLEAN NOT NULL DEFAULT TRUE,
    UNIQUE (tenant_id, party_id, role_type)
);
CREATE INDEX IF NOT EXISTS idx_party_roles_lookup ON party_roles(tenant_id, role_type, is_active);

CREATE TABLE IF NOT EXISTS party_finance_profiles (
    id SERIAL PRIMARY KEY, tenant_id TEXT NOT NULL DEFAULT 'default', party_id INTEGER NOT NULL,
    credit_limit NUMERIC(18,2) DEFAULT 0, credit_currency VARCHAR(3) DEFAULT 'THB',
    credit_days INTEGER DEFAULT 0, payment_term_code TEXT, tax_id TEXT,
    vat_registered BOOLEAN DEFAULT FALSE, withholding_tax BOOLEAN DEFAULT FALSE,
    bank_name TEXT, bank_account_name TEXT, bank_account_no TEXT, swift_code TEXT,
    active BOOLEAN DEFAULT TRUE, UNIQUE (tenant_id, party_id)
);

CREATE TABLE IF NOT EXISTS rate_cards (
    id SERIAL PRIMARY KEY, tenant_id TEXT NOT NULL DEFAULT 'default', rate_no TEXT NOT NULL,
    carrier_id INTEGER, origin_port_id INTEGER, destination_port_id INTEGER,
    mode TEXT NOT NULL, service_type TEXT, equipment_type TEXT, currency VARCHAR(3) DEFAULT 'USD',
    valid_from DATE, valid_to DATE, status TEXT DEFAULT 'ACTIVE', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (tenant_id, rate_no)
);
CREATE TABLE IF NOT EXISTS rate_card_lines (
    id SERIAL PRIMARY KEY, tenant_id TEXT NOT NULL DEFAULT 'default', rate_card_id INTEGER NOT NULL,
    charge_id INTEGER, basis TEXT, minimum NUMERIC(18,2) DEFAULT 0, rate NUMERIC(18,2) DEFAULT 0,
    currency VARCHAR(3) DEFAULT 'USD'
);

ALTER TABLE bookings ADD COLUMN IF NOT EXISTS mother_vessel TEXT;
ALTER TABLE bookings ADD COLUMN IF NOT EXISTS booking_date DATE;
CREATE INDEX IF NOT EXISTS idx_bookings_tenant_booking_date ON bookings(tenant_id, booking_date);
