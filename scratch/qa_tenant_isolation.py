import os
import sys

os.environ['APP_ENV'] = 'development'
sys.path.append(os.path.abspath('.'))

from managers.customer_manager import create_customer, get_customer_by_name, search_customers, update_customer, delete_customer
import streamlit as st

class MockSessionState:
    def __init__(self):
        self.user = {}
        
st.session_state = MockSessionState()

def test_tenant_isolation():
    print("Testing Tenant Isolation on Customer Manager")
    
    # 1. Tenant A creates customer
    st.session_state.user['tenant_id'] = 'TENANT_A'
    create_customer({
        'company_name': 'Tenant A Customer',
        'contact_person': 'Alice',
        'is_active': True
    })
    
    # Tenant A can read it
    cust_a = get_customer_by_name('Tenant A Customer')
    assert cust_a is not None, "Tenant A should see its own customer"
    print("PASS: Tenant A can read own customer")
    
    # 2. Tenant B attempts to read Customer A
    st.session_state.user['tenant_id'] = 'TENANT_B'
    cust_b_view = get_customer_by_name('Tenant A Customer')
    assert cust_b_view is None, "Tenant B should NOT see Tenant A's customer"
    print("PASS: Tenant B cannot read Tenant A customer")
    
    # Tenant B attempts search
    search_res = search_customers('Tenant A')
    assert len(search_res) == 0, "Tenant B should NOT see Tenant A in search"
    print("PASS: Tenant B search isolation")
    
    # 3. Tenant B attempts update Customer A
    update_res = update_customer('Tenant A Customer', {'company_name': 'Hacked', 'contact_person': 'Bob'})
    assert update_res is False, "Tenant B should NOT be able to update Tenant A's customer"
    print("PASS: Tenant B update isolation")
    
    # 4. Tenant B attempts delete Customer A
    st.session_state.user['tenant_id'] = 'TENANT_A'
    cust_id = get_customer_by_name('Tenant A Customer')['id']
    
    st.session_state.user['tenant_id'] = 'TENANT_B'
    del_res = delete_customer(cust_id)
    assert del_res is False or del_res is None, "Tenant B should NOT be able to delete Tenant A's customer"
    print("PASS: Tenant B delete isolation")

    print("ALL CUSTOMER ISOLATION TESTS PASSED")

if __name__ == '__main__':
    test_tenant_isolation()
