"""CRM / Customer Management view."""
import streamlit as st
import pandas as pd
from managers.customer_manager import (
    list_customers, create_customer, update_customer, delete_customer,
    get_customer, search_customers,
)
from managers.auth_manager import can_write


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
    
    # ===== ALL CUSTOMERS TAB =====
    with tab_objs[0]:
        col_search, col_count = st.columns([3, 1])
        with col_search:
            query = st.text_input("🔍 Search by company name", key="crm_search",
                                   placeholder="Type partial name...")
        
        rows = search_customers(query) if query else list_customers()
        
        with col_count:
            st.metric("Total", len(rows))
        
        if not rows:
            st.info("No customers found.")
        else:
            df = pd.DataFrame(rows)
            display_cols = ["company_name", "contact_person", "tel", "email",
                            "tax_id", "credit_terms_days", "address"]
            display_cols = [c for c in display_cols if c in df.columns]
            
            st.dataframe(
                df[display_cols],
                use_container_width=True,
                hide_index=True,
                height=400,
                column_config={
                    "company_name": "Company",
                    "contact_person": "Attention",
                    "tel": "Tel.",
                    "email": "Email",
                    "tax_id": "Tax ID",
                    "credit_terms_days": st.column_config.NumberColumn(
                        "Credit (days)", format="%d"),
                    "address": "Address",
                }
            )
            
            # Edit / Delete section
            if can_edit:
                st.markdown("---")
                st.markdown("##### ✏️ Edit / Delete Customer")
                sel_company = st.selectbox(
                    "Select customer",
                    [""] + [r["company_name"] for r in rows],
                    key="crm_select_edit",
                )
                if sel_company:
                    cust = next((r for r in rows if r["company_name"] == sel_company), None)
                    if cust:
                        _edit_form(cust)
    
    # ===== NEW CUSTOMER TAB =====
    if can_edit:
        with tab_objs[1]:
            _new_form()


def _new_form():
    st.subheader("Create New Customer")
    with st.form("new_customer_form"):
        c1, c2 = st.columns(2)
        with c1:
            company_name = st.text_input("Company Name *", key="new_cn")
            contact_person = st.text_input("Contact Person", key="new_cp")
            tel = st.text_input("Phone Number", key="new_tel")
            email = st.text_input("Email", key="new_email")
        with c2:
            tax_id = st.text_input("Tax ID", key="new_tax")
            credit_terms = st.number_input("Credit Terms (days)",
                                            min_value=0, value=30, step=1,
                                            key="new_credit")
            address = st.text_area("Address", key="new_addr", height=100)
        
        notes = st.text_area("Notes", key="new_notes", height=60)
        
        submit = st.form_submit_button("➕ Create", type="primary",
                                        use_container_width=True)
    
    if submit:
        if not company_name.strip():
            st.error("Company Name is required")
        else:
            try:
                new_id = create_customer({
                    "company_name": company_name.strip(),
                    "contact_person": contact_person,
                    "tel": tel, "email": email,
                    "tax_id": tax_id, "address": address,
                    "credit_terms_days": int(credit_terms),
                    "notes": notes,
                })
                st.success(f"✅ Customer created (ID: {new_id})")
                st.rerun()
            except Exception as ex:
                st.error(f"Failed: {ex}")


def _edit_form(cust):
    with st.form(f"edit_customer_{cust['id']}"):
        c1, c2 = st.columns(2)
        with c1:
            company_name = st.text_input("Company Name *",
                value=cust.get("company_name", ""))
            contact_person = st.text_input("Contact Person",
                value=cust.get("contact_person") or "")
            tel = st.text_input("Phone Number",
                value=cust.get("tel") or "")
            email = st.text_input("Email", value=cust.get("email") or "")
        with c2:
            tax_id = st.text_input("Tax ID", value=cust.get("tax_id") or "")
            credit_terms = st.number_input("Credit Terms (days)",
                min_value=0, value=int(cust.get("credit_terms_days") or 30), step=1)
            address = st.text_area("Address",
                value=cust.get("address") or "", height=100)
        
        notes = st.text_area("Notes", value=cust.get("notes") or "", height=60)
        
        col_save, col_del = st.columns([1, 1])
        with col_save:
            save = st.form_submit_button("💾 Save Changes", type="primary",
                                          use_container_width=True)
        with col_del:
            delete = st.form_submit_button("🗑️ Delete (Deactivate)",
                                            use_container_width=True)
    
    if save:
        update_customer(cust["id"], {
            "company_name": company_name.strip(),
            "contact_person": contact_person, "tel": tel, "email": email,
            "tax_id": tax_id, "address": address,
            "credit_terms_days": int(credit_terms), "notes": notes,
        })
        st.success(f"✅ Updated {company_name}")
        st.rerun()
    if delete:
        delete_customer(cust["id"])
        st.success(f"🗑️ Deactivated {cust['company_name']}")
        st.rerun()
