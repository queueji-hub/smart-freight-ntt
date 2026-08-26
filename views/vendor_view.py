import streamlit as st
import pandas as pd
from managers.vendor_manager import get_vendors, create_vendor, update_vendor
from views.document_ui import render_document_section

def render_vendor_list():
    st.subheader("Vendor & Supplier Master / ทะเบียนเจ้าหนี้และผู้ให้บริการ")
    
    vendors = get_vendors()
    if not vendors:
        st.info("No vendors found. Please create one.")
    else:
        df = pd.DataFrame(vendors)
        display_cols = [c for c in ['id', 'vendor_code', 'legal_name', 'roles', 'tax_id', 'country', 'status'] if c in df.columns]
        st.dataframe(df[display_cols], use_container_width=True)

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
                st.session_state["vendor_active_tab"] = "Vendor List"
                st.success(f"Vendor {v_code} created successfully!")
                st.rerun()
            except Exception as e:
                st.error(f"Error: {e}")

def render():
    st.title("🏢 Vendor Management")
    
    tab_opts = ["Vendor List", "Add Vendor", "Vendor Documents"]
    if "vendor_active_tab" not in st.session_state or st.session_state["vendor_active_tab"] not in tab_opts:
        st.session_state["vendor_active_tab"] = tab_opts[0]
        
    active_tab = st.radio(
        "Vendor Navigation",
        tab_opts,
        horizontal=True,
        key="vendor_active_tab",
        label_visibility="collapsed"
    )
    
    if active_tab == tab_opts[0]:
        render_vendor_list()
        
    elif active_tab == tab_opts[1]:
        render_vendor_create()
        
    elif active_tab == tab_opts[2]:
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

