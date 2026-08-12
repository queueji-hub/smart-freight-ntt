import sys
import os
import json
from unittest.mock import patch, MagicMock
from datetime import date, timedelta, datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set up mock streamlit
mock_st = MagicMock()
mock_st.session_state = {}
sys.modules["streamlit"] = mock_st

from database.connection import init_database, get_connection
from managers.customer_manager import create_customer
from managers.quotation_manager import (
    create_quotation, get_quotation_by_no, list_quotations,
    update_quotation, duplicate_quotation, create_quotation_revision
)
from managers.booking_manager import (
    create_booking, get_booking, list_bookings, convert_booking_to_job,
    update_booking, create_booking_revision, get_revision_history
)
from managers.shipment_manager import list_shipments, get_reporting_period, get_shipment, add_job_container, list_job_containers
from managers.bl_manager import create_bl, get_bl, list_bls, add_bl_container, list_bl_containers
from managers.tenant_context import get_current_tenant_id

def run_reality_checks():
    print("=========================================================")
    print("PHASE 29 — SUPABASE SCHEMA REALITY REGRESSION SUITE")
    print("=========================================================")
    
    mock_secrets = {
        "APP_ENV": "production",
        "host": "aws-1-ap-southeast-1.pooler.supabase.com",
        "port": 5432,
        "database": "postgres",
        "user": "postgres.mziinbzvgphrqafxityk",
        "password": "E+tA.5@-_FZLMt7",
        "sslmode": "require"
    }
    
    mock_st_secrets = MagicMock()
    mock_st_secrets.get.side_effect = lambda k, default=None: mock_secrets.get(k, default)
    mock_st_secrets.__getitem__.side_effect = lambda k: mock_secrets[k]
    mock_st_secrets.__contains__.side_effect = lambda k: k in mock_secrets
    
    with patch("streamlit.secrets", mock_st_secrets):
        # We verify that we are indeed connecting to PostgreSQL/Supabase
        with get_connection() as conn:
            conn_type = type(conn).__name__
            print(f"Connected to database type: {conn_type}")
            assert conn_type != "SQLiteConnAdapter", "Must connect to production PostgreSQL/Supabase database!"
            
            # Clean test datasets
            with conn.cursor() as cur:
                cur.execute("DELETE FROM quotations WHERE customer_name = 'Tenant UAT Customer'")
                cur.execute("DELETE FROM bookings WHERE customer_name = 'Tenant UAT Customer'")
                cur.execute("DELETE FROM booking_revisions WHERE booking_no = 'BK-QA-29'")
                cur.execute("DELETE FROM shipments WHERE customer_name = 'Tenant UAT Customer'")
                cur.execute("DELETE FROM customers WHERE company_name = 'Tenant UAT Customer'")
                cur.execute("DELETE FROM bills_of_lading WHERE bl_no LIKE 'HBL-QA-%'")
                conn.commit()
                print("Cleaned UAT test datasets successfully.")

        # Mock current user and tenant context
        user_context = {"id": 1, "username": "qa_operator", "tenant_id": "default"}
        mock_st.session_state = {"user": user_context}
        
        # 1. Customer Creation
        c_id = create_customer({
            "company_name": "Tenant UAT Customer",
            "contact_person": "UAT Coordinator",
            "tel": "9999",
            "email": "uat@smartfreight.com",
            "address": "Bangkok Port",
            "tax_id": "TAX-UAT-29"
        })
        assert c_id is not None
        print("1. Customer Creation: PASS")
        
        # 2. Quotation Creation
        payload = {
            "job_type": "SE",
            "customer_name": "Tenant UAT Customer",
            "salesperson": "QA Agent UAT",
            "pol": "Bangkok",
            "pod": "Singapore",
            "commodity": "Steel",
            "incoterm": "FOB",
            "service_type": "FCL",
            "container_type": "40HC",
            "container_quantity": 1,
            "quotation_date": date.today().isoformat(),
            "validity_date": (date.today() + timedelta(days=30)).isoformat(),
        }
        items = [{"description": "Handling charges", "quantity": 1, "unit_rate": 100, "price": 100, "currency": "USD"}]
        
        qno = create_quotation(payload, items)
        assert qno is not None
        print(f"2. Quotation Creation: PASS (No: {qno})")
        
        # 3. Quotation Revision
        revised_qno = create_quotation_revision(qno)
        assert revised_qno is not None
        assert "-R1" in revised_qno
        print(f"3. Quotation Revision: PASS (No: {revised_qno})")
        
        # 4. Booking Creation
        booking_payload = {
            "booking_no": "BK-QA-29",
            "quotation_id": 1,
            "quotation_no": revised_qno,
            "job_type": "EXPORT SEA FCL",
            "customer_name": "Tenant UAT Customer",
            "pol": "Bangkok",
            "pod": "Singapore",
            "etd": "2026-08-11",
            "eta": "2026-08-25",
            "cargo_type": "FCL",
            "commodity": "Steel",
            "gross_weight": 12000.0,
            "measurement_cbm": 25.0,
            "container_summary": "1x 40HC",
            "freight_term": "PREPAID",
            "created_by": "QA Agent UAT"
        }
        bk_no = create_booking(booking_payload, user_context)
        assert bk_no == "BK-QA-29"
        print(f"4. Booking Creation: PASS (No: {bk_no})")
        
        # 5. Booking Revision (controlled revision)
        update_booking(bk_no, {"status": "SUBMITTED"}, "default")
        update_booking(bk_no, {"status": "CONFIRMED"}, "default")
        
        rev_no = create_booking_revision(bk_no, "Change of shipping line", user_context)
        assert rev_no == 1
        history = get_revision_history(bk_no)
        assert len(history) == 1
        print("5. Booking Revision: PASS")
        
        # 6. Job Conversion
        update_booking(bk_no, {"status": "SUBMITTED"}, "default")
        update_booking(bk_no, {"status": "CONFIRMED"}, "default")
        job_no = convert_booking_to_job(bk_no, user_context)
        assert job_no is not None
        print(f"6. Job Conversion: PASS (Job No: {job_no})")
        
        # 7. Job 360 (Overview, Containers, Milestones)
        shipment = get_shipment(job_no)
        assert shipment is not None
        
        # Container assignment
        add_job_container({
            "job_no": job_no,
            "container_no": "TEST2900011",
            "container_size": "40HC",
            "container_type": "GP",
            "seal_no": "SEAL-2901",
            "gross_weight": 24000.0
        })
        containers = list_job_containers(job_no)
        assert len(containers) == 1
        assert containers[0]["container_no"] == "TEST2900011"
        print("7. Job 360 & Containers: PASS")
        
        # 8. B/L Creation
        bl_extra = {
            "bl_no": "HBL-QA-2901",
            "shipper": "Shipper Corp",
            "consignee": "Consignee Ltd",
            "notify_party": "Notify Co",
            "port_of_loading": "Bangkok",
            "port_of_discharge": "Singapore",
            "vessel": "Ever Given",
            "voyage": "0123W",
            "status": "Draft"
        }
        bl_id = create_bl(job_no, "HBL", user_context, bl_extra)
        assert bl_id is not None
        bl_record = get_bl(bl_id)
        assert bl_record is not None
        assert bl_record["bl_no"] == "HBL-QA-2901"
        print(f"8. B/L Creation: PASS (ID: {bl_id})")
        
        # 9. B/L Containers Mapping
        c_id = containers[0]["id"]
        add_bl_container(bl_id, c_id)
        mapped_containers = list_bl_containers(bl_id)
        assert len(mapped_containers) == 1
        assert mapped_containers[0]["container_no"] == "TEST2900011"
        print("9. B/L Containers Junction: PASS")
        
        # 10. Tenant Isolation
        # Switch tenant and ensure queries do not return records
        user_context_isolated = {"id": 2, "username": "other_operator", "tenant_id": "isolated_tenant"}
        mock_st.session_state = {"user": user_context_isolated}
        
        isolated_bookings = list_bookings()
        assert not any(b["booking_no"] == bk_no for b in isolated_bookings)
        
        isolated_shipments = list_shipments()
        assert not any(s["job_no"] == job_no for s in isolated_shipments)
        print("10. Tenant Isolation: PASS")
        
        # Clean up
        mock_st.session_state = {"user": user_context}
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM quotations WHERE customer_name = 'Tenant UAT Customer'")
                cur.execute("DELETE FROM bookings WHERE customer_name = 'Tenant UAT Customer'")
                cur.execute("DELETE FROM booking_revisions WHERE booking_no = 'BK-QA-29'")
                cur.execute("DELETE FROM shipments WHERE customer_name = 'Tenant UAT Customer'")
                cur.execute("DELETE FROM customers WHERE company_name = 'Tenant UAT Customer'")
                cur.execute("DELETE FROM bills_of_lading WHERE bl_no LIKE 'HBL-QA-%'")
                conn.commit()
        print("UAT test cleanup: PASS")
        print("\nAll regression tests completed successfully against Supabase production database!")

if __name__ == "__main__":
    run_reality_checks()
