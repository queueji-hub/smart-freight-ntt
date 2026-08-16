from pathlib import Path


def test_system_health_contracts_all_production_routes():
    source = Path("views/system_health_view.py").read_text(encoding="utf-8")
    for module in (
        "views.quotation_v2_view",
        "views.booking_v2_view",
        "views.bl_v2_view",
        "views.finance_document_workspace",
        "views.ar_ap_workspace",
        "views.document_v2_view",
        "views.shipment_view",
    ):
        assert module in source
    assert "ALL PRODUCTION INTEGRITY CHECKS PASS" in source


def test_dashboard_exposes_health_workspace():
    source = Path("Dashboard.py").read_text(encoding="utf-8")
    assert '("health", "System Health", "system_health")' in source
    assert '"views.system_health_view"' in source
