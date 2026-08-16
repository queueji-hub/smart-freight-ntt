from pathlib import Path


def test_booking_v2_import_and_helpers():
    import views.booking_v2_view as booking_view

    assert callable(booking_view.render)
    assert booking_view.resolve_vessel("", "EVER STAR") == "EVER STAR"
    assert booking_view.resolve_vessel("MAERSK MANCHESTER", "EVER STAR") == "MAERSK MANCHESTER"


def test_booking_v2_container_summary():
    import pandas as pd
    from views.booking_v2_view import _container_summary

    df = pd.DataFrame([
        {"type": "20'GP", "qty": 2},
        {"type": "40'HC", "qty": 3},
    ])
    assert _container_summary(df) == "20'GP x 2 | 40'HC x 3"


def test_booking_v2_is_production_route_and_has_document_sections():
    dashboard = Path("Dashboard.py").read_text(encoding="utf-8")
    source = Path("views/booking_v2_view.py").read_text(encoding="utf-8")
    assert 'PAGE_ROUTES["booking"] = ("views.booking_v2_view", "render")' in dashboard
    for field in [
        "Customer *", "Job Type *", "Cargo Type *", "POL *", "POD *",
        "Transshipment Port", "Liner", "Vessel", "Mother Vessel", "Voyage",
        "ETD", "ETA", "Container Type", "Gross Weight (KG)",
        "Volume (CBM)", "Chargeable Weight (KG)",
    ]:
        assert field in source, f"missing Booking UI field: {field}"


def test_booking_v2_uses_canonical_manager_and_lifecycle():
    source = Path("views/booking_v2_view.py").read_text(encoding="utf-8")
    assert "from managers.booking_manager import" in source
    assert "create_booking" in source
    assert "update_booking" in source
    assert "can_transition_booking_status" in source
    assert "convert_booking_to_job" in source
    assert "generate_booking_pdf" in source


def test_booking_v2_keeps_mode_specific_input_rules():
    source = Path("views/booking_v2_view.py").read_text(encoding="utf-8")
    assert "profile.show_container_type" in source
    assert "profile.show_chargeable_weight" in source
    assert "profile.show_cbm" in source
    assert "profile.show_cy" in source
    assert "profile.show_cfs" in source
    assert "ETA cannot be earlier than ETD" in source
