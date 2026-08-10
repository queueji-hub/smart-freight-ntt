import streamlit as st
import pandas as pd
from managers.vendor_manager import get_vendors, create_vendor, update_vendor
from views.document_ui import render_document_section

def render_vendor_list():
    st.subheader("Vendor Master / ทะเบียนผู้ขาย")
    
    vendors = get_vendors()
    if not vendors:
        st.info("No vendors found. Please create one.")
    else:
        df = pd.DataFrame(vendors)
        st.dataframe(df[['id', 'vendor_code', 'legal_name', 'country', 'status', 'created_at']], use_container_width=True)

def render_vendor_create():
    st.subheader("Add New Vendor / เพิ่มผู้ขาย")
    with st.form("new_vendor_form"):
        col1, col2 = st.columns(2)
        v_code = col1.text_input("Vendor Code*", help="e.g. V-TH-001")
        v_name = col2.text_input("Legal Name*")
        
        c1, c2 = st.columns(2)
        v_tax = c1.text_input("Tax ID")
        v_country = c2.text_input("Country", value="TH")
        
        submit = st.form_submit_button("Create Vendor")
        if submit:
            if not v_code or not v_name:
                st.error("Vendor Code and Legal Name are required.")
                return
            
            try:
                vid = create_vendor({
                    "vendor_code": v_code,
                    "legal_name": v_name,
                    "tax_id": v_tax,
                    "country": v_country
                }, st.session_state.get('user'))
                st.success(f"Vendor {v_code} created successfully!")
                st.rerun()
            except Exception as e:
                st.error(f"Error: {e}")

def render():
    st.title("🏢 Vendor Management")
    
    tab1, tab2, tab3 = st.tabs(["Vendor List", "Add Vendor", "Vendor Documents"])
    
    with tab1:
        render_vendor_list()
        
    with tab2:
        render_vendor_create()
        
    with tab3:
        st.subheader("Vendor Document Center")
        vendors = get_vendors()
        if vendors:
            v_opts = {f"{v['vendor_code']} - {v['legal_name']}": v['id'] for v in vendors}
            sel = st.selectbox("Select Vendor", list(v_opts.keys()))
            if sel:
                vid = v_opts[sel]
                render_document_section("vendor", str(vid))
        else:
            st.warning("Please create a vendor first.")
