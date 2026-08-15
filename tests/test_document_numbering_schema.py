from pathlib import Path


MIGRATION = Path("database/migrations/20260815_document_numbering_tenant.sql").read_text(encoding="utf-8")


def test_document_counters_has_tenant_column_and_composite_key():
    assert "ADD COLUMN IF NOT EXISTS tenant_id TEXT" in MIGRATION
    assert "PRIMARY KEY (tenant_id, doc_type, yymm)" in MIGRATION


def test_document_counters_has_tenant_index():
    assert "idx_document_counters_tenant" in MIGRATION
