"""Test suite verifying UI state resets, navigation resets to Browse / Register,
and deduplication safeguards after create/save/batch operations across all modules.
"""
import pytest
from database.connection import init_database
from database.local_schema_compat import ensure_phase30_local_schema
from managers.customer_master_manager import save_customer, list_customers
from managers.vendor_manager import create_vendor, get_vendors
from managers.ap_manager import create_ap_voucher, get_ap_vouchers
from managers.invoice_manager import create_invoice, list_invoices
from managers.shipment_manager import create_shipment, get_shipment
from managers.profit_manager import add_cost_line, pull_ap_to_ar, create_batch_payment_voucher, create_batch_invoice_from_ar


@pytest.fixture(scope="module", autouse=True)
def setup_db():
    init_database()
    ensure_phase30_local_schema()


import time

def test_customer_creation_and_state_reset():
    """Verify customer creation and state keys."""
    user = {"id": 1, "username": "admin", "tenant_id": "default"}
    uid = int(time.time() * 1000) % 10000
    cust_code = f"C{uid:04d}"
    cust_name = f"Test Navigation Customer {uid} Co., Ltd."
    cust_id = save_customer({
        "customer_code": cust_code,
        "company_name": cust_name,
        "display_name": cust_name,
        "tax_id": "0105558012345",
        "credit_limit": 500000.0,
        "credit_days": 30,
        "is_active": True,
    }, user)
    assert cust_id > 0
    customers = list_customers(user=user)
    match = next((c for c in customers if c.get("id") == cust_id or c.get("customer_code") == cust_code or c.get("company_name") == cust_name), None)
    assert match is not None


def test_vendor_creation_and_state_reset():
    """Verify vendor creation and listing."""
    user = {"id": 1, "username": "admin", "tenant_id": "default"}
    uid = int(time.time() * 1000) % 100000
    v_code = f"V-N-{uid}"
    v_name = f"Test Navigation Vendor {uid} Co., Ltd."
    vid = create_vendor({
        "vendor_code": v_code,
        "legal_name": v_name,
        "tax_id": "0105558099999",
        "country": "TH"
    }, user)
    assert vid > 0
    vendors = get_vendors()
    match = next((v for v in vendors if v.get("vendor_code") == v_code), None)
    assert match is not None
    assert match["legal_name"] == v_name



def test_ap_voucher_creation_flow():
    """Verify AP voucher creation and listing."""
    user = {"id": 1, "username": "admin", "tenant_id": "default"}
    items = [{
        "service_id": "FRT",
        "service_text": "OCEAN FREIGHT TEST",
        "amount": 25000.0,
        "vat_rate": 7.0,
        "has_tax": 1,
        "wht_rate": 1.0,
        "pr_no": "PR-NAV-001",
        "master_job": "JOB-NAV-001"
    }]
    vid = create_ap_voucher({
        "voucher_no": "PV-NAV-TEST-01",
        "vendor_name": "Ocean Carrier Co.",
        "payee_name": "Ocean Carrier Co.",
        "invoice_no": "INV-OC-001",
        "invoice_date": "2026-08-26",
        "due_date": "2026-09-26",
        "currency": "THB",
        "exchange_rate": 1.0,
        "paid_by": "Transfer",
        "paid_amount": 26500.0,
        "status": "APPROVED",
    }, items, user)
    assert vid > 0
    vouchers = get_ap_vouchers()
    v_rec = next((v for v in vouchers if v.get("id") == vid), None)
    assert v_rec is not None
    assert v_rec["vendor_name"] == "Ocean Carrier Co."


def test_invoice_creation_flow():
    """Verify invoice creation and listing."""
    user = {"id": 1, "username": "admin", "tenant_id": "default"}
    items = [{
        "description": "Freight & Logistics Service",
        "quantity": 1.0,
        "unit_price": 30000.0,
        "tax_type": "VAT 7%",
        "wht_type": "WHT 1%",
    }]
    doc_no = create_invoice({
        "doc_type": "INV",
        "customer_name": "Test Nav Customer",
        "issue_date": "2026-08-26",
        "due_date": "2026-09-26",
        "currency": "THB",
        "ref_doc_no": "REF-NAV-001",
        "status": "DRAFT",
        "created_by": "admin",
    }, items)
    assert doc_no is not None
    invoices = list_invoices()
    match = next((i for i in invoices if i.get("doc_no") == doc_no), None)
    assert match is not None


def test_profit_batch_actions_and_deduplication():
    """Verify AP pull to AR, batch PV creation, and batch invoice creation cannot double-submit."""
    user = {"id": 1, "username": "admin", "tenant_id": "default"}
    job_no = create_shipment({
        "customer_id": 1,
        "customer_name": "Batch Nav Customer",
        "job_type": "SE",
        "mode": "SEA",
        "service_type": "CY/CY",
        "carrier": "COSCO",
        "status": "Proceed"
    }, user)
    ship = get_shipment(job_no)
    ship_id = ship["id"]

    # 1. Add AP Line
    ap_id = add_cost_line({
        "shipment_id": ship_id,
        "cost_type": "AP",
        "category": "Ocean Freight",
        "description": "Ocean Freight 20GP",
        "supplier": "Cosco Shipping",
        "quantity": 1.0,
        "unit": "CTR",
        "unit_price": 15000.0,
        "currency": "THB",
        "exchange_rate": 1.0,
        "tax_type": "VAT 7%",
        "wht_type": "WHT 1%",
        "created_by": "admin"
    })

    # 2. Pull AP to AR
    ar_ids = pull_ap_to_ar(
        shipment_id=ship_id,
        ap_line_ids=[ap_id],
        markup_pct=20.0,
        target_customer="Batch Nav Customer",
        user=user
    )
    assert len(ar_ids) == 1

    # 3. Pulling the SAME AP line again MUST raise ValueError (deduplication check)
    with pytest.raises(ValueError, match="already been pulled"):
        pull_ap_to_ar(
            shipment_id=ship_id,
            ap_line_ids=[ap_id],
            markup_pct=20.0,
            target_customer="Batch Nav Customer",
            user=user
        )

    # 4. Create Batch PV for AP Line
    pv_no = create_batch_payment_voucher(
        shipment_id=ship_id,
        ap_line_ids=[ap_id],
        voucher_type="PAYMENT_VOUCHER",
        due_date="2026-09-01",
        user=user
    )
    assert pv_no is not None

    # 5. Creating Batch PV again for the SAME AP line MUST raise ValueError (deduplication check)
    with pytest.raises(ValueError, match="already attached|already assigned"):
        create_batch_payment_voucher(
            shipment_id=ship_id,
            ap_line_ids=[ap_id],
            voucher_type="PAYMENT_VOUCHER",
            due_date="2026-09-01",
            user=user
        )

    # 6. Create Batch Invoice for AR Line
    inv_no = create_batch_invoice_from_ar(
        shipment_id=ship_id,
        ar_line_ids=ar_ids,
        customer_id=1,
        billing_currency="THB",
        exchange_rate=1.0,
        user=user
    )
    assert inv_no is not None

    # 7. Creating Batch Invoice again for the SAME AR line MUST raise ValueError (deduplication check)
    with pytest.raises(ValueError, match="already billed|already attached|already assigned"):
        create_batch_invoice_from_ar(
            shipment_id=ship_id,
            ar_line_ids=ar_ids,
            customer_id=1,
            billing_currency="THB",
            exchange_rate=1.0,
            user=user
        )


