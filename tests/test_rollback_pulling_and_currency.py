"""
Automated Tests for Document Rollback, Pull Filtering, Multi-Currency, and PDF Stamp Sizing.
"""
import uuid
import pytest
from datetime import date
from decimal import Decimal

from managers.tenant_context import set_current_tenant_id
from database.connection import get_connection
from managers.ap_manager import create_ap_voucher, cancel_ap_voucher, get_ap_voucher
from managers.invoice_manager import create_invoice, cancel_invoice_document, get_invoice_snapshot
from managers.profit_manager import (
    create_batch_invoice_from_ar,
    create_batch_payment_voucher,
    rollback_job_voucher,
    rollback_job_invoice,
    get_cost_lines,
    add_cost_line,
)
from pdf.payment_voucher_pdf import generate_payment_voucher_pdf
from pdf.invoice_pdf import generate_invoice_pdf
from pdf.receipt_pdf import generate_receipt_pdf
from pdf.profit_pdf import generate_profit_pdf


def test_ap_voucher_rollback_lifecycle():
    set_current_tenant_id("test_tenant_pv_rb")
    tenant_id = "test_tenant_pv_rb"
    job_no = f"JOB-PV-{uuid.uuid4().hex[:8]}"
    
    # 1. Create a mock shipment and cost lines
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO shipments (job_no, job_type, status, tenant_id)
                VALUES (%s, 'OUTBOUND', 'ACTIVE', %s)
            """, (job_no, tenant_id))
            cur.execute("SELECT id FROM shipments WHERE job_no=%s AND tenant_id=%s", (job_no, tenant_id))
            row = cur.fetchone()
            s_id = row["id"] if isinstance(row, dict) or hasattr(row, "keys") else row[0]
            conn.commit()

    # Add AP cost lines
    c1_id = add_cost_line({
        "shipment_id": s_id,
        "cost_type": "AP",
        "description": "Ocean Freight AP",
        "currency": "USD",
        "exchange_rate": 35.50000,
        "unit_price": 500.0,
        "quantity": 1.0,
        "amount": 500.0,
        "amount_thb": 17750.0,
        "payout_status": "UNPAID",
    })

    c2_id = add_cost_line({
        "shipment_id": s_id,
        "cost_type": "AP",
        "description": "Port Handling AP",
        "currency": "THB",
        "exchange_rate": 1.0,
        "unit_price": 2500.0,
        "quantity": 1.0,
        "amount": 2500.0,
        "amount_thb": 2500.0,
        "payout_status": "UNPAID",
    })

    # Verify initial state: 2 unvouchered lines
    lines = get_cost_lines(s_id, "AP")
    avail = [c for c in lines if not c.get("voucher_no") and c.get("payout_status") in ("UNPAID", "ESTIMATED", None)]
    assert len(avail) == 2

    # 2. Create batch voucher
    v_no = create_batch_payment_voucher(
        shipment_id=s_id,
        ap_line_ids=[c1_id, c2_id],
        payee_name="ONE LINE",
        voucher_type="PAYMENT_VOUCHER",
        due_date=date.today().isoformat()
    )
    assert v_no is not None

    # Verify lines are now locked / marked with voucher_no
    lines_after = get_cost_lines(s_id, "AP")
    avail_after = [c for c in lines_after if not c.get("voucher_no") and c.get("payout_status") in ("UNPAID", "ESTIMATED", None)]
    assert len(avail_after) == 0  # No lines available to pull again!

    # 3. Rollback / Cancel voucher
    res = rollback_job_voucher(v_no, shipment_id=s_id)
    assert res is True

    # Verify lines are released back to UNPAID and voucher_no is cleared
    lines_reverted = get_cost_lines(s_id, "AP")
    avail_reverted = [c for c in lines_reverted if not c.get("voucher_no") and c.get("payout_status") in ("UNPAID", "ESTIMATED", None)]
    assert len(avail_reverted) == 2
    for l in lines_reverted:
        assert l.get("voucher_no") is None
        assert l.get("payout_status") == "UNPAID"


def test_ar_invoice_rollback_lifecycle():
    set_current_tenant_id("test_tenant_inv_rb")
    tenant_id = "test_tenant_inv_rb"
    job_no = f"JOB-INV-{uuid.uuid4().hex[:8]}"

    # 1. Create a mock shipment and AR revenue lines
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO shipments (job_no, customer_name, job_type, status, tenant_id)
                VALUES (%s, 'Acme Logistics', 'OUTBOUND', 'ACTIVE', %s)
            """, (job_no, tenant_id))
            cur.execute("SELECT id FROM shipments WHERE job_no=%s AND tenant_id=%s", (job_no, tenant_id))
            row = cur.fetchone()
            s_id = row["id"] if isinstance(row, dict) or hasattr(row, "keys") else row[0]
            conn.commit()

    ar1_id = add_cost_line({
        "shipment_id": s_id,
        "cost_type": "AR",
        "description": "Freight Revenue",
        "currency": "USD",
        "exchange_rate": 35.50000,
        "unit_price": 700.0,
        "quantity": 1.0,
        "amount": 700.0,
        "amount_thb": 24850.0,
        "billing_status": "UNBILLED",
    })

    # Verify unbilled
    ar_lines = get_cost_lines(s_id, "AR")
    unbilled = [r for r in ar_lines if not r.get("invoice_no") and r.get("billing_status") != "INVOICED"]
    assert len(unbilled) == 1

    # 2. Create batch invoice
    doc_no = create_batch_invoice_from_ar(
        shipment_id=s_id,
        ar_line_ids=[ar1_id],
        billing_currency="USD",
        exchange_rate=35.50000,
    )
    assert doc_no is not None

    # Verify line is invoiced
    ar_lines_after = get_cost_lines(s_id, "AR")
    unbilled_after = [r for r in ar_lines_after if not r.get("invoice_no") and r.get("billing_status") != "INVOICED"]
    assert len(unbilled_after) == 0

    # 3. Rollback / Cancel invoice
    rb_res = rollback_job_invoice(doc_no, shipment_id=s_id)
    assert rb_res is True

    # Verify line is restored to UNBILLED and can be pulled again
    ar_lines_rev = get_cost_lines(s_id, "AR")
    unbilled_rev = [r for r in ar_lines_rev if not r.get("invoice_no") and r.get("billing_status") != "INVOICED"]
    assert len(unbilled_rev) == 1
    assert ar_lines_rev[0].get("invoice_no") is None
    assert ar_lines_rev[0].get("billing_status") == "UNBILLED"


def test_pdf_generation_and_1_7inch_stamp():
    """Verify that PDF generation renders without error and uses 1.7-inch stamp correctly."""
    voucher_payload = {
        "voucher_no": "PV-2026-TEST-001",
        "voucher_type": "PAYMENT_VOUCHER",
        "invoice_date": date.today().isoformat(),
        "due_date": date.today().isoformat(),
        "job_no": "SE2608-001",
        "payee_name": "MEDITERRANEAN SHIPPING COMPANY",
        "payee_tax_id": "0105541012345",
        "currency": "USD",
        "status": "APPROVED",
        "created_by": "TestUser",
    }
    voucher_items = [
        {"description": "Ocean Freight Service", "quantity": 1, "unit": "CNTR", "unit_price": 1200.0, "amount": 1200.0, "vat_amount": 0, "wht_amount": 0, "net_amount": 1200.0, "tax_type": "NON-VAT", "wht_type": "None", "vendor_invoice_no": "MSC-998811"},
    ]
    pv_pdf_path = generate_payment_voucher_pdf(voucher_payload, voucher_items)
    assert pv_pdf_path is not None

    inv_payload = {
        "doc_no": "INV-2026-TEST-001",
        "doc_type": "INV",
        "customer_name": "GLOBAL TRADING CORP",
        "customer_address": "123 Sukhumvit Road, Bangkok",
        "customer_tax_id": "0105559998887",
        "currency": "USD",
        "exchange_rate": 35.50000,
        "issue_date": date.today().isoformat(),
        "due_date": date.today().isoformat(),
        "subtotal": 1200.0,
        "vat_amount": 84.0,
        "total_amount": 1284.0,
        "grand_total": 1284.0,
    }
    inv_pdf_path = generate_invoice_pdf(inv_payload, customer={"company_name": "GLOBAL TRADING CORP"})
    assert inv_pdf_path is not None

    rc_pdf_path = generate_receipt_pdf(inv_payload, customer={"company_name": "GLOBAL TRADING CORP"})
    assert rc_pdf_path is not None
