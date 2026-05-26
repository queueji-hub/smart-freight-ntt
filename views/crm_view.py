"""
CRM / Customer Management View Workspace
PostgreSQL Connected - 100% Professional ERP Grade Interface
"""

import streamlit as st
import pandas as pd
from managers.customer_manager import (
    list_customers, create_customer, update_customer, delete_customer,
    get_customer, search_customers,
)
from managers.auth_manager import can_write

# =========================================================
# PERFORMANCE & DATA INTELLIGENCE LAYER
# =========================================================
@st.cache_data(ttl=60)
def get_cached_customers():
    """Fetches and caches customer data to minimize PostgreSQL transaction overhead."""
    try:
        return list_customers() or []
    except Exception as e:
        print(f"[CRM CACHE ERROR]: {str(e)}")
        return []


# =========================================================
# SYSTEM VIEW ROUTER ENTRYPOINT
# =========================================================
def render():
    user = st.session_state.get("user", {})
    role = str(user.get("role", "")).lower()
    can_edit = can_write(role, "crm")
    
    st.markdown("<p style='color: #38BDF8; font-weight: 700; font-size: 13px; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 2px;'>Commercial CRM Matrix</p>", unsafe_allow_html=True)
    st.markdown("<h2 style='margin-top: 0px; font-weight: 800; color:#F8FAFC;'>👥 Customer Master Database</h2>", unsafe_allow_html=True)
    st.caption("Centralized global partner directory — dynamic data mapping engine auto-populates quotations, booking manifests, shipments, and multi-currency billing accounts.")
    
    tabs = ["📋 Ledger Directory"]
    if can_edit:
        tabs.append("➕ Provision New Account")
    
    tab_objs = st.tabs(tabs)
    
    # --- TAB 1: ALL CUSTOMERS MASTER REPOSITORY ---
    with tab_objs[0]:
        col_search, col_count = st.columns([3, 1])
        with col_search:
            query = st.text_input("🔍 Enterprise Directory Search", placeholder="Lookup by partial company name, brand code, identifier...")
        
        # Safe Search Architecture Switch
        with st.spinner("Quoting relational ledger records..."):
            try:
                rows = search_customers(query.strip()) if query else get_cached_customers()
            except Exception as read_err:
                st.error(f"Failed to fetch records from PostgreSQL infrastructure: {str(read_err)}")
                rows = []
        
        with col_count:
            st.metric("Global Partner Accounts", len(rows))
        
        if not rows:
            st.info("ℹ️ No customer profiles match the current ledger query indices.")
        else:
            # PostgreSQL Clean Data Conversion Schema
            df = pd.DataFrame(rows)
            
            # Map structural columns out neatly for professional enterprise presentation
            column_mapping = {
                "id": "Account ID",
                "company_name": "Legal Corporate Name",
                "contact_person": "Primary Attn Contact",
                "tax_id": "Corporate Tax ID Reference",
                "credit_terms_days": "Credit Framework (Days)",
                "address": "Registered Fiscal Address",
                "tel": "Contact Telecom"
            }
            
            # Keep and rename columns if they exist in returning payload
            existing_cols = [col for col in df.columns if col in column_mapping]
            df_display = df[existing_cols].rename(columns=column_mapping)
            
            st.dataframe(
                df_display, 
                use_container_width=True, 
                hide_index=True
            )
            
            # --- ACCOUNT MODIFICATION CONTROL PANEL ---
            if can_edit:
                st.markdown("<div style='margin-top: 25px;'></div>", unsafe_allow_html=True)
                st.markdown("---")
                st.markdown("<h4 style='font-size:16px; color:#F1F5F9; font-weight:700;'>✏️ Enterprise Account Operation Desk</h4>", unsafe_allow_html=True)
                
                # Dynamic Selectbox generation using target identifier strings safely
                company_list = ["-- Select Target Account to Modify --"] + [str(r["company_name"]) for r in rows if "company_name" in r]
                sel_company = st.selectbox("Select Account", options=company_list, label_visibility="collapsed")
                
                if sel_company and sel_company != "-- Select Target Account to Modify --":
                    cust = next((r for r in rows if str(r.get("company_name")) == sel_company), None)
                    if cust:
                        st.markdown(f"<div style='padding: 18px; border: 1px solid #1E293B; background-color: #0F172A; border-radius:12px; margin-top:14px;'>", unsafe_allow_html=True)
                        _edit_form(cust)
                        st.markdown("</div>", unsafe_allow_html=True)
    
    # --- TAB 2: PROVISIONING NEW DATA PIPELINE ---
    if can_edit:
        with tab_objs[1]:
            _new_form()


# =========================================================
# SUB-COMPONENT: CREATION ENGINE FORM
# =========================================================
def _new_form():
    st.markdown("<h4 style='font-size:16px; color:#F1F5F9; font-weight:700;'>➕ Provision New Legal Corporate Entity Account</h4>", unsafe_allow_html=True)
    
    with st.form("new_customer_form_enterprise", clear_on_submit=True):
        with st.container(border=True):
            st.markdown("**📋 General Parameters Profile**")
            c1, c2 = st.columns(2)
            with c1:
                company_name = st.text_input("Legal Corporate Registered Name *", placeholder="e.g., Global Logistics Corp Ltd.")
                contact_person = st.text_input("Primary Authorized Contact Person", placeholder="e.g., John Doe (Procurement Manager)")
                tel = st.text_input("Authorized Telecom / Contact Phone Line", placeholder="e.g., +662-123-4567")
            with c2:
                tax_id = st.text_input("Government Tax Registration Reference ID (Tax ID)", placeholder="e.g., 01055XXXXXXXX")
                credit_terms = st.number_input("Commercial Credit Risk Terms (Days Default)", min_value=0, max_value=365, value=30, step=1)
            
            address = st.text_area("Registered Legal & Operations Fiscal Address Statement", placeholder="Complete shipping / corporate billing destination address...")
            
        submit = st.form_submit_button("🚀 Commit Account Provisioning to Ledger", type="primary", use_container_width=True)
    
    if submit:
        if not company_name.strip():
            st.error("⚠️ Validation Refusal: Legal Corporate Name parameter is strictly mandatory.")
        else:
            with st.spinner("Executing transactional account creation..."):
                try:
                    payload = {
                        "company_name": company_name.strip(),
                        "contact_person": contact_person.strip() if contact_person else None,
                        "tax_id": tax_id.strip() if tax_id else None,
                        "credit_terms_days": int(credit_terms),
                        "address": address.strip() if address else None,
                        "tel": tel.strip() if tel else None
                    }
                    create_customer(payload)
                    st.toast("✅ Legal entity account successfully committed to database indexes!", icon="✅")
                    st.cache_data.clear()  # Clear cache to force reload database entries dynamically
                    st.rerun()
                except Exception as ex:
                    st.error(f"🚨 Relational Ledger Processing Exception Intercepted: {str(ex)}")


# =========================================================
# SUB-COMPONENT: EDIT/RECONCILIATION ENGINE FORM
# =========================================================
def _edit_form(cust):
    st.markdown(f"##### 🔒 Workspace Lockout: Editing Record ID `{cust.get('id', 'Unknown')}`")
    
    with st.form(f"edit_customer_secure_{cust['id']}"):
        company_name = st.text_input("Legal Corporate Registered Name *", value=str(cust.get("company_name", "")))
        
        c1, c2 = st.columns(2)
        with c1:
            contact_person = st.text_input("Primary Authorized Contact Person", value=str(cust.get("contact_person") or ""))
            tel = st.text_input("Authorized Telecom / Contact Phone Line", value=str(cust.get("tel") or ""))
        with c2:
            tax_id = st.text_input("Government Tax Registration Reference ID (Tax ID)", value=str(cust.get("tax_id") or ""))
            
            # Safely transform PostgreSQL legacy int formats
            try:
                current_credit_days = int(cust.get("credit_terms_days") or 30)
            except (ValueError, TypeError):
                current_credit_days = 30
            credit_terms = st.number_input("Commercial Credit Risk Terms (Days Default)", min_value=0, max_value=365, value=current_credit_days)
            
        address = st.text_area("Registered Legal & Operations Fiscal Address Statement", value=str(cust.get("address") or ""))
        
        col_save, col_del = st.columns([1, 1])
        save = col_save.form_submit_button("💾 Overwrite Existing Ledger Parameters", type="primary", use_container_width=True)
        delete = col_del.form_submit_button("🗑️ Deactivate / Purge Account Context", use_container_width=True)
    
    if save:
        if not company_name.strip():
            st.error("⚠️ Validation Error: Corporate Name is required.")
            return
        
        with st.spinner("Applying overwrite vector..."):
            try:
                update_payload = {
                    "company_name": company_name.strip(),
                    "contact_person": contact_person.strip() if contact_person else None,
                    "tax_id": tax_id.strip() if tax_id else None,
                    "credit_terms_days": int(credit_terms),
                    "address": address.strip() if address else None,
                    "tel": tel.strip() if tel else None
                }
                update_customer(cust["id"], update_payload)
                st.toast("💾 Ledger metrics modified and updated successfully.", icon="✅")
                st.cache_data.clear()
                st.rerun()
            except Exception as update_err:
                st.error(f"🚨 Pipeline Intercept Error during update action: {str(update_err)}")
        
    if delete:
        with st.spinner("Executing purge schema vector..."):
            try:
                delete_customer(cust["id"])
                st.toast("🗑️ Account context successfully pruned from ledger registry.")
                st.cache_data.clear()