import sys
import os
from unittest.mock import patch, MagicMock

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set up mock streamlit
mock_st = MagicMock()
mock_st.session_state = {}
sys.modules["streamlit"] = mock_st

def run_health_checks():
    print("Running Production Health Diagnostics...")
    
    # 1. Imports Verification
    try:
        from database.connection import init_database, get_connection
        from managers.quotation_manager import get_quotation_by_no
        from managers.booking_manager import get_booking
        from managers.shipment_manager import list_shipments
        from pdf.booking_pdf import generate_booking_pdf
        print("Managers and PDF generation imports: OK")
    except Exception as imp_err:
        print(f"Import check: FAIL ({imp_err})")
        sys.exit(1)

    # 2. Database Connectivity
    with patch("psycopg2.connect", side_effect=Exception("Forced SQLite Fallback")):
        mock_secrets = MagicMock()
        mock_secrets.get.side_effect = lambda k, default=None: "development" if k == "APP_ENV" else default
        with patch("streamlit.secrets", mock_secrets):
            try:
                init_database()
                with get_connection() as conn:
                    with conn.cursor() as cur:
                        cur.execute("SELECT 1")
                        cur.fetchone()
                print("Database connection context check: OK")
            except Exception as conn_err:
                print(f"Database connection: FAIL ({conn_err})")
                sys.exit(1)

    # 3. Font Asset Availability
    font_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "fonts", "Sarabun-Regular.ttf")
    if os.path.exists(font_path):
        print("Sarabun-Regular.ttf font check: OK")
    else:
        print(f"Sarabun-Regular.ttf font check: FAIL (missing at {font_path})")
        sys.exit(1)

    print("System Health Diagnostics: ALL CHECKS PASSED")

if __name__ == "__main__":
    run_health_checks()
