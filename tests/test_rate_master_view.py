from pathlib import Path
import views.rate_master_view as rm_view


def test_rate_master_view_has_render():
    assert hasattr(rm_view, "render")
    assert callable(rm_view.render)


def test_rate_master_view_no_session_state_form_key_collision():
    source = Path("views/rate_master_view.py").read_text(encoding="utf-8")
    # Form key and session state flag must never collide
    assert 'with st.form(f"rate_card_form_' in source
    assert 'st.session_state["rate_master_create_mode"]' in source
    assert 'with st.form(f"rate_master_' not in source
