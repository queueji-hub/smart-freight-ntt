from pathlib import Path


MIGRATION = Path("database/migrations/20260815_payables_contract.sql").read_text(encoding="utf-8")


def test_payables_tables_and_indexes_exist_in_migration():
    assert "CREATE TABLE IF NOT EXISTS vendors" in MIGRATION
    assert "CREATE TABLE IF NOT EXISTS ap_vouchers" in MIGRATION
    assert "tenant_id TEXT NOT NULL DEFAULT 'default'" in MIGRATION
    assert "idx_ap_vouchers_tenant_job" in MIGRATION
    assert "idx_vendors_tenant_name" in MIGRATION
