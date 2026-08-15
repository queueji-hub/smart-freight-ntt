from pathlib import Path


def test_document_v2_routes_to_job_documents():
    import views.document_v2_view  # noqa: F401
    source = Path("views/document_v2_view.py").read_text(encoding="utf-8")
    assert "list_shipments" in source
    assert "generate_booking_pdf" in source
    assert "generate_bl_pdf" in source
    assert "generate_invoice_pdf" in source
    assert "generate_profitability_pdf" in source


def test_document_v2_has_no_upload_widget():
    source = Path("views/document_v2_view.py").read_text(encoding="utf-8")
    assert "file_uploader" not in source
