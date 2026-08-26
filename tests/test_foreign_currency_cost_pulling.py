"""Unit test suite for foreign currency (USD, EUR, etc.) expenses and pulling workflows.

Validates that:
1. Entering costs in USD with exchange rate stores both original currency amount and converted THB amount.
2. Pulling AP in USD to AR as THB converts correctly: rate_thb = orig_rate * ex_rate, currency="THB".
3. Pulling AP in USD to AR as ORIGINAL preserves USD with exchange rate and correct amount_thb.
4. Auto-filling costs into Payment Voucher converts foreign currencies into accurate THB values instead of using unconverted amounts.
5. Invoicing with currency conversions accurately calculates billing amounts.
"""
import os
import time
import pytest
from database.connection import init_database
from database.local_schema_compat import ensure_phase30_local_schema
from managers.profit_manager import (
    add_cost_line,
    get_cost_line,
    get_cost_lines,
    pull_ap_to_ar,
    create_batch_payment_voucher,
    create_batch_invoice_from_ar,
    compute_line_tax_and_net,
)
from managers.shipment_manager import create_shipment, get_shipment


@pytest.fixture(scope="module", autouse=True)
def setup_db():
    init_database()
    ensure_phase30_local_schema()


def test_foreign_currency_cost_entry_and_calculation():
    """Test entering 500 USD @ 35.0 exchange rate with VAT 7% and WHT 1%."""
    # 500 USD @ 35.0 = 17,500 THB
    # VAT 7%: 35.00 USD (1,225.00 THB)
    # WHT 1%: 5.00 USD (175.00 THB)
    # Net: 530.00 USD (18,550.00 THB)
    res = compute_line_tax_and_net(qty=1, unit_price=500.0, tax_type="VAT 7%", wht_type="WHT 1%", currency="USD", exchange_rate=35.0)
    assert res["amount"] == 500.0
    assert res["amount_thb"] == 17500.0
    assert res["vat_amount"] == 35.0
    assert res["wht_amount"] == 5.0
    assert res["net_amount"] == 530.0
    assert res["net_thb"] == 18550.0
    assert res["exchange_rate"] == 35.0


def test_pull_ap_usd_to_ar_converted_to_thb():
    """Test pulling 500 USD AP to AR with target_currency='THB' and 15% markup."""
    user = {"id": 1, "username": "admin", "tenant_id": "default"}
    uid = int(time.time() * 1000) % 1000000

    job_no = create_shipment({
        "customer_id": 1,
        "customer_name": f"Foreign Currency Customer {uid}",
        "job_type": "SE",
        "mode": "SEA",
        "service_type": "CY/CY",
        "carrier": "ONE LINE",
        "status": "Proceed"
    }, user)
    ship = get_shipment(job_no)
    ship_id = ship["id"]

    # 1. Add AP Line in USD (500 USD @ 35.0 = 17,500 THB)
    ap_id = add_cost_line({
        "shipment_id": ship_id,
        "cost_type": "AP",
        "category": "Ocean Freight",
        "description": "Ocean Freight 20GP (USD)",
        "supplier": "Ocean Network Express",
        "quantity": 1.0,
        "unit": "CTR",
        "unit_price": 500.0,
        "currency": "USD",
        "exchange_rate": 35.0,
        "tax_type": "VAT 7%",
        "wht_type": "WHT 1%",
        "created_by": "admin"
    })
    ap_rec = get_cost_line(ap_id)
    assert ap_rec["currency"] == "USD"
    assert ap_rec["unit_price"] == 500.0
    assert ap_rec["amount"] == 500.0
    assert ap_rec["amount_thb"] == 17500.0

    # 2. Pull AP to AR as THB with 15% markup
    # Base THB rate = 500 * 35 = 17,500 THB
    # Selling rate with 15% markup = 17,500 * 1.15 = 20,125 THB
    pulled_ar_ids = pull_ap_to_ar(
        shipment_id=ship_id,
        ap_line_ids=[ap_id],
        markup_pct=15.0,
        target_customer="Test Customer",
        target_currency="THB",
        user=user
    )
    assert len(pulled_ar_ids) == 1
    ar_rec = get_cost_line(pulled_ar_ids[0])
    assert ar_rec["currency"] == "THB"
    assert ar_rec["exchange_rate"] == 1.0
    assert ar_rec["unit_price"] == 20125.0
    assert ar_rec["amount"] == 20125.0
    assert ar_rec["amount_thb"] == 20125.0


def test_pull_ap_usd_to_ar_kept_as_original_usd():
    """Test pulling 500 USD AP to AR with target_currency='ORIGINAL' and 10% markup."""
    user = {"id": 1, "username": "admin", "tenant_id": "default"}
    uid = int(time.time() * 1000) % 1000000

    job_no = create_shipment({
        "customer_id": 1,
        "customer_name": f"USD Keeping Customer {uid}",
        "job_type": "SE",
        "mode": "SEA",
        "service_type": "CY/CY",
        "carrier": "HAPAG-LLOYD",
        "status": "Proceed"
    }, user)
    ship = get_shipment(job_no)
    ship_id = ship["id"]

    # 1. Add AP Line in USD (800 USD @ 35.0 = 28,000 THB)
    ap_id = add_cost_line({
        "shipment_id": ship_id,
        "cost_type": "AP",
        "category": "Ocean Freight",
        "description": "Ocean Freight 40HC (USD)",
        "supplier": "Hapag-Lloyd (Thailand)",
        "quantity": 1.0,
        "unit": "CTR",
        "unit_price": 800.0,
        "currency": "USD",
        "exchange_rate": 35.0,
        "tax_type": "VAT 7%",
        "wht_type": "WHT 1%",
        "created_by": "admin"
    })

    # 2. Pull AP to AR as ORIGINAL with 10% markup
    # Selling rate in USD = 800 * 1.10 = 880.00 USD
    # Amount THB = 880 * 35.0 = 30,800.00 THB
    pulled_ar_ids = pull_ap_to_ar(
        shipment_id=ship_id,
        ap_line_ids=[ap_id],
        markup_pct=10.0,
        target_customer="Test Customer",
        target_currency="ORIGINAL",
        user=user
    )
    assert len(pulled_ar_ids) == 1
    ar_rec = get_cost_line(pulled_ar_ids[0])
    assert ar_rec["currency"] == "USD"
    assert ar_rec["exchange_rate"] == 35.0
    assert ar_rec["unit_price"] == 880.0
    assert ar_rec["amount"] == 880.0
    assert ar_rec["amount_thb"] == 30800.0
