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
