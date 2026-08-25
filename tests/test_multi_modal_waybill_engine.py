"""Unit and Integration Tests for Multi-Modal Waybill and B/L Engine.

Verifies:
1. Automatic mode detection from Job (Sea, Air, Truck)
2. Proper pre-filling of operational and mode-specific data
3. Number sequence generators (Sea B/L, Air Waybill, Truck Waybill)
4. High-fidelity PDF rendering for all three formats (Ocean B/L, Air Waybill, Truck Waybill)
5. Non-empty PDF byte output without exceptions
"""
from __future__ import annotations

import os
import uuid
from pathlib import Path
import pytest

from database.connection import get_connection, init_database
from database.local_schema_compat import ensure_phase30_local_schema
from managers.tenant_context import set_current_tenant_id
from managers.bl_consolidation_service import (
    generate_company_bl_no,
    generate_air_waybill_no,
    generate_truck_waybill_no,
)
from managers.bl_workflow_service import create_bl_from_job, get_bl, update_bl, detect_transport_mode
from pdf.bl_pdf import generate_bl_pdf
from pdf.bl_document_renderer import resolve_document_title, generate_company_bl_pdf
from pdf.air_waybill_pdf import generate_air_waybill_pdf
from pdf.truck_waybill_pdf import generate_truck_waybill_pdf


@pytest.fixture(autouse=True)
def setup_test_env():
    init_database()
    ensure_phase30_local_schema()
    set_current_tenant_id("test_tenant")
    yield
    set_current_tenant_id(None)


def test_document_number_generators():
    bl_no = generate_company_bl_no("BKK", "SIN", "2026-08-25")
    assert bl_no.startswith("NATTA-BKKSIN2608")

    awb_no = generate_air_waybill_no("BKK", "SIN", "2026-08-25")
    assert awb_no.startswith("HAWB-2608-")

    twb_no = generate_truck_waybill_no("BKK", "VTE", "2026-08-25")
    assert twb_no.startswith("TWB-2608-")


def test_detect_transport_mode():
    assert detect_transport_mode(job={"job_type": "AE", "mode": "AIR"})[0] == "AIR"
    assert detect_transport_mode(job={"job_type": "TE", "mode": "ROAD"})[0] == "TRUCK"
    assert detect_transport_mode(job={"job_type": "SE", "mode": "SEA"})[0] == "SEA"
    assert detect_transport_mode(booking={"flight_no": "TG123"})[0] == "AIR"
    assert detect_transport_mode(booking={"truck_plate": "70-1234"})[0] == "TRUCK"


def test_sea_freight_bl_creation_and_pdf(tmp_path):
    user = {"username": "tester", "role": "admin"}
    tag = uuid.uuid4().hex[:6].upper()
    job_no = f"JOB-SEA-{tag}"

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO shipments (
                    tenant_id, job_no, job_type, mode, cargo_type, service_type,
                    customer_name, shipper, consignee, notify_party,
                    pol, pod, vessel, voyage, etd, eta, commodity, gross_weight, cbm
                ) VALUES (
                    'test_tenant', %s, 'SE', 'SEA', 'FCL', 'CY/CY',
                    'Global Tech Logistics', 'Thai Exporter Ltd.', 'Singapore Importer Pte.', 'Same as Consignee',
                    'Bangkok, Thailand', 'Singapore', 'MOL BRILLIANCE', '045W', '2026-08-25', '2026-08-30',
                    'Electronic Parts', 15400.5, 45.2
                )
                """,
                (job_no,)
            )
            conn.commit()

    bl_id = create_bl_from_job(job_no, user)
    bl = get_bl(bl_id)
    assert bl is not None
    assert bl["transport_mode"] == "SEA"
    assert bl["doc_title"] == "OCEAN BILL OF LADING"
    assert bl["vessel"] == "MOL BRILLIANCE"
    assert float(bl["gross_weight"]) == 15400.5

    out_file = str(tmp_path / f"BL_{bl['bl_no']}.pdf")
    pdf_path = generate_bl_pdf(bl_id, output_path=out_file)
    assert os.path.exists(pdf_path)
    assert os.path.getsize(pdf_path) > 1000


def test_air_freight_awb_creation_and_pdf(tmp_path):
    user = {"username": "tester", "role": "admin"}
    tag = uuid.uuid4().hex[:6].upper()
    bk_no = f"BK-AIR-{tag}"
    job_no = f"JOB-AIR-{tag}"

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO bookings (
                    tenant_id, booking_no, mode, job_type, flight_no, flight_date, mawb_no, hawb_no,
                    pol, pod, carrier, chargeable_weight, gross_weight
                ) VALUES (
                    'test_tenant', %s, 'AIR', 'AE', 'TG 678', '2026-08-26', '217-12345678', 'HAWB-2608-0099',
                    'BKK / Suvarnabhumi', 'NRT / Narita', 'Thai Airways', 450.0, 420.0
                )
                """,
                (bk_no,)
            )
            cur.execute(
                """
                INSERT INTO shipments (
                    tenant_id, job_no, booking_no, job_type, mode, cargo_type,
                    customer_name, shipper, consignee, notify_party,
                    pol, pod, etd, eta, commodity, gross_weight
                ) VALUES (
                    'test_tenant', %s, %s, 'AE', 'AIR', 'AIR',
                    'Precision Auto Parts Co.', 'Thai Precision Parts Ltd.', 'Tokyo Auto Japan', 'Tokyo Logistics',
                    'BKK / Suvarnabhumi', 'NRT / Narita', '2026-08-26', '2026-08-27', 'Automotive Sensors', 420.0
                )
                """,
                (job_no, bk_no)
            )
            conn.commit()

    bl_id = create_bl_from_job(job_no, user)
    bl = get_bl(bl_id)
    assert bl is not None
    assert bl["transport_mode"] == "AIR"
    assert bl["doc_title"] == "AIR WAYBILL"
    assert bl["flight_no"] == "TG 678"
    assert float(bl["chargeable_weight"]) == 450.0
    assert bl["bl_no"].startswith("HAWB-2608-")

    out_file = str(tmp_path / "AWB_TEST.pdf")
    pdf_path = generate_bl_pdf(bl_id, output_path=out_file)
    assert os.path.exists(pdf_path)
    assert os.path.getsize(pdf_path) > 1000


def test_truck_freight_twb_creation_and_pdf(tmp_path):
    user = {"username": "tester", "role": "admin"}
    tag = uuid.uuid4().hex[:6].upper()
    bk_no = f"BK-TRK-{tag}"
    job_no = f"JOB-TRK-{tag}"

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO bookings (
                    tenant_id, booking_no, mode, job_type, truck_type, truck_plate, driver_name, driver_phone,
                    pol, pod, gross_weight
                ) VALUES (
                    'test_tenant', %s, 'ROAD', 'TE', '10 Wheeler (FTL)', '70-9876 BKK', 'Somchai Driver', '081-234-5678',
                    'Bangkok, Thailand', 'Vientiane, Laos', 8500.0
                )
                """,
                (bk_no,)
            )
            cur.execute(
                """
                INSERT INTO shipments (
                    tenant_id, job_no, booking_no, job_type, mode, cargo_type,
                    customer_name, shipper, consignee, notify_party,
                    pol, pod, etd, eta, commodity, gross_weight, cbm, invoice_no
                ) VALUES (
                    'test_tenant', %s, %s, 'TE', 'ROAD', 'FTL',
                    'Mekong Trading Ltd.', 'Siam Consumer Goods', 'Laos Mart Vientiane', 'Same as Consignee',
                    'Bangkok, Thailand', 'Vientiane, Laos', '2026-08-25', '2026-08-27', 'Consumer Beverages', 8500.0, 28.0, 'INV-2026-088'
                )
                """,
                (job_no, bk_no)
            )
            conn.commit()

    bl_id = create_bl_from_job(job_no, user)
    bl = get_bl(bl_id)
    assert bl is not None
    assert bl["transport_mode"] == "TRUCK"
    assert bl["doc_title"] == "TRUCK WAYBILL"
    assert bl["truck_plate"] == "70-9876 BKK"
    assert bl["driver_name"] == "Somchai Driver"
    assert bl["invoice_details"] == "INV-2026-088"
    assert bl["bl_no"].startswith("TWB-2608-")

    out_file = str(tmp_path / "TWB_TEST.pdf")
    pdf_path = generate_bl_pdf(bl_id, output_path=out_file)
    assert os.path.exists(pdf_path)
    assert os.path.getsize(pdf_path) > 1000
