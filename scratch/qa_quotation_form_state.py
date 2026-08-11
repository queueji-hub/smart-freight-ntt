import sys
import os
from unittest.mock import patch, MagicMock

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set up mock streamlit before importing views.quotation_view
mock_st = MagicMock()
mock_st.session_state = {}
sys.modules["streamlit"] = mock_st

from views.quotation_view import _validate_form, _clear_form_state, _blank_item

def test_validation_ux():
    print("Running Phase 23 Quotation Form State & Validation UX Tests...")

    # Initialize mock session state
    mock_st.session_state = {
        "new_cust": "QA Customer",
        "new_sales": "QA Agent",
        "new_items": [
            {"description": "", "quantity": 1, "unit_rate": 100}
        ]
    }

    # 1. Validation Fail: description empty
    data = {
        "job_type": "SE",
        "customer_name": "QA Customer",
        "salesperson": "QA Agent",
        "pol": "",  # missing for sea freight
        "pod": "",  # missing for sea freight
    }
    items = mock_st.session_state["new_items"]
    
    errors = _validate_form(data, items)
    
    # Assert errors are found
    assert len(errors) > 0, "Validation should have failed"
    print("Validation failed correctly as expected.")
    
    # Verify that form state was preserved and NOT cleared
    assert mock_st.session_state["new_cust"] == "QA Customer"
    assert mock_st.session_state["new_sales"] == "QA Agent"
    assert len(mock_st.session_state["new_items"]) == 1
    print("Form state successfully preserved after validation failure.")

    # 2. Simulate form clear after success
    _clear_form_state("new")
    assert "new_cust" not in mock_st.session_state
    assert "new_sales" not in mock_st.session_state
    print("Form state successfully cleared after simulated successful save.")
    
    print("All Phase 23 tests PASSED!")

if __name__ == "__main__":
    test_validation_ux()
