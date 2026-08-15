-- Canonical Charge Master for pricing / billing / profitability SSOT.
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

INSERT INTO charge_master
    (tenant_id, charge_code, description, category, default_basis, default_unit, default_currency)
VALUES
    ('default', 'OF',  'Ocean Freight',             'Freight',   'Shipment', 'SHPMT', 'USD'),
    ('default', 'THC', 'Terminal Handling Charge',  'Origin',    'Container','CTR',   'USD'),
    ('default', 'DOC', 'Documentation',             'Origin',    'Shipment', 'SHPMT', 'USD'),
    ('default', 'CUS', 'Customs Clearance',         'Customs',   'Shipment', 'SHPMT', 'THB'),
    ('default', 'TRK', 'Trucking',                  'Transport', 'Trip',     'TRIP',  'THB'),
    ('default', 'CFS', 'CFS Handling',              'Handling',  'CBM',      'CBM',   'USD'),
    ('default', 'AIR', 'Air Freight',               'Freight',   'KG',       'KG',    'USD'),
    ('default', 'INS', 'Insurance',                 'Other',     'Shipment', 'SHPMT', 'THB')
ON CONFLICT (tenant_id, charge_code) DO NOTHING;
