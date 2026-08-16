from pathlib import Path


def test_bl_schema_contract_contains_required_runtime_columns():
    root = Path(__file__).resolve().parents[1]
    migration = root / "database" / "migrations" / "20260815_bills_of_lading_phase30_contract.sql"
    text = migration.read_text(encoding="utf-8")

    required = {
        "tenant_id",
        "approval_status",
        "bl_no",
        "job_no",
        "shipment_id",
        "booking_no",
        "vessel",
        "voyage",
        "etd",
        "eta",
    }
    for column in required:
        assert column in text


def test_bl_runtime_repair_exists():
    root = Path(__file__).resolve().parents[1]
    compat = root / "database" / "postgres_compat.py"
    service = root / "managers" / "bl_workflow_service.py"
    compat_text = compat.read_text(encoding="utf-8")
    service_text = service.read_text(encoding="utf-8")

    assert "def ensure_phase30_bl_schema" in compat_text
    assert "ensure_phase30_bl_schema(conn)" in service_text
