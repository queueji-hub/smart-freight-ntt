import managers.quotation_ssot_service as ssot


def test_create_quotation_ssot_requires_customer_id(monkeypatch):
    try:
        ssot.create_quotation_ssot({"sales_id": 2}, [])
    except ValueError as exc:
        assert "customer_id is required" in str(exc)
    else:
        raise AssertionError("customer_id must be required")


def test_create_quotation_ssot_persists_master_ids(monkeypatch):
    monkeypatch.setattr(ssot, "_legacy_create_quotation", lambda data, items: "QT-1")
    captured = {}

    def fake_sync(quotation_no, customer_id=None, sales_id=None):
        captured.update(quotation_no=quotation_no, customer_id=customer_id, sales_id=sales_id)
        return True

    monkeypatch.setattr(ssot, "sync_quotation_master_ids", fake_sync)
    result = ssot.create_quotation_ssot({"customer_id": 11, "sales_id": 7}, [])

    assert result == "QT-1"
    assert captured == {"quotation_no": "QT-1", "customer_id": 11, "sales_id": 7}


def test_update_quotation_ssot_requires_customer_id(monkeypatch):
    try:
        ssot.update_quotation_ssot("QT-1", {"sales_id": 7}, [])
    except ValueError as exc:
        assert "customer_id is required" in str(exc)
    else:
        raise AssertionError("customer_id must be required")


def test_delete_quotation_ssot(monkeypatch):
    monkeypatch.setattr(ssot, "_legacy_delete_quotation", lambda qno: True)
    assert ssot.delete_quotation_ssot("QT-TEST-01") is True


def test_normalize_items_preserves_custom_unit_and_currency(monkeypatch):
    items = [{
        "charge_code": "OFR",
        "description": "Ocean Freight (40HC to Singapore)",
        "unit": "40'HC",
        "currency": "EUR",
        "quantity": 2,
        "unit_rate": 1500,
    }]
    normalized = ssot._normalize_items(items)
    assert len(normalized) == 1
    assert normalized[0]["unit"] == "40'HC"
    assert normalized[0]["currency"] == "EUR"
    assert normalized[0]["description"] == "Ocean Freight (40HC to Singapore)"


def test_handover_accepts_approved_status_and_resolves_customer():
    from managers.job_handover_service import build_job_payload
    # Test with status='Approved' even if approval_status is 'Draft' or missing
    q_data = {
        "quotation_no": "QT-TEST-99",
        "status": "Approved",
        "approval_status": "Draft",
        "customer_id": 1,
        "customer_name": "Test Co",
        "sales_id": 1,
        "pol": "Bangkok",
        "pod": "Singapore",
    }
    payload = build_job_payload(q_data, {"username": "admin"})
    assert payload["quotation_no"] == "QT-TEST-99"
    assert payload["status"] == "Proceed"
    assert payload["customer_id"] == 1


def test_handover_accepts_approval_status_approved():
    from managers.job_handover_service import build_job_payload
    q_data = {
        "quotation_no": "QT-TEST-100",
        "status": "Draft",
        "approval_status": "Approved",
        "customer_id": 2,
        "customer_name": "Test Co 2",
        "sales_id": 1,
    }
    payload = build_job_payload(q_data, {"username": "admin"})
    assert payload["quotation_no"] == "QT-TEST-100"
    assert payload["status"] == "Proceed"


