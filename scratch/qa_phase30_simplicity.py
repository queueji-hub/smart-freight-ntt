import sys
import os
import json
from unittest.mock import patch, MagicMock
from datetime import date, timedelta

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set up mock streamlit
mock_st = MagicMock()
mock_st.session_state = {}
sys.modules["streamlit"] = mock_st

from database.connection import get_connection
from managers.customer_manager import create_customer
from managers.quotation_manager import create_quotation, create_quotation_revision
from managers.booking_manager import create_booking, convert_booking_to_job, update_booking
from managers.shipment_manager import list_shipments, get_shipment, add_job_container, list_job_containers
from managers.report_manager import get_company_monthly_performance, get_salesperson_job_drilldown
from managers.commission_manager import create_commission_draft

def run_simplicity_verification():
    print("=========================================================")
    print("PHASE 30 — SIMPLICITY & CONSOLIDATION VERIFICATION SUITE")
    print("=========================================================")

    # Configure mock secrets for production Supabase
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
        # 1. Database connection check
        with get_connection() as conn:
            assert type(conn).__name__ != "SQLiteConnAdapter", "Must use production Supabase instance!"
            
            # Setup/Teardown cleanup
            with conn.cursor() as cur:
                cur.execute("DELETE FROM shipment_milestones WHERE shipment_id IN (SELECT id FROM shipments WHERE customer_name = 'Simplicity UAT Customer')")
                cur.execute("DELETE FROM shipments WHERE customer_name = 'Simplicity UAT Customer'")
                cur.execute("DELETE FROM bookings WHERE customer_name = 'Simplicity UAT Customer'")
                cur.execute("DELETE FROM quotations WHERE customer_name = 'Simplicity UAT Customer'")
                cur.execute("DELETE FROM customers WHERE company_name = 'Simplicity UAT Customer'")
                conn.commit()
                print("Cleaned database UAT state.")

        # Set user session context
        user_context = {"id": 1, "username": "simp_operator", "tenant_id": "default"}
        mock_st.session_state = {"user": user_context}

        # 2. Customer
        c_id = create_customer({
            "company_name": "Simplicity UAT Customer",
            "contact_person": "UAT Coordinator",
            "tel": "1111",
            "email": "uat@smartfreight.com",
            "address": "Bangkok",
            "tax_id": "TAX-UAT-30"
        })
        assert c_id is not None
        print("Customer Creation: PASS")

        # 3. Quotation
        payload = {
            "job_type": "SE",
            "customer_name": "Simplicity UAT Customer",
            "salesperson": "QA Agent Simp",
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
        items = [{"description": "Surcharge", "quantity": 1, "unit_rate": 200, "price": 200, "currency": "USD"}]
        qno = create_quotation(payload, items)
        assert qno is not None
        print(f"Quotation Creation: PASS (No: {qno})")

        # Get actual quotation id
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT id FROM quotations WHERE quotation_no = %s", (qno,))
                row = cur.fetchone()
                actual_q_id = row["id"] if isinstance(row, dict) else row[0]

        # 4. Booking
        booking_payload = {
            "booking_no": "BK-QA-30",
            "quotation_id": actual_q_id,
            "quotation_no": qno,
            "job_type": "EXPORT SEA FCL",
            "customer_name": "Simplicity UAT Customer",
            "pol": "Bangkok",
            "pod": "Singapore",
            "etd": "2026-08-11",
            "eta": "2026-08-25",
            "cargo_type": "FCL",
            "commodity": "Steel",
            "gross_weight": 10000.0,
            "measurement_cbm": 20.0,
            "container_summary": "1x 40HC",
            "freight_term": "PREPAID",
            "created_by": "QA Agent Simp"
        }
        bk_no = create_booking(booking_payload, user_context)
        assert bk_no == "BK-QA-30"
        print(f"Booking Creation: PASS (No: {bk_no})")

        # Convert to Job
        update_booking(bk_no, {"status": "SUBMITTED"}, "default")
        update_booking(bk_no, {"status": "CONFIRMED"}, "default")
        job_no = convert_booking_to_job(bk_no, user_context)
        assert job_no is not None
        print(f"Convert to Job: PASS (Job No: {job_no})")

        # 5. Core Reporting Calculations Check
        # Set reporting month and year based on ETD (August 2026)
        r_month = "08"
        r_year = "2026"
        
        # Test Report Manager GP calculations
        perf = get_company_monthly_performance(r_month, r_year)
        assert perf is not None
        print(f"Company performance query: PASS (Total Jobs: {perf['operations']['total_jobs']})")
        
        # Test salesperson performance drill down
        drilldown = get_salesperson_job_drilldown(r_month, r_year, "QA Agent Simp")
        assert len(drilldown) >= 1
        print("Salesperson performance job drilldown: PASS")

        # 6. Tenant Isolation
        with patch("managers.shipment_manager.get_current_tenant_id", return_value="isolated_tenant"):
            isolated_jobs = list_shipments()
            assert not any(j["job_no"] == job_no for j in isolated_jobs)
        print("Tenant Isolation checks: PASS")

        # Teardown / Clean up UAT records
        mock_st.session_state = {"user": user_context}
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM shipment_milestones WHERE shipment_id IN (SELECT id FROM shipments WHERE customer_name = 'Simplicity UAT Customer')")
                cur.execute("DELETE FROM shipments WHERE customer_name = 'Simplicity UAT Customer'")
                cur.execute("DELETE FROM bookings WHERE customer_name = 'Simplicity UAT Customer'")
                cur.execute("DELETE FROM quotations WHERE customer_name = 'Simplicity UAT Customer'")
                cur.execute("DELETE FROM customers WHERE company_name = 'Simplicity UAT Customer'")
                conn.commit()
        print("UAT test cleanup: PASS")
        print("\nAll Simplicity Verification scenarios PASSED successfully!")

if __name__ == "__main__":
    run_simplicity_verification()
