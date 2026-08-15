from pathlib import Path


MIGRATION = Path("database/migrations/20260815_profitability_tenant_contract.sql").read_text(encoding="utf-8")
MANAGER = Path("managers/profit_manager.py").read_text(encoding="utf-8")


def test_profitability_migration_adds_tenant_and_cost_status():
    assert "ADD COLUMN IF NOT EXISTS tenant_id TEXT" in MIGRATION
    assert "ADD COLUMN IF NOT EXISTS cost_status TEXT DEFAULT 'ESTIMATED'" in MIGRATION
    assert "idx_job_costs_tenant_shipment" in MIGRATION
    assert "idx_profit_sheets_tenant_shipment" in MIGRATION


def test_profit_manager_filters_job_costs_by_tenant():
    assert "WHERE shipment_id=%s AND tenant_id=%s" in MANAGER
    assert "WHERE id=%s AND tenant_id=%s" in MANAGER
    assert "INSERT INTO job_costs" in MANAGER
    assert "INSERT INTO profit_sheets" in MANAGER
