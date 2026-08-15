from core.document_preflight import validate_document


def test_booking_preflight_requires_routing_schedule_and_customer():
    errors = validate_document("booking", {"customer_id": 1, "pol": "LCH", "pod": "RTM", "etd": "2026-08-25", "eta": "2026-10-06", "cargo_type": "FCL"})
    assert errors == []


def test_booking_preflight_blocks_missing_eta():
    errors = validate_document("booking", {"customer_id": 1, "pol": "LCH", "pod": "RTM", "etd": "2026-08-25", "cargo_type": "FCL"})
    assert "ETA is required." in errors


def test_invoice_preflight_accepts_legacy_customer_name():
    errors = validate_document("invoice", {"customer_name": "Erawan", "invoice_date": "2026-08-15", "currency": "THB"})
    assert errors == []


def test_bl_preflight_requires_parties_and_route():
    errors = validate_document("bl", {"shipper": "A", "consignee": "B", "pol": "LCH", "pod": "RTM"})
    assert errors == []
