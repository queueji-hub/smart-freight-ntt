import os
import sys

os.environ['APP_ENV'] = 'development'
sys.path.append(os.path.abspath('.'))

from managers.booking_manager import create_booking, get_booking, list_bookings, update_booking, delete_booking
import streamlit as st

class MockSessionState:
    def __init__(self):
        self.user = {}
        
st.session_state = MockSessionState()

def test_booking_isolation():
    print("Testing Tenant Isolation on Booking Manager")
    
    # 1. Tenant A creates booking
    st.session_state.user['tenant_id'] = 'TENANT_A'
    st.session_state.user['id'] = 1
    booking_no = create_booking({
        'job_type': 'SE',
        'customer_name': 'Tenant A Customer',
        'pol': 'BKK',
        'pod': 'SIN'
    }, user={'id': 1})
    
    # Tenant A can read it
    b_a = get_booking(booking_no)
    assert b_a is not None, "Tenant A should see its own booking"
    print("PASS: Tenant A can read own booking")
    
    # 2. Tenant B attempts to read Booking A
    st.session_state.user['tenant_id'] = 'TENANT_B'
    b_b_view = get_booking(booking_no)
    assert b_b_view is None, "Tenant B should NOT see Tenant A's booking"
    print("PASS: Tenant B cannot read Tenant A booking")
    
    # Tenant B attempts search/list
    search_res = list_bookings(search_query=booking_no)
    assert len(search_res) == 0, "Tenant B should NOT see Tenant A in list"
    print("PASS: Tenant B list/search isolation")
    
    # 3. Tenant B attempts update Booking A
    try:
        update_res = update_booking(booking_no, {'customer_name': 'Hacked'})
        assert update_res is False, "Tenant B should NOT be able to update Tenant A's booking"
    except Exception as e:
        # If it throws an exception (e.g. ValueError due to lock check), that's fine too as long as it doesn't update.
        assert "Booking not found" in str(e) or update_res is False
    print("PASS: Tenant B update isolation")
    
    # 4. Tenant B attempts delete Booking A
    st.session_state.user['tenant_id'] = 'TENANT_B'
    del_res = delete_booking(booking_no)
    assert del_res is False or del_res is None, "Tenant B should NOT be able to delete Tenant A's booking"
    print("PASS: Tenant B delete isolation")

    print("ALL BOOKING ISOLATION TESTS PASSED")

if __name__ == '__main__':
    test_booking_isolation()
