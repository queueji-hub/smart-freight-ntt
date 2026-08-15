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
