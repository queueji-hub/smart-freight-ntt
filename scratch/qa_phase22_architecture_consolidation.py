import sys
import os
import streamlit as st
from unittest.mock import patch, MagicMock
from decimal import Decimal

# Add workspace root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.connection import get_connection, init_database
from managers.customer_manager import create_customer, list_customers
from managers.quotation_manager import create_quotation
from managers.booking_manager import create_booking, list_bookings
from managers.shipment_manager import create_shipment, list_shipments
from managers.milestone_manager import add_milestone, list_milestones
from managers.container_manager import add_container, list_containers
from managers.bl_manager import create_bl, list_bls
from managers.finance_manager import create_invoice, list_invoices
from managers.ap_manager import create_ap_voucher, get_ap_vouchers
from managers.profit_manager import add_cost_line, get_profit_summary
from managers.month_end_manager import get_month_end_summary
from managers.report_manager import get_company_monthly_performance
from managers.vendor_manager import create_vendor, get_vendors

def run_regression_test():
    print("Initializing Phase 22 Master Regression and Reconciliation Suite...")
    
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
                    cur.execute("DELETE FROM bookings WHERE booking_no = 'BK-TEST-P22'")
                    cur.execute("DELETE FROM customers WHERE company_name = 'Antigravity Tenant A'")
                    cur.execute("DELETE FROM shipments WHERE customer_name = 'Antigravity Tenant A'")
                    cur.execute("DELETE FROM vendors WHERE legal_name = 'Carrier Transporter Test'")
                    cur.execute("DELETE FROM ap_vouchers WHERE invoice_no = 'AP-TEST-VCH'")
                    cur.execute("DELETE FROM invoices WHERE customer_name = 'Antigravity Tenant A'")
                    conn.commit()
            
            # 2. Customer
            c_data = {
                "company_name": "Antigravity Tenant A",
                "contact_person": "Lead QA",
                "tel": "999",
                "email": "qa@test.com",
                "address": "Bangkok",
                "tax_id": "TX22"
            }
            c_id = create_customer(c_data)
            assert c_id is not None
            print("Customer validated.")

            # 3. Vendor
            v_id = create_vendor({
                "vendor_code": "V-QA-22",
                "legal_name": "Carrier Transporter Test",
                "tax_id": "TAX-V-22",
                "country": "TH",
                "currency": "THB"
            }, {"id": 1, "username": "qa_runner"})
            assert v_id is not None
            print("Vendor validated.")

            # 4. Quotation
            q_no = create_quotation({
                "job_type": "SE",
                "customer_name": "Antigravity Tenant A",
                "quotation_date": "2026-08-11"
            }, [{"description": "Sea Freight", "price": 1000.0, "unit": "CNTR"}])
            assert q_no is not None
            print("Quotation validated.")

            # 5. Booking
            create_booking({
                "booking_no": "BK-TEST-P22",
                "job_type": "EXPORT SEA FCL",
                "customer_name": "Antigravity Tenant A",
                "pol": "Bangkok",
                "pod": "Singapore",
                "etd": "2026-08-11"
            })
            bookings = list_bookings()
            assert any(b["booking_no"] == "BK-TEST-P22" for b in bookings)
            print("Booking validated.")

            # 6. Job / Shipment (EXPORT)
            s_data = {
                "job_type": "EXPORT SEA FCL",
                "customer_name": "Antigravity Tenant A",
                "etd": "2026-08-11",
                "eta": "2026-08-15"
            }
            job_no = create_shipment(s_data)
            assert job_no is not None
            jobs = list_shipments()
            job = next(j for j in jobs if j["job_no"] == job_no)
            # EXPORT = ETD Month (08)
            assert job["reporting_month"] == "08"
            assert job["reporting_year"] == "2026"
            print("Shipment creation & EXPORT = ETD verified.")

            # 7. Milestone
            m_id = add_milestone(
                shipment_id=job["id"],
                job_no=job_no,
                code="JOB_CREATED",
                name="Job Created",
                event_date="2026-08-11 10:00:00"
            )
            assert m_id is not None
            print("Milestones verified.")

            # 8. Container
            ok = add_container({
                "shipment_id": job["id"],
                "job_no": job_no,
                "container_no": "CONTAINER-P22",
                "container_size": "40HC"
            })
            assert ok
            print("Container verified.")

            # 9. HBL / MBL
            bl_no = create_bl(
                job_no,
                "HBL",
                {"id": 1, "username": "qa_runner"},
                extra_data={
                    "bl_no": "HBL-QA-22",
                    "shipper": "Antigravity Tenant A"
                }
            )
            assert bl_no is not None
            print("BL verified.")

            # 10. Financial AR Invoice
            inv_no = create_invoice(
                "default",
                {
                    "customer_name": "Antigravity Tenant A",
                    "issue_date": "2026-08-11",
                    "due_date": "2026-09-11"
                },
                [{"description": "Ocean Freight", "quantity": 1, "unit_price": 5000.0, "amount": 5000.0}],
                {"id": 1, "username": "qa_runner"}
            )
            assert inv_no is not None
            print("Invoice AR validated.")

            # 11. Financial AP Voucher
            ap_id = create_ap_voucher({
                "vendor_id": v_id,
                "job_no": job_no,
                "invoice_no": "AP-TEST-VCH",
                "invoice_date": "2026-08-11",
                "total": 3500.0
            }, {"id": 1, "username": "qa_runner"})
            assert ap_id is not None
            print("AP Voucher validated.")

            # 12. Month End Closing
            summary = get_month_end_summary("08", "2026")
            assert summary["job_stats"]["total_jobs"] > 0
            print("Month-End validated.")
            
            # 13. Company monthly performance
            perf = get_company_monthly_performance("08", "2026")
            assert perf["operations"]["total_jobs"] > 0
            print("Company performance validated.")

if __name__ == "__main__":
    run_regression_test()
    print("Master regression suite executed successfully! SUCCESS")
