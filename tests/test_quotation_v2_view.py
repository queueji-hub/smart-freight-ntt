def test_quotation_v2_import_and_helpers():
    import views.quotation_v2_view as quotation_view

    assert callable(quotation_view.render)
    assert callable(quotation_view._render_edit_form)
    assert callable(quotation_view.update_quotation_ssot)
    assert quotation_view._s("None", "fallback") == "fallback"
    assert quotation_view._s("Erawan") == "Erawan"

