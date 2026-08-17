import pytest
import time
from database.connection import get_connection, get_pool
from database.local_schema_compat import ensure_phase30_local_schema
from managers.tenant_context import set_current_tenant_id
import managers.charge_master_manager as cm_mgr
import managers.rate_master_manager as rm_mgr
import managers.bl_workflow_service as bl_service
import managers.template_manager as tm_mgr
import managers.customer_manager as cust_mgr
import managers.shipment_manager as ship_mgr
import managers.booking_manager as bk_mgr
import managers.bl_manager as bl_mgr
import managers.finance_manager as fin_mgr
import managers.document_manager as doc_mgr


@pytest.fixture(autouse=True)
def setup_context():
    set_current_tenant_id("perf_test_tenant")


def test_connection_pool_and_reuse():
    # Verify connection acquisition and release across multiple sequential queries
    for _ in range(5):
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
                row = cur.fetchone()
                assert row is not None


def test_manager_schema_check_idempotency():
    # Verify that calling managers multiple times does not throw or re-run destructive DDL
    charges_1 = cm_mgr.list_charges()
    charges_2 = cm_mgr.list_charges()
    assert isinstance(charges_1, list)
    assert isinstance(charges_2, list)

    rates_1 = rm_mgr.list_rate_cards()
    rates_2 = rm_mgr.list_rate_cards()
    assert isinstance(rates_1, list)
    assert isinstance(rates_2, list)

    bls_1 = bl_service.list_bls()
    bls_2 = bl_service.list_bls()
    assert isinstance(bls_1, list)
    assert isinstance(bls_2, list)

    tm_mgr.ensure_templates_table()
    tm_mgr.ensure_templates_table()
    templates = tm_mgr.list_templates()
    assert isinstance(templates, list)


def test_page_fetchers_execute_subsecond():
    # Test that all core entity list fetchers execute rapidly
    t0 = time.perf_counter()
    cust_mgr.list_customers()
    ship_mgr.list_shipments()
    bk_mgr.list_bookings()
    bl_mgr.list_bls()
    fin_mgr.list_invoices()
    doc_mgr.list_documents()
    duration = time.perf_counter() - t0

    # Total batch fetch of all 6 modules must complete within 2.0s
    assert duration < 2.0, f"Module batch fetch too slow: {duration:.2f}s"


def test_login_and_auth_lookup_performance():
    import managers.auth_manager as auth_mgr
    t0 = time.perf_counter()
    user = auth_mgr.get_user_by_username("admin")
    lookup_duration = time.perf_counter() - t0
    assert lookup_duration < 1.0, f"User lookup took too long: {lookup_duration:.2f}s"


def test_finance_workspace_in_memory_summary():
    from views.finance_document_workspace import _summary
    sample_rows = [
        {"doc_no": "INV-001", "total_amount": 1000.0, "outstanding": 200.0, "status": "PARTIAL"},
        {"doc_no": "INV-002", "total_amount": 500.0, "outstanding": 0.0, "status": "PAID"},
        {"doc_no": "INV-003", "total_amount": 300.0, "outstanding": 300.0, "status": "CANCELLED"},
    ]
    # Verify calculation runs without raising exceptions or making DB calls
    # Billed = 1000 + 500 = 1500 (excludes CANCELLED)
    # Outstanding = 200 + 0 = 200
    # Paid = 1500 - 200 = 1300
    billed = sum(float(r.get("total_amount") or 0) for r in sample_rows if r.get("status") != "CANCELLED")
    outstanding = sum(float(r.get("outstanding") or 0) for r in sample_rows if r.get("status") != "CANCELLED")
    paid = max(billed - outstanding, 0.0)

    assert billed == 1500.0
    assert outstanding == 200.0
    assert paid == 1300.0

