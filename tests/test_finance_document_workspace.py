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


def test_finance_v2_and_workspace_api_surface():
    import views.finance_v2_view as fin
    import views.finance_document_workspace as fdw

    assert hasattr(fin, "_status")
    assert callable(fin._status)
    assert hasattr(fin, "_payments")
    assert callable(fin._payments)
    assert hasattr(fin, "_pdf")
    assert callable(fin._pdf)
    assert hasattr(fin, "_new")
    assert callable(fin._new)
    assert hasattr(fin, "_edit")
    assert callable(fin._edit)
    assert hasattr(fin, "DOC_TYPES")
    assert hasattr(fdw, "render")
    assert callable(fdw.render)
