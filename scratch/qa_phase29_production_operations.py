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
from managers.tenant_context import get_current_tenant_id

def run_operations_verification():
    print("Running Production Operations & Governance Verification...")
    
    with patch("psycopg2.connect", side_effect=Exception("Forced SQLite Fallback")):
        mock_secrets = MagicMock()
        mock_secrets.get.side_effect = lambda k, default=None: "development" if k == "APP_ENV" else default
        with patch("streamlit.secrets", mock_secrets):
            init_database()
            
            with get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("DELETE FROM quotations WHERE customer_name = 'Tenant UAT Customer'")
                    cur.execute("DELETE FROM bookings WHERE customer_name = 'Tenant UAT Customer'")
                    cur.execute("DELETE FROM shipments WHERE customer_name = 'Tenant UAT Customer'")
                    cur.execute("DELETE FROM customers WHERE company_name = 'Tenant UAT Customer'")
                    conn.commit()

            c_id = create_customer({
                "company_name": "Tenant UAT Customer",
                "contact_person": "Operations Manager",
                "tel": "54321",
                "email": "ops@uat.com",
                "address": "Zone B",
                "tax_id": "TAX-OPS-29"
            })
            assert c_id is not None

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
            
            booking_payload = {
                "booking_no": "BK-OPS-29",
                "quotation_id": 1,
                "quotation_no": qno,
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
            bk_no = create_booking(booking_payload, {"id": 1, "username": "QA Agent UAT"})
            assert bk_no == "BK-OPS-29"

            update_booking(bk_no, {"status": "SUBMITTED"})
            update_booking(bk_no, {"status": "CONFIRMED"})
            job_no = convert_booking_to_job(bk_no, {"id": 1, "username": "QA Agent UAT"})
            assert job_no is not None
            
            # Check ETD/ETA Reporting period
            rep_month, rep_year = get_reporting_period({"job_type": "EXPORT SEA FCL", "etd": "2026-08-11", "eta": "2026-08-25"})
            assert rep_month == "08"
            assert rep_year == "2026"
            
            print("Operations & Governance Verification: SUCCESS")

if __name__ == "__main__":
    run_operations_verification()
