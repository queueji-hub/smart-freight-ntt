from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _text(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_dashboard_exposes_core_production_routes():
    source = _text("Dashboard.py")
    for marker in ("current_navigation", '"quotation"', '"booking"', '"bl"', '"billing"', '"rates"'):
        assert marker in source


def test_quote_uses_master_ports_and_rate_lookup():
    source = _text("views/quotation_v2_view.py")
    assert "list_ports" in source
    assert "list_parties(\"CARRIER\"" in source
    assert "find_applicable_rates" in source
    assert "Charge Master" in source


def test_rate_lookup_returns_canonical_charge_metadata():
    source = _text("managers/rate_lookup_service.py")
    assert "charge_master" in source
    assert "charge_code" in source
    assert "charge_description" in source
    assert "tenant_id" in source


def test_job_handover_is_approval_gated_and_id_canonical():
    source = _text("managers/job_handover_service.py")
    assert "Only approved quotations" in source
    assert "customer_id" in source
    assert "sales_id" in source
    assert "_master_labels" in source


def test_billing_and_billing_documents_remain_split_from_pdf_engine():
    source = _text("pdf/bl_document_renderer.py")
    assert "get_connection" not in source
    assert "psycopg2" not in source
