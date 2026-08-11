import sys
import os
from unittest.mock import patch, MagicMock
from datetime import date, timedelta

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Mock Streamlit session state
mock_st = MagicMock()
mock_st.session_state = {}
sys.modules["streamlit"] = mock_st

from database.connection import init_database, get_connection
from managers.customer_manager import create_customer
from managers.quotation_manager import (
    create_quotation, get_quotation_by_no, list_quotations,
    update_quotation, duplicate_quotation, create_quotation_revision
)
from managers.booking_manager import create_booking, list_bookings, convert_booking_to_job, update_booking
from managers.shipment_manager import list_shipments, get_reporting_period
from managers.profit_manager import add_cost_line, get_profit_summary
from managers.report_manager import get_company_monthly_performance
from views.quotation_view import _validate_form, _clear_form_state

def run_commercial_workflow_test():
    print("Initializing Phase 26 Commercial Workflow & Production Hardening Suite...")

    with patch("psycopg2.connect", side_effect=Exception("Forced SQLite Fallback")):
        mock_secrets = MagicMock()
        mock_secrets.get.side_effect = lambda k, default=None: "development" if k == "APP_ENV" else default
        with patch("streamlit.secrets", mock_secrets):
            init_database()
            print("Database initialized.")

            # Clean test datasets
            with get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("DELETE FROM quotations WHERE customer_name = 'Tenant UAT Customer'")
                    cur.execute("DELETE FROM bookings WHERE customer_name = 'Tenant UAT Customer'")
                    cur.execute("DELETE FROM shipments WHERE customer_name = 'Tenant UAT Customer'")
                    cur.execute("DELETE FROM customers WHERE company_name = 'Tenant UAT Customer'")
                    conn.commit()

            # 1. Customer
            c_id = create_customer({
                "company_name": "Tenant UAT Customer",
                "contact_person": "Commercial Manager",
                "tel": "12345",
                "email": "sales@uat.com",
                "address": "Terminal A",
                "tax_id": "TAX-UAT-26"
            })
            assert c_id is not None
            print("Customer verified.")

            # 2. Quotation Creation with Validation Error (State Preservation)
            mock_st.session_state = {
                "new_cust": "Tenant UAT Customer",
                "new_sales": "QA Agent UAT",
                "new_items": [
                    {"description": "Ocean Freight FCL", "quantity": 1, "unit_rate": 2000, "price": 2000, "currency": "USD"},
                    {"description": "", "quantity": 1, "unit_rate": 300, "price": 300, "currency": "USD"} # invalid description
                ]
            }

            payload = {
                "job_type": "SE",
                "customer_name": mock_st.session_state["new_cust"],
                "salesperson": mock_st.session_state["new_sales"],
                "pol": "",  # invalid
                "pod": "",  # invalid
                "commodity": "",
                "incoterm": "",
                "service_type": "",
            }
            items = mock_st.session_state["new_items"]
            errors = _validate_form(payload, items)
            assert len(errors) > 0
            print("Validation failure detected correctly.")

            # Confirm state was preserved
            assert mock_st.session_state["new_cust"] == "Tenant UAT Customer"
            assert len(mock_st.session_state["new_items"]) == 2
            print("State preservation on failure verified.")

            # 3. Fix & Create Quotation
            payload.update({
                "pol": "Bangkok",
                "pod": "Singapore",
                "commodity": "Rubber",
                "incoterm": "FOB",
                "service_type": "FCL",
                "container_type": "40HC",
                "container_quantity": 1,
                "quotation_date": date.today().isoformat(),
                "validity_date": (date.today() + timedelta(days=30)).isoformat(),
            })
            items[1]["description"] = "Handling fees" # fix line

            qno = create_quotation(payload, items)
            assert qno is not None
            print(f"Quotation {qno} successfully created.")

            # 4. Quotation Revision Control
            rev_qno = create_quotation_revision(qno)
            assert rev_qno != qno
            
            # Verify parent is superseded
            parent_qt = get_quotation_by_no(qno)
            assert parent_qt["status"] == "SUPERSEDED"
            print("Quotation revision immutability and status mapping verified.")

            # 5. Conversion: Quotation -> Booking
            booking_payload = {
                "booking_no": "BK-UAT-26",
                "quotation_id": parent_qt["id"],
                "quotation_no": qno,
                "job_type": "EXPORT SEA FCL",
                "customer_name": "Tenant UAT Customer",
                "pol": "Bangkok",
                "pod": "Singapore",
                "etd": "2026-08-11",
                "eta": "2026-08-25",
                "cargo_type": "FCL",
                "commodity": "Rubber",
                "gross_weight": 12000.0,
                "measurement_cbm": 25.0,
                "container_summary": "1x 40HC",
                "freight_term": "PREPAID",
                "created_by": "QA Agent UAT"
            }
            bk_no = create_booking(booking_payload, {"id": 1, "username": "QA Agent UAT"})
            assert bk_no == "BK-UAT-26"
            print(f"Booking {bk_no} converted from Quotation successfully.")

            # Transition status from DRAFT -> SUBMITTED -> CONFIRMED
            ok1 = update_booking(bk_no, {"status": "SUBMITTED"})
            assert ok1
            ok2 = update_booking(bk_no, {"status": "CONFIRMED"})
            assert ok2
            print("Booking transitioned to CONFIRMED status successfully.")

            # 6. Conversion: Booking -> Job
            job_no = convert_booking_to_job(bk_no, {"id": 1, "username": "QA Agent UAT"})
            assert job_no is not None
            print(f"Job {job_no} generated from Booking successfully.")

            # 7. Sales Ownership & Reporting Month verification
            jobs = list_shipments()
            job = next(j for j in jobs if j["job_no"] == job_no)
            assert job.get("sales_person") == "QA Agent UAT"
            
            # EXPORT month determined by ETD (08/2026)
            rep_month, rep_year = get_reporting_period({"job_type": "EXPORT SEA FCL", "etd": "2026-08-11", "eta": "2026-08-25"})
            assert rep_month == "08"
            assert rep_year == "2026"
            print("Sales ownership and canonical reporting period rules verified.")

            # 8. Profitability calculation
            add_cost_line({
                "shipment_id": job["id"],
                "cost_type": "actual",
                "description": "Port charges",
                "currency": "THB",
                "amount": 5000.0,
                "exchange_rate": 1.0,
                "vendor_name": "Carrier Transporter Test"
            })
            p_summary = get_profit_summary(job["id"])
            assert p_summary["actual_net_profit"] is not None
            print("Job profitability calculations validated.")

            # 9. Clean up states
            _clear_form_state("new")
            print("Form state cleared successfully.")
            
            print("All Phase 26 commercial integration checkpoints PASSED successfully! SUCCESS")

if __name__ == "__main__":
    run_commercial_workflow_test()
