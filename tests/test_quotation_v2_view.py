def test_quotation_v2_import_and_helpers():
    import views.quotation_v2_view as quotation_view

    assert callable(quotation_view.render)
    assert callable(quotation_view._render_edit_form)
    assert callable(quotation_view.update_quotation_ssot)
    assert quotation_view._s("None", "fallback") == "fallback"
    assert quotation_view._s("Erawan") == "Erawan"


def test_quotation_v2_master_data():
    import views.quotation_v2_view as quotation_view

    customer_map, customer_dict, sales_map, carrier_map, port_map, charge_map = quotation_view._master_data()
    assert isinstance(customer_map, dict)
    assert isinstance(customer_dict, dict)
    assert isinstance(sales_map, dict)
    assert isinstance(carrier_map, dict)
    assert isinstance(port_map, dict)
    assert isinstance(charge_map, dict)


