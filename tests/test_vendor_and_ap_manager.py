import pytest
import time
from database.connection import init_database
from database.local_schema_compat import ensure_phase30_local_schema
from managers.tenant_context import set_current_tenant_id
from managers.vendor_manager import (
    get_vendors,
    get_vendor,
    create_vendor,
    update_vendor,
)
from managers.ap_manager import (
    get_ap_vouchers,
    get_ap_voucher,
    create_ap_voucher,
    update_ap_voucher_status,
)


@pytest.fixture(autouse=True)
def setup_db():
    init_database()
    ensure_phase30_local_schema()


def test_vendor_lifecycle_and_multi_tenant():
    uid = int(time.time() * 1000) % 1000000
    tenant_a = f"tenant_ap_{uid}"
    tenant_b = f"tenant_ap_other_{uid}"

    set_current_tenant_id(tenant_a)

    # 1. Create vendor in Tenant A
    vendor_data = {
        "vendor_code": f"VND-{uid}",
        "legal_name": "Evergreen Marine Corp.",
        "tax_id": "0105559876543",
        "country": "Taiwan",
        "currency": "USD",
    }
    user = {"id": 1, "username": "admin"}
    vendor_id = create_vendor(vendor_data, user)
    assert vendor_id is not None
    assert vendor_id > 0

    # Retrieve vendor
    v = get_vendor(vendor_id)
    assert v is not None
    assert v["vendor_code"] == f"VND-{uid}"
    assert v["legal_name"] == "Evergreen Marine Corp."

    # Update vendor
    update_vendor(vendor_id, {
        "legal_name": "Evergreen Line Pte Ltd",
        "tax_id": "0105559876543",
        "country": "Singapore",
        "currency": "USD",
        "status": "Active"
    }, user)

    v_updated = get_vendor(vendor_id)
    assert v_updated["legal_name"] == "Evergreen Line Pte Ltd"

    # Multi-tenant isolation check: Tenant B should NOT see this vendor
    set_current_tenant_id(tenant_b)
    assert get_vendor(vendor_id) is None
    assert not any(x["id"] == vendor_id for x in get_vendors())

    # Switch back
    set_current_tenant_id(tenant_a)
    assert get_vendor(vendor_id) is not None


def test_ap_voucher_lifecycle():
    uid = int(time.time() * 1000) % 1000000
    tenant_id = f"tenant_voucher_{uid}"
    set_current_tenant_id(tenant_id)

    # Create vendor
    vendor_id = create_vendor({
        "vendor_code": f"CARRIER-{uid}",
        "legal_name": "Ocean Network Express (ONE)",
        "tax_id": "0105551234567",
        "country": "Japan",
        "currency": "USD",
    }, {"username": "admin"})

    # Create AP Voucher
    voucher_data = {
        "vendor_id": vendor_id,
        "job_no": f"JOB-AP-{uid}",
        "invoice_no": f"V-INV-{uid}",
        "invoice_date": "2026-08-17",
        "due_date": "2026-09-17",
        "currency": "USD",
        "exchange_rate": 35.5,
        "subtotal": 1200.0,
        "tax": 84.0,
        "total": 1284.0,
    }
    user = {"id": 1, "username": "accounting_user"}
    voucher_id = create_ap_voucher(voucher_data, user)
    assert voucher_id is not None
    assert voucher_id > 0

    # Retrieve voucher
    voucher = get_ap_voucher(voucher_id)
    assert voucher is not None
    assert voucher["invoice_no"] == f"V-INV-{uid}"
    assert voucher["vendor_name"] == "Ocean Network Express (ONE)"
    assert voucher["status"] == "DRAFT"

    # Update status
    update_ap_voucher_status(voucher_id, "Approved", user)
    v_approved = get_ap_voucher(voucher_id)
    assert v_approved["status"] == "Approved"

    # List vouchers
    all_vouchers = get_ap_vouchers()
    assert any(v["id"] == voucher_id for v in all_vouchers)
