"""CRM / Customer Management view."""
import streamlit as st
import pandas as pd
from managers.customer_manager import (
    list_customers, create_customer, update_customer, delete_customer,
    get_customer, search_customers,
)
from managers.auth_manager import can_write

# ใช้ Caching เพื่อลดการโหลดข้อมูลซ้ำจาก Database
@st.cache_data(ttl=60)
def get_cached_customers():
    return list_customers()

def render():
    user = st.session_state.get("user", {})
    role = user.get("role", "")
    can_edit = can_write(role, "crm")
    
    st.title("👥 CRM / Customer Database")
    st.caption("Centralized customer database — auto-fills quotation, booking, shipment, billing")
    
    tabs = ["📋 All Customers"]
    if can_edit:
        tabs.append("➕ New Customer")
    
    tab_objs = st.tabs(tabs)
    
    with tab_objs[0]:
        col_search, col_count = st.columns([3, 1])
        with col_search:
            query = st.text_input("🔍 Search by company name", placeholder="Type partial name...")
        
        # ใช้ Search หรือดึงจาก Cache
        rows = search_customers(query) if query else get_cached_customers()
        
        with col_count:
            st.metric("Total", len(rows))
        
        if not rows:
            st.info("No customers found.")
        else:
            df = pd.DataFrame(rows)
            st.dataframe(df, use_container_width=True, hide_index=True)
            
            if can_edit:
                st.markdown("---")
                st.markdown("##### ✏️ Edit / Delete Customer")
                sel_company = st.selectbox("Select customer to edit", [""] + [r["company_name"] for r in rows])
                if sel_company:
                    cust = next((r for r in rows if r["company_name"] == sel_company), None)
                    if cust: _edit_form(cust)
    
    if can_edit:
        with tab_objs[1]:
            _new_form()

def _new_form():
    st.subheader("Create New Customer")
    with st.form("new_customer_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            company_name = st.text_input("Company Name *")
            contact_person = st.text_input("Contact Person")
        with c2:
            tax_id = st.text_input("Tax ID")
            credit_terms = st.number_input("Credit Terms (days)", min_value=0, value=30, step=1)
        
        address = st.text_area("Address")
        submit = st.form_submit_button("➕ Create", type="primary", use_container_width=True)
    
    if submit:
        if not company_name.strip():
            st.error("Company Name is required")
        else:
            try:
                create_customer({"company_name": company_name.strip(), "contact_person": contact_person, "tax_id": tax_id, "credit_terms_days": int(credit_terms), "address": address})
                st.toast("✅ Customer created successfully!", icon="✅")
                st.rerun()
            except Exception as ex:
                st.error(f"Failed: {ex}")

def _edit_form(cust):
    with st.form(f"edit_customer_{cust['id']}"):
        company_name = st.text_input("Company Name *", value=cust.get("company_name", ""))
        c1, c2 = st.columns(2)
        with c1:
            contact_person = st.text_input("Contact Person", value=cust.get("contact_person") or "")
        with c2:
            credit_terms = st.number_input("Credit Terms (days)", min_value=0, value=int(cust.get("credit_terms_days") or 30))
        
        col_save, col_del = st.columns([1, 1])
        save = col_save.form_submit_button("💾 Save Changes", type="primary", use_container_width=True)
        delete = col_del.form_submit_button("🗑️ Delete", use_container_width=True)
    
    if save:
        update_customer(cust["id"], {"company_name": company_name.strip(), "contact_person": contact_person, "credit_terms_days": int(credit_terms)})
        st.toast("✅ Updated successfully!")
        st.rerun()
        
    if delete:
        # ยืนยันก่อนลบ (Optional: สามารถสร้างสถานะให้กดยืนยันอีกครั้งได้ถ้าต้องการ)
        delete_customer(cust["id"])
        st.toast("🗑️ Deactivated successfully!")
        st.rerun()