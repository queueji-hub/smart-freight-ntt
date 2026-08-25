import pytest
import time
from database.connection import init_database
from database.local_schema_compat import ensure_phase30_local_schema
from managers.tenant_context import set_current_tenant_id
from managers.master_data_crud_manager import list_parties, upsert_party, delete_party
from managers.vendor_manager import get_vendors, get_vendor, create_vendor
from managers.customer_manager import list_customers as cm_list_customers
from managers.customer_master_manager import list_customers as cmm_list_customers


@pytest.fixture(autouse=True)
def setup_db():
    init_database()
    ensure_phase30_local_schema()


def test_unified_business_party_crud_and_roles():
    uid = int(time.time() * 1000) % 1000000
    tenant_id = f"tenant_test_bp_{uid}"
    set_current_tenant_id(tenant_id)
    user = {"id": 1, "username": "admin"}

    # 1. Create a Carrier / Liner
    carrier_id = upsert_party(
        data={
            "party_code": f"CR{uid % 1000:03d}",
            "legal_name": f"Test Ocean Carrier {uid}",
            "display_name": f"TOC Line {uid}",
            "tax_id": f"010555{uid:07d}",
            "branch_no": "00000",
            "phone": "02-111-2222",
            "email": "carrier@test.com",
            "billing_address": "Bangkok Port Terminal",
            "country_code": "TH",
            "is_active": True,
        },
        roles=["CARRIER", "LINER", "VENDOR"],
        finance={
            "credit_limit": 100000.0,
            "credit_currency": "USD",
            "credit_days": 30,
            "payment_term_code": "Net 30",
            "bank_name": "SCB",
            "bank_account_name": f"Test Ocean Carrier {uid}",
            "bank_account_no": "123-4-56789-0",
        },
        user=user
    )
    assert carrier_id > 0

    # 2. Create a Transporter
    transporter_id = upsert_party(
        data={
            "party_code": f"TR{uid % 1000:03d}",
            "legal_name": f"Test Trucking Logistics {uid}",
            "display_name": f"TTL Trucking {uid}",
            "tax_id": f"010556{uid:07d}",
            "branch_no": "00000",
            "phone": "02-333-4444",
            "email": "truck@test.com",
            "billing_address": "Bangna Km.19",
            "country_code": "TH",
            "is_active": True,
        },
        roles=["TRANSPORTER", "VENDOR"],
        finance={
            "payment_term_code": "Net 15",
            "credit_currency": "THB",
        },
        user=user
    )
    assert transporter_id > 0

    # 3. Create a Customer (with Shipper/Consignee roles)
    customer_id = upsert_party(
        data={
            "party_code": f"C{uid % 1000:04d}",
            "legal_name": f"Test Siam Manufacturing {uid}",
            "display_name": f"Siam Mfg {uid}",
            "tax_id": f"010557{uid:07d}",
            "branch_no": "00000",
            "phone": "055-123-456",
            "email": "purchasing@siammfg.com",
            "billing_address": "Phitsanulok Industrial Estate",
            "country_code": "TH",
            "is_active": True,
        },
        roles=["CUSTOMER", "SHIPPER", "CONSIGNEE"],
        finance={
            "credit_limit": 500000.0,
            "credit_currency": "THB",
            "credit_days": 45,
            "payment_term_code": "Net 45",
        },
        user=user
    )
    assert customer_id > 0

    # 4. Test list_parties filtering
    all_parties = list_parties(active_only=True)
    assert len(all_parties) >= 3

    carriers = list_parties(role_type="CARRIER", active_only=True)
    assert any(c["id"] == carrier_id for c in carriers)
    assert not any(c["id"] == customer_id for c in carriers)

    multi_role_carriers = list_parties(role_type=["CARRIER", "LINER"], active_only=True)
    assert any(c["id"] == carrier_id for c in multi_role_carriers)

    transporters = list_parties(role_type="TRANSPORTER", active_only=True)
    assert any(t["id"] == transporter_id for t in transporters)

    customers = list_parties(role_type="CUSTOMER", active_only=True)
    assert any(c["id"] == customer_id for c in customers)

    # 5. Test vendor_manager.get_vendors() returns all payable parties
    vendors = get_vendors()
    # Should include both Carrier and Transporter
    assert any(v["id"] == carrier_id for v in vendors)
    assert any(v["id"] == transporter_id for v in vendors)
    # Should NOT include pure Customer if not assigned VENDOR/CARRIER/TRANSPORTER role
    assert not any(v["id"] == customer_id for v in vendors)

    # 6. Test customer_manager.list_customers() returns the unified customer
    cm_customers = cm_list_customers()
    assert any(c["company_name"] == f"Test Siam Manufacturing {uid}" or c.get("legal_name") == f"Test Siam Manufacturing {uid}" for c in cm_customers)

    # 7. Clean up
    delete_party(carrier_id, user)
    delete_party(transporter_id, user)
    delete_party(customer_id, user)
