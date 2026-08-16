import os
from pathlib import Path
import importlib
import pytest

from database.connection import init_database, get_connection
from database.local_schema_compat import ensure_phase30_local_schema
from database.party_finance_compat import ensure_party_finance_schema
from database.postgres_compat import (
    ensure_phase30_charge_master_schema,
    ensure_phase30_master_data_schema,
    ensure_phase30_profitability_schema,
    ensure_phase30_bl_schema,
    ensure_phase30_approval_schema,
)

import Dashboard as dash
from managers.tenant_context import set_current_tenant_id
from managers.customer_manager import create_customer
from managers.master_data_crud_manager import upsert_port
from managers.rate_lookup_service import find_applicable_rates
from managers.quotation_ssot_service import create_quotation_ssot
from managers.quotation_manager import get_quotation_by_no
from managers.booking_ssot_service import create_booking_ssot
from managers.booking_manager import get_booking
from managers.shipment_manager import create_shipment, get_shipment
from managers.bl_workflow_service import create_bl_from_job, get_bl
from managers.bl_consolidation_service import assemble_bl_document_payload
from managers.invoice_manager import create_invoice, list_invoices, record_payment
from managers.profit_manager import add_cost_line, get_profit_summary, create_profit_sheet
from managers.document_approval_manager import submit_for_approval, approve_document, get_approval_status
from core.freight_rules import get_freight_profile
from core.booking_presentation import container_lines
from core.document_preflight import validate_document
from pdf.booking_pdf import generate_booking_pdf
from pdf.bl_document_renderer import generate_company_bl_pdf
from pdf.invoice_pdf import generate_invoice_pdf
from pdf.profitability_pdf import generate_profitability_pdf


def test_full_production_system_lifecycle():
    # 1. Database Bootstrap
    init_database()
    ensure_phase30_local_schema()
    with get_connection() as conn:
        sqlite = (type(conn).__name__ == "SQLiteConnAdapter")
        ensure_party_finance_schema(conn, sqlite=sqlite)
        if not sqlite:
            ensure_phase30_charge_master_schema(conn)
            ensure_phase30_master_data_schema(conn)
            ensure_phase30_profitability_schema(conn)
            ensure_phase30_bl_schema(conn)
            ensure_phase30_approval_schema(conn)

    # 2. All 17 Dashboard routes are valid
    for name, route_info in dash.PAGE_ROUTES.items():
        mod_name, fn_name = route_info if isinstance(route_info, (tuple, list)) else (route_info, "render")
        mod = importlib.import_module(mod_name)
        assert hasattr(mod, fn_name), f"Module {mod_name} has no {fn_name}()"

    # 3. Freight Rules
    sea_profile = get_freight_profile("SEA", "FCL")
    assert sea_profile.show_vessel is True
    assert sea_profile.show_container_type is True
    
    conts = container_lines([{"container_type": "40'HC", "quantity": 1}])
    assert len(conts) == 1

    # 4. E2E Business Trace
    set_current_tenant_id("default")
    import time
    uid = int(time.time() * 1000) % 1000000
    
    # Customer
    cust_id = create_customer({
        "company_name": f"E2E Automated Verification Ltd {uid}",
        "contact_person": "Auto QA",
        "tel": "02-999-8888",
        "tax_id": f"010555{uid:07d}",
        "credit_terms_days": 30,
    })
    assert cust_id, "Customer creation failed"

    # Port & Rate Lookup
    port_id = upsert_port({"port_code": "THBKK", "port_name": "Bangkok Port", "country_code": "TH"})
    assert port_id > 0
    find_applicable_rates(origin_port_id=port_id)

    # Quotation
    quote_no = create_quotation_ssot({
        "customer_id": cust_id,
        "customer_name": f"E2E Automated Verification Ltd {uid}",
        "job_type": "SE",
        "pol": "Bangkok Port",
        "pod": "Singapore",
    }, [{"charge_code": "OFR", "description": "Ocean Freight", "quantity": 1, "unit_price": 800, "currency": "USD"}])
    quote_record = get_quotation_by_no(quote_no)
    quote_id = quote_record["id"]
    assert quote_id > 0

    # Booking
    booking_no = create_booking_ssot({
        "customer_id": cust_id,
        "quotation_id": quote_id,
        "mode": "SEA",
        "cargo_type": "FCL",
        "pol": "Bangkok Port",
        "pod": "Singapore",
        "etd": "2026-09-15",
        "eta": "2026-09-20",
        "vessel": "WAN HAI 301",
        "voyage": "N120",
        "container_summary": "20'GP x 1",
        "containers": [{"container_type": "20'GP", "quantity": 1}]
    })
    booking_data = get_booking(booking_no)
    assert booking_data is not None

    # Preflight & Approval
    errors = validate_document("booking", booking_data)
    assert len(errors) == 0
    sub_res = submit_for_approval("BOOKING", booking_no, {"username": "Operator", "role": "sales"})
    assert sub_res == "Pending Approval"
    app_res = approve_document("BOOKING", booking_no, {"username": "Manager", "role": "admin"})
    assert app_res == "Approved"
    assert get_approval_status("BOOKING", booking_no) == "Approved"

    # Job Control
    created_job_no = create_shipment({
        "job_no": f"JOB-{booking_no}-{uid}",
        "booking_no": booking_no,
        "customer_id": cust_id,
        "customer_name": f"E2E Automated Verification Ltd {uid}",
        "pol": "Bangkok Port",
        "pod": "Singapore",
        "vessel": "WAN HAI 301",
        "voyage": "N120",
        "status": "In Progress"
    })
    job = get_shipment(created_job_no)
    job_id = job["id"]
    job_no = job["job_no"]
    assert job_id > 0

    # B/L
    bl_id = create_bl_from_job(job_no, {"username": "qa_engineer"})
    bl_data = get_bl(bl_id)
    bl_no = bl_data["bl_no"]
    doc_payload = assemble_bl_document_payload(bl_id)
    assert doc_payload["bl"]["bl_no"] == bl_no

    # Invoice
    inv_doc_no = create_invoice({
        "shipment_id": job_id,
        "customer_id": cust_id,
        "customer_name": "E2E Automated Verification Ltd",
        "doc_type": "INV",
        "job_no": job_no,
        "currency": "THB",
    }, [
        {"charge_code": "OFR", "description": "Ocean Freight", "quantity": 1, "unit_price": 28000.0, "tax_type": "Non-VAT", "wht_type": "WHT 1%"}
    ])
    assert inv_doc_no is not None
    invoices = list_invoices()
    assert len(invoices) > 0

    # Payment
    record_payment({
        "doc_no": inv_doc_no,
        "amount": 10000.0,
        "method": "Bank Transfer",
        "reference": "TXN-AUTO-TEST",
    })

    # Profitability
    add_cost_line({
        "shipment_id": job_id,
        "cost_type": "AR",
        "category": "Ocean Freight Revenue",
        "description": "Freight Revenue",
        "quantity": 1,
        "unit_price": 28000.0,
        "amount": 28000.0,
        "currency": "THB",
        "cost_status": "ACTUAL"
    })
    add_cost_line({
        "shipment_id": job_id,
        "cost_type": "AP",
        "category": "Ocean Freight Cost",
        "description": "Carrier Cost",
        "supplier": "Wan Hai Lines",
        "quantity": 1,
        "unit_price": 20000.0,
        "amount": 20000.0,
        "currency": "THB",
        "cost_status": "ACTUAL"
    })
    prof_summary = get_profit_summary(job_id)
    assert prof_summary["actual_net_profit"] == 8000.0
    sheet = create_profit_sheet(job_id, prepared_by="QA Engine")
    assert sheet.get("sheet_no") is not None

    # PDF Generation
    os.makedirs("output", exist_ok=True)
    b_pdf = generate_booking_pdf(booking_data, output_path=f"output/Test_Booking_{booking_no}.pdf")
    bl_pdf = generate_company_bl_pdf(doc_payload, f"output/Test_BL_{bl_id}.pdf")
    inv_pdf = generate_invoice_pdf({
        "doc_no": inv_doc_no,
        "doc_type": "INV",
        "customer_name": "E2E Automated Verification Ltd",
        "items": [{"charge_code": "OFR", "description": "Ocean Freight", "quantity": 1, "unit_price": 28000, "tax_type": "0%", "wht_type": "1%"}]
    }, output_path=f"output/Test_Invoice_{inv_doc_no}.pdf")
    prof_pdf = generate_profitability_pdf(job, prof_summary, output_path=f"output/Test_Profit_{job_id}.pdf")

    assert os.path.exists(b_pdf) and os.path.getsize(b_pdf) > 500
    assert os.path.exists(bl_pdf) and os.path.getsize(bl_pdf) > 500
    assert os.path.exists(inv_pdf) and os.path.getsize(inv_pdf) > 500
    assert os.path.exists(prof_pdf) and os.path.getsize(prof_pdf) > 500
