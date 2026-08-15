from pathlib import Path


REPO = Path(__file__).resolve().parents[1]


def _text(relative: str) -> str:
    return (REPO / relative).read_text(encoding="utf-8")


def test_booking_and_bl_views_have_no_direct_sql():
    for path in ["views/booking_v2_view.py", "views/bl_v2_view.py"]:
        text = _text(path).lower()
        assert "select " not in text
        assert "insert into " not in text
        assert "update " not in text
        assert "delete from " not in text
        assert "from psycopg2" not in text


def test_company_bl_renderer_has_no_database_access():
    text = _text("pdf/bl_document_renderer.py").lower()
    assert "database.connection" not in text
    assert "get_connection" not in text
    assert "cursor(" not in text
    assert "select " not in text


def test_billing_and_managers_do_not_import_streamlit_backend_side_effects():
    for path in ["managers/bl_workflow_service.py", "managers/bl_consolidation_service.py"]:
        text = _text(path).lower()
        assert "import streamlit" not in text
        assert "from streamlit" not in text
