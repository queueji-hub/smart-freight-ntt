from pathlib import Path

from pdf.bl_document_renderer import generate_company_bl_pdf, resolve_document_title


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


def test_resolve_document_title_modes():
    # Sea freight -> OCEAN BILL OF LADING
    assert resolve_document_title(job={"job_type": "SE"}) == "OCEAN BILL OF LADING"
    assert resolve_document_title(job={"job_type": "SI"}) == "OCEAN BILL OF LADING"
    assert resolve_document_title(job={"mode": "SEA"}) == "OCEAN BILL OF LADING"
    assert resolve_document_title(job={"mode": "OCEAN"}) == "OCEAN BILL OF LADING"
    assert resolve_document_title({}) == "OCEAN BILL OF LADING"

    # Truck freight (งานรถ) -> TRUCK WAYBILL
    assert resolve_document_title(job={"job_type": "TE"}) == "TRUCK WAYBILL"
    assert resolve_document_title(job={"job_type": "TI"}) == "TRUCK WAYBILL"
    assert resolve_document_title(job={"mode": "TRUCK"}) == "TRUCK WAYBILL"
    assert resolve_document_title(job={"mode": "ROAD"}) == "TRUCK WAYBILL"
    assert resolve_document_title(job={"mode": "LAND"}) == "TRUCK WAYBILL"
    assert resolve_document_title(job={"service_type": "Crossborder Truck"}) == "TRUCK WAYBILL"
    assert resolve_document_title(bl={"mode": "TRUCK"}) == "TRUCK WAYBILL"

    # Air freight (งาน AIR) -> AIR WAYBILL
    assert resolve_document_title(job={"job_type": "AE"}) == "AIR WAYBILL"
    assert resolve_document_title(job={"job_type": "AI"}) == "AIR WAYBILL"
    assert resolve_document_title(job={"mode": "AIR"}) == "AIR WAYBILL"
    assert resolve_document_title(job={"cargo_type": "AIR"}) == "AIR WAYBILL"
    assert resolve_document_title(bl={"mode": "AIR"}) == "AIR WAYBILL"


def test_multimodal_pdf_generation(tmp_path):
    base_bl = {
        "bl_no": "NATTA-TEST001",
        "shipper": "TEST SHIPPER",
        "consignee": "TEST CONSIGNEE",
        "port_of_loading": "BKK",
        "port_of_discharge": "SIN",
    }
    
    # 1. Sea
    sea_pdf = tmp_path / "sea.pdf"
    generate_company_bl_pdf({"bl": base_bl, "job": {"mode": "SEA"}}, str(sea_pdf))
    assert sea_pdf.exists() and sea_pdf.stat().st_size > 0

    # 2. Truck
    truck_pdf = tmp_path / "truck.pdf"
    generate_company_bl_pdf({"bl": base_bl, "job": {"mode": "TRUCK"}}, str(truck_pdf))
    assert truck_pdf.exists() and truck_pdf.stat().st_size > 0

    # 3. Air
    air_pdf = tmp_path / "air.pdf"
    generate_company_bl_pdf({"bl": base_bl, "job": {"mode": "AIR"}}, str(air_pdf))
    assert air_pdf.exists() and air_pdf.stat().st_size > 0
