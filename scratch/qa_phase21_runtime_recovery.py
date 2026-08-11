import sys
import os
import streamlit as st
from unittest.mock import patch, MagicMock

# Add workspace root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.connection import get_connection, init_database
from managers.customer_manager import create_customer, list_customers
from managers.booking_manager import create_booking, list_bookings
from managers.shipment_manager import create_shipment, list_shipments
from managers.milestone_manager import add_milestone, list_milestones
from managers.container_manager import add_container, list_containers
from managers.month_end_manager import get_month_end_summary
from managers.report_manager import get_company_monthly_performance

def run_regression_test():
    print("Initializing master regression test suite...")
    
    # Force SQLite fallback for the test to ensure all tables exist and can be tested
    with patch("psycopg2.connect", side_effect=Exception("Forced SQLite Fallback for Testing")):
        mock_secrets = MagicMock()
        mock_secrets.get.side_effect = lambda k, default=None: "development" if k == "APP_ENV" else default
        with patch("streamlit.secrets", mock_secrets):
            # 1. Initialize local test database
            init_database()
            print("Database initialized successfully.")
            
            # Clean up existing test data to ensure idempotency
            with get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("DELETE FROM bookings WHERE booking_no = 'BK-TEST-999'")
                    cur.execute("DELETE FROM customers WHERE company_name = 'Antigravity Freight Test'")
                    cur.execute("DELETE FROM shipments WHERE customer_name = 'Antigravity Freight Test'")
                    conn.commit()
            
            # 2. Test Customer CRUD
            c_data = {
                "company_name": "Antigravity Freight Test",
                "contact_person": "Lead Architect",
                "tel": "12345",
                "email": "arch@test.com",
                "address": "Bangkok",
                "tax_id": "TX999"
            }
            c_id = create_customer(c_data)
            assert c_id is not None
            customers = list_customers()
            assert any(c["company_name"] == "Antigravity Freight Test" for c in customers)
            print("Customer CRUD verified.")

            # 3. Test Booking creation
            b_data = {
                "booking_no": "BK-TEST-999",
                "job_type": "EXPORT SEA FCL",
                "customer_name": "Antigravity Freight Test",
                "pol": "Bangkok",
                "pod": "Singapore"
            }
            create_booking(b_data)
            bookings = list_bookings()
            assert any(b["booking_no"] == "BK-TEST-999" for b in bookings)
            print("Booking flow verified.")

            # 4. Test Shipment / Job Creation and get_reporting_period
            s_data = {
                "job_type": "EXPORT SEA FCL",
                "customer_name": "Antigravity Freight Test",
                "etd": "2026-08-11",
                "eta": "2026-08-15"
            }
            job_no = create_shipment(s_data)
            assert job_no is not None
            jobs = list_shipments()
            job = next(j for j in jobs if j["job_no"] == job_no)
            assert job["reporting_month"] == "08"
            assert job["reporting_year"] == "2026"
            print("Shipment creation & canonical reporting month (ETD for EXPORT) verified.")

            # 5. Test Milestones with adapted schema
            m_id = add_milestone(
                shipment_id=job["id"],
                job_no=job_no,
                code="STF",
                name="Stuffing",
                event_date="2026-08-11 10:00:00"
            )
            assert m_id is not None
            milestones = list_milestones(job_no)
            assert len(milestones) > 0
            print("Milestones flow verified.")

            # 6. Test Month-End reporting
            summary = get_month_end_summary("08", "2026")
            assert summary["job_stats"]["total_jobs"] > 0
            print("Month-End reporting verified.")
            
            # 7. Test Company monthly report calculation
            perf = get_company_monthly_performance("08", "2026")
            assert perf["operations"]["total_jobs"] > 0
            print("Company performance calculation verified.")

if __name__ == "__main__":
    run_regression_test()
    print("Master regression suite executed successfully! SUCCESS")
