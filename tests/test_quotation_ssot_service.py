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
