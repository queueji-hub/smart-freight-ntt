import os
import sys

os.environ['APP_ENV'] = 'development'
sys.path.append(os.path.abspath('.'))

from managers.shipment_manager import create_shipment, get_shipment, list_shipments, update_shipment, delete_shipment
import streamlit as st

class MockSessionState:
    def __init__(self):
        self.user = {}
        
st.session_state = MockSessionState()

def test_shipment_isolation():
    print("Testing Tenant Isolation on Shipment Manager")
    
    # 1. Tenant A creates shipment
    st.session_state.user['tenant_id'] = 'TENANT_A'
    st.session_state.user['id'] = 1
    job_no = create_shipment({
        'job_type': 'SE',
        'customer_name': 'Tenant A Customer',
        'pol': 'BKK',
        'pod': 'SIN'
    })
    
    # Tenant A can read it
    s_a = get_shipment(job_no)
    assert s_a is not None, "Tenant A should see its own shipment"
    print("PASS: Tenant A can read own shipment")
    
    # 2. Tenant B attempts to read Shipment A
    st.session_state.user['tenant_id'] = 'TENANT_B'
    s_b_view = get_shipment(job_no)
    assert s_b_view is None, "Tenant B should NOT see Tenant A's shipment"
    print("PASS: Tenant B cannot read Tenant A shipment")
    
    # Tenant B attempts search/list
    search_res = list_shipments(search_query=job_no)
    assert len(search_res) == 0, "Tenant B should NOT see Tenant A in list"
    print("PASS: Tenant B list/search isolation")
    
    # 3. Tenant B attempts update Shipment A
    try:
        update_res = update_shipment(job_no, {'customer_name': 'Hacked'})
        assert update_res is False, "Tenant B should NOT be able to update Tenant A's shipment"
    except Exception as e:
        assert "not found" in str(e).lower() or update_res is False
    print("PASS: Tenant B update isolation")
    
    # 4. Tenant B attempts delete Shipment A
    st.session_state.user['tenant_id'] = 'TENANT_B'
    del_res = delete_shipment(job_no)
    assert del_res is False or del_res is None, "Tenant B should NOT be able to delete Tenant A's shipment"
    print("PASS: Tenant B delete isolation")

    print("ALL SHIPMENT ISOLATION TESTS PASSED")

if __name__ == '__main__':
    test_shipment_isolation()
