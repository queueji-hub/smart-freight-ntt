import sys
import os
from unittest.mock import patch, MagicMock

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set up mock streamlit
mock_st = MagicMock()
mock_st.session_state = {}
sys.modules["streamlit"] = mock_st

from views.quotation_view import _validate_form

def test_ui_presentation():
    print("Running Phase 25 Wording & Sizing UAT Tests...")
    
    # 1. Validation Fail test for compact messaging
    data = {
        "job_type": "SE",
        "customer_name": "QA Customer",
        "salesperson": "QA Agent",
        "pol": "",
        "pod": "",
        "incoterm": "",
        "service_type": "",
    }
    items = [{"description": ""}]
    
    errors = _validate_form(data, items)
    
    # Assert messages follow the new streamlined format
    assert "POL is required for Sea Freight." in errors
    assert "POD is required for Sea Freight." in errors
    assert "Service Type is required." in errors
    assert "Line 1: Description is required." in errors
    
    print("All Phase 25 UAT validation messages validated.")
    print("All Phase 25 tests PASSED!")

if __name__ == "__main__":
    test_ui_presentation()
