from pathlib import Path


def test_finance_document_workspace_contract():
    import views.finance_document_workspace  # noqa: F401
    source = Path("views/finance_document_workspace.py").read_text(encoding="utf-8")
    assert "Billing Note" in source
    assert "Receipt / Tax Invoice" in source
    assert "Credit Note" in source
    assert "Debit Note" in source
    assert "Statement of Account" in source
    assert "get_outstanding_summary" in source
    assert "finance_v2_view" in source


def test_dashboard_routes_billing_to_structured_workspace():
    source = Path("Dashboard.py").read_text(encoding="utf-8")
    assert 'PAGE_ROUTES["billing"] = ("views.finance_document_workspace", "render")' in source
