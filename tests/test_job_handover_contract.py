import managers.job_handover_service as handover


def test_build_job_payload_requires_approval(monkeypatch):
    quotation = {
        "quotation_no": "QT-TEST-001",
        "customer_id": 10,
        "customer_name": "Example Customer",
        "sales_id": 20,
        "salesperson": "Sales User",
        "approval_status": "Draft",
    }
    try:
        handover.build_job_payload(quotation)
    except ValueError as exc:
        assert "approved quotations" in str(exc).lower()
    else:
        raise AssertionError("Draft quotation must not be handed over to Operations")


def test_build_job_payload_carries_canonical_context(monkeypatch):
    monkeypatch.setattr(handover, "_master_labels", lambda customer_id, sales_id: ("Example Customer", "Sales User"))
    quotation = {
        "quotation_no": "QT-TEST-002",
        "customer_id": 10,
        "sales_id": 20,
        "approval_status": "Approved",
        "job_type": "SEA",
        "service_type": "FCL",
        "pol": "THLCH",
        "pod": "NLRTM",
        "incoterm": "FOB",
        "commodity": "General Cargo",
    }
    payload = handover.build_job_payload(quotation)
    assert payload["quotation_no"] == "QT-TEST-002"
    assert payload["customer_id"] == 10
    assert payload["sales_id"] == 20
    assert payload["customer_name"] == "Example Customer"
    assert payload["sales_person"] == "Sales User"
    assert payload["pol"] == "THLCH"
    assert payload["pod"] == "NLRTM"
    assert payload["status"] == "Proceed"
