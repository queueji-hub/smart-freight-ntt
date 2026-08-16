from pathlib import Path


def test_bl_v2_view_and_service_exist():
    import views.bl_v2_view  # noqa: F401
    import managers.bl_workflow_service  # noqa: F401


def test_bl_workspace_keeps_pdf_deferred():
    source = Path("views/bl_v2_view.py").read_text(encoding="utf-8")
    assert "from pdf.bl_pdf import generate_bl_pdf" in source
    assert source.index("from pdf.bl_pdf import generate_bl_pdf") > source.index("def _pdf")
