from pathlib import Path

from pdf.bl_document_renderer import generate_company_bl_pdf


def test_company_bl_renderer_uses_payload_only(tmp_path):
    payload = {
        "bl": {
            "bl_no": "NATTA-LCHNAH2608003",
            "approval_status": "Draft",
            "shipper": "Y2J MACHINERY CO.,LTD.",
            "consignee": "KUMIKI CO.,LTD.",
            "port_of_loading": "LAEM CHABANG, THAILAND",
            "port_of_discharge": "NAHA, OKINAWA, JAPAN",
            "vessel": "SKY CHALLENGE",
            "voyage": "V.2608N",
            "package_qty": 3,
            "gross_weight": 982,
            "measurement_cbm": 5.132,
            "description_of_goods": "HARNESS SET",
            "freight_term": "PREPAID",
            "consol_seq": 3,
        },
        "job": {"job_no": "JOB-2608-0014"},
        "booking": {},
        "containers": [{"container_no": "CAIU8226953", "container_type": "40'HQ", "seal_no": "M4912926"}],
    }
    output = tmp_path / "BL_test.pdf"
    result = generate_company_bl_pdf(payload, str(output))
    assert result == str(output)
    assert Path(result).exists()
    assert Path(result).stat().st_size > 0
