import sys
import os
from unittest.mock import patch, MagicMock
from datetime import date, timedelta

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set up mock streamlit
mock_st = MagicMock()
mock_st.session_state = {}
sys.modules["streamlit"] = mock_st

from database.connection import init_database, get_connection
from views.quotation_view import _validate_form, _clear_form_state, _blank_item
from managers.quotation_manager import create_quotation, get_quotation_by_no, list_quotations, duplicate_quotation, update_quotation
from managers.tenant_context import get_current_tenant_id

def run_realworld_uat():
    print("Initializing Phase 24 Realworld UAT Verification...")
    
    with patch("psycopg2.connect", side_effect=Exception("Forced SQLite Fallback")):
        mock_secrets = MagicMock()
        mock_secrets.get.side_effect = lambda k, default=None: "development" if k == "APP_ENV" else default
        with patch("streamlit.secrets", mock_secrets):
            init_database()
            print("Database initialized successfully.")
            
            # Clean old test records
            with get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("DELETE FROM quotations WHERE customer_name = 'Antigravity Tenant A'")
                    conn.commit()

            # Initialize session state cache
            prefix = "new"
            mock_st.session_state = {
                f"{prefix}_cust": "Antigravity Tenant A",
                f"{prefix}_sales": "QA Agent",
                f"{prefix}_items": [
                    {"description": "Freight", "quantity": 1, "unit_rate": 1500, "price": 1500, "currency": "USD"},
                    {"description": "", "quantity": 1, "unit_rate": 200, "price": 200, "currency": "USD"} # invalid description
                ]
            }

            # 1. Validation failure test
            payload = {
                "job_type": "SE",
                "customer_name": mock_st.session_state[f"{prefix}_cust"],
                "salesperson": mock_st.session_state[f"{prefix}_sales"],
                "pol": "",  # invalid
                "pod": "",  # invalid
                "commodity": "", # invalid
                "incoterm": "", # invalid
                "service_type": "", # invalid
            }
            items = mock_st.session_state[f"{prefix}_items"]
            errors = _validate_form(payload, items)
            
            assert len(errors) > 0
            print("Validation failure correctly returned errors:", errors)
            
            # Check state preservation
            assert mock_st.session_state[f"{prefix}_cust"] == "Antigravity Tenant A"
            assert len(mock_st.session_state[f"{prefix}_items"]) == 2
            assert mock_st.session_state[f"{prefix}_items"][1]["unit_rate"] == 200
            print("All form state values and line items verified as preserved on failure.")

            # 2. Partial fix test (fix POL/POD/commodity/incoterm/service_type/description)
            payload["pol"] = "Bangkok"
            payload["pod"] = "Singapore"
            payload["commodity"] = "General cargo"
            payload["incoterm"] = "FOB"
            payload["service_type"] = "FCL"
            payload["container_type"] = "40HC"
            payload["container_quantity"] = 1
            payload["quotation_date"] = date.today().isoformat()
            payload["validity_date"] = (date.today() + timedelta(days=30)).isoformat()
            items[1]["description"] = "Local charges" # fix description
            
            errors_fixed = _validate_form(payload, items)
            assert len(errors_fixed) == 0
            print("Partial fix verified: validation succeeds.")

            # 3. Successful create
            qno = create_quotation(payload, items)
            assert qno is not None
            print(f"Quotation {qno} successfully created.")

            # 4. Post-create check: load and verify
            qt = get_quotation_by_no(qno)
            assert qt["customer_name"] == "Antigravity Tenant A"
            assert len(qt["items"]) == 2
            print("Quotation detail verified in DB.")

            # 5. Duplication test
            qno_dup = duplicate_quotation(qno)
            assert qno_dup != qno
            qt_dup = get_quotation_by_no(qno_dup)
            assert qt_dup["customer_name"] == "Antigravity Tenant A"
            assert len(qt_dup["items"]) == 2
            print(f"Duplicated quotation {qno_dup} successfully verified.")

            # 6. Edit/Update verification
            payload["commodity"] = "Updated cargo"
            update_quotation(qno, payload, items)
            qt_updated = get_quotation_by_no(qno)
            assert qt_updated["commodity"] == "Updated cargo"
            print("Quotation edit/update verified.")

            # 7. Clean form state
            _clear_form_state(prefix)
            assert f"{prefix}_cust" not in mock_st.session_state
            print("Form state cleaned after creation.")
            
            print("Real-world UAT UAT checks PASSED successfully!")

if __name__ == "__main__":
    run_realworld_uat()
