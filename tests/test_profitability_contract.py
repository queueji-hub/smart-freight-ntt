from pathlib import Path

from managers.profit_manager import (
    _resolve_charge_domain,
    get_cost_sell_audit_matrix,
    lock_job_financials,
    unlock_job_financials,
)


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
    assert "SET financial_locked = TRUE" in MANAGER
    assert "SET financial_locked = FALSE" in MANAGER


def test_resolve_charge_domain():
    # Ocean Freight domain
    assert _resolve_charge_domain("", "Ocean Freight Cost", "Carrier Sea Freight") == "ocean_freight"
    assert _resolve_charge_domain("", "Ocean Freight Revenue", "Freight Revenue") == "ocean_freight"
    assert _resolve_charge_domain("OF", "", "") == "ocean_freight"

    # Terminal domain
    assert _resolve_charge_domain("", "Port Terminal Cost", "THC at Port") == "terminal"
    assert _resolve_charge_domain("", "Local Terminal Charges (AR)", "Terminal Handling Charge") == "terminal"

    # Customs domain
    assert _resolve_charge_domain("", "Customs Duty Paid", "Import Duty & Tax") == "customs"
    assert _resolve_charge_domain("", "Customs Clearance Service", "Customs Clearance Fee") == "customs"

    # Trucking domain
    assert _resolve_charge_domain("", "Inland Carrier Expenses", "Trailer drop fee") == "trucking"
    assert _resolve_charge_domain("", "Inland Trucking Revenue", "Delivery to factory") == "trucking"
