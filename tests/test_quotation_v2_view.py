def test_quotation_v2_import_and_helpers():
    import views.quotation_v2_view as quotation_view

    assert callable(quotation_view.render)
    assert quotation_view._s("None", "fallback") == "fallback"
    assert quotation_view._s("Erawan") == "Erawan"
