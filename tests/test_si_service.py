"""Unit tests for Shipping Instruction (S/I) service and PDF generation."""
import os
import pytest
from managers.si_service import assemble_si_payload, NATTAYAARAT_OFFICIAL_SHIPPER
from pdf.si_pdf import generate_si_pdf
from managers.shipment_manager import list_shipments, create_shipment
from managers.tenant_context import set_current_tenant_id


@pytest.fixture(autouse=True)
def setup_tenant():
    set_current_tenant_id("default")
    yield
    set_current_tenant_id(None)


def _get_or_create_test_job() -> str:
    jobs = list_shipments(limit=10)
    if jobs:
        return jobs[0]["job_no"]
    return create_shipment({
        "job_type": "EXPORT SEA",
        "mode": "SEA",
        "customer_name": "TEST CUSTOMER",
        "shipper": "ORIGINAL SHIPPER CO., LTD.",
        "consignee": "ORIGINAL CONSIGNEE CO., LTD.",
        "notify_party": "SAME AS CONSIGNEE",
        "delivery_agent": "DESTINATION AGENT OVERSEAS CO., LTD.",
        "carrier": "MSC",
        "booking_no": "BK-TEST-001",
        "mbl_no": "MEDU1234567",
        "pol": "BANGKOK",
        "pod": "SINGAPORE",
        "etd": "2026-08-20",
        "eta": "2026-08-25",
        "status": "Proceed"
    })


def test_si_direct_mode():
    job_no = _get_or_create_test_job()

    payload = assemble_si_payload(job_no, si_mode="direct")
    assert payload["si_mode"] == "direct"
    assert payload["si_mode_label"] == "DIRECT B/L"
    assert payload["job_no"] == job_no
    assert payload["notify_party"] != ""

    pdf_path = generate_si_pdf(payload)
    assert os.path.exists(pdf_path)
    assert os.path.getsize(pdf_path) > 0


def test_si_hbl_mode_parties():
    job_no = _get_or_create_test_job()

    payload = assemble_si_payload(job_no, si_mode="hbl")
    assert payload["si_mode"] == "hbl"
    assert payload["si_mode_label"] == "AGENT B/L (HBL MODE)"
    assert "NATTAYAARAT CO., LTD." in payload["shipper"]
    assert "TAX ID: 073-556-800-4823" in payload["shipper"]
    assert "DESTINATION AGENT" in payload["consignee"] or "AGENT" in payload["consignee"]
    assert payload["notify_party"] == "SAME AS CONSIGNEE"

    pdf_path = generate_si_pdf(payload)
    assert os.path.exists(pdf_path)
    assert os.path.getsize(pdf_path) > 0
