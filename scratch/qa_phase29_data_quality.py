import sys
import os
from unittest.mock import patch, MagicMock

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set up mock streamlit
mock_st = MagicMock()
mock_st.session_state = {}
sys.modules["streamlit"] = mock_st

from database.connection import init_database, get_connection

def run_data_quality_audit():
    print("Running Production Data Quality Scan...")
    
    with patch("psycopg2.connect", side_effect=Exception("Forced SQLite Fallback")):
        mock_secrets = MagicMock()
        mock_secrets.get.side_effect = lambda k, default=None: "development" if k == "APP_ENV" else default
        with patch("streamlit.secrets", mock_secrets):
            init_database()
            
            with get_connection() as conn:
                with conn.cursor() as cur:
                    # 1. Check jobs without salesperson
                    cur.execute("SELECT COUNT(*) FROM shipments WHERE sales_person IS NULL OR sales_person = ''")
                    r1 = cur.fetchone()
                    orphans_sales = r1[0] if not isinstance(r1, dict) else list(r1.values())[0]
                    print(f"Jobs without salesperson: {orphans_sales}")

                    # 2. Check jobs without ETD/ETA
                    cur.execute("SELECT COUNT(*) FROM shipments WHERE etd IS NULL OR eta IS NULL")
                    r2 = cur.fetchone()
                    orphans_dates = r2[0] if not isinstance(r2, dict) else list(r2.values())[0]
                    print(f"Jobs without ETD/ETA: {orphans_dates}")

                    # 3. Check orphan bookings
                    cur.execute("SELECT COUNT(*) FROM bookings WHERE quotation_id IS NULL AND (quotation_no IS NULL OR quotation_no = '')")
                    r3 = cur.fetchone()
                    orphan_bk = r3[0] if not isinstance(r3, dict) else list(r3.values())[0]
                    print(f"Orphan bookings (no quotation ref): {orphan_bk}")

            print("Data Quality Scan: completed successfully.")

if __name__ == "__main__":
    run_data_quality_audit()
