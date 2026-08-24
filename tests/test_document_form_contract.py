from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _text(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_bl_workspace_uses_company_renderer():
    source = _text("views/bl_v2_view.py")
    assert "assemble_bl_document_payload" in source
    assert "generate_company_bl_pdf" in source
    assert "pdf.bl_pdf" not in source
    for label in ("Shipper", "Consignee", "Notify Party", "Ocean Vessel", "Voyage No.", "Port of Loading", "Port of Discharge", "No. of Packages", "Gross Weight Kgs", "Measurement CBM", "Freight payable at", "Number of original B/Ls"):
        assert label in source


def test_bl_renderer_matches_reference_sections():
    source = _text("pdf/bl_document_renderer.py")
    for marker in ("Shipper", "Consignee", "Notify Party", "Ocean Vessel/Voyage No.", "Port of Loading", "Port of Discharge", "No. of Packages", "Gross Weight Kgs", "Measurement CBM", "Freight and Disbursements", "Number of original B/Ls"):
        assert marker in source


def test_finance_workspace_has_document_register_and_preview():
    source = _text("views/finance_document_workspace.py")
    for marker in ("Document Type", "Issue Date", "Due Date", "Reference", "Document Actions", "Document Preview", "Grand Total", "Outstanding", "Payer / Receiver", "Authorized Signature"):
        assert marker in source


def test_finance_pdf_contains_reference_document_types():
    source = _text("pdf/invoice_pdf.py")
    assert "ใบเสร็จรับเงิน / ใบกำกับภาษี" in source
    assert "ใบวางบิล" in source
    assert "Original" in source
    assert "Copy" in source
    assert "generate_invoice_pdf(" in source


def test_dashboard_routes_current_workspaces():
    source = _text("Dashboard.py")
    assert '"booking"' in source
    assert '"bl"' in source
    assert '"billing"' in source
    assert "views.bl_v2_view" in source
    assert "views.finance_document_workspace" in source
