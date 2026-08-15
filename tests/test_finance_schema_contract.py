from pathlib import Path


MIGRATION = Path("database/migrations/20260815_phase30_ssot_workflow.sql").read_text(encoding="utf-8")


def test_finance_migration_has_tenant_and_approval_columns():
    assert "ALTER TABLE invoices" in MIGRATION
    assert "ADD COLUMN IF NOT EXISTS tenant_id TEXT" in MIGRATION
    assert "ADD COLUMN IF NOT EXISTS approval_status TEXT DEFAULT 'Draft'" in MIGRATION
    assert "ALTER TABLE bills_of_lading" in MIGRATION


def test_finance_migration_has_tenant_indexes():
    assert "idx_invoices_tenant_customer" in MIGRATION
    assert "idx_bills_of_lading_tenant_job" in MIGRATION
