import streamlit as st
import pandas as pd
from datetime import datetime
from managers.ap_manager import get_ap_vouchers, create_ap_voucher, update_ap_voucher_status
from managers.vendor_manager import get_vendors
from views.document_ui import render_document_section

def render_ap_list():
    st.subheader("Accounts Payable Vouchers / เจ้าหนี้การค้า")
    
    vouchers = get_ap_vouchers()
    if not vouchers:
        st.info("No AP Vouchers found.")
    else:
        df = pd.DataFrame(vouchers)
        st.dataframe(
            df[['id', 'vendor_name', 'invoice_no', 'invoice_date', 'job_no', 'currency', 'total', 'status']], 
            use_container_width=True
        )

def render_ap_create():
    st.subheader("Register Vendor Invoice (AP Voucher) / บันทึกตั้งหนี้")
    
    vendors = get_vendors()
    if not vendors:
        st.error("Please create a vendor first.")
        return
        
    v_opts = {f"{v['vendor_code']} - {v['legal_name']}": v['id'] for v in vendors}
    
    with st.form("new_ap_form"):
        col1, col2 = st.columns(2)
        v_sel = col1.selectbox("Select Vendor*", list(v_opts.keys()))
        job_no = col2.text_input("Job / Shipment No.", help="Link to an existing Job")
        
        c1, c2, c3 = st.columns(3)
        inv_no = c1.text_input("Vendor Invoice No.*")
        inv_date = c2.date_input("Invoice Date*")
        due_date = c3.date_input("Due Date")
        
        fc1, fc2, fc3, fc4 = st.columns(4)
        curr = fc1.text_input("Currency", value="THB")
        subtotal = fc2.number_input("Subtotal", min_value=0.0, format="%.2f")
        tax = fc3.number_input("Tax", min_value=0.0, format="%.2f")
        total = fc4.number_input("Total", min_value=0.0, format="%.2f", value=subtotal+tax)
        
        submit = st.form_submit_button("Register AP Voucher")
        if submit:
            if not inv_no:
                st.error("Invoice No is required.")
                return
            
            try:
                ap_id = create_ap_voucher({
                    "vendor_id": v_opts[v_sel],
                    "job_no": job_no,
                    "invoice_no": inv_no,
                    "invoice_date": inv_date.strftime("%Y-%m-%d"),
                    "due_date": due_date.strftime("%Y-%m-%d"),
                    "currency": curr,
                    "subtotal": subtotal,
                    "tax": tax,
                    "total": total
                }, st.session_state.get('user'))
                st.success(f"AP Voucher for {inv_no} created successfully! (ID: {ap_id})")
                st.rerun()
            except Exception as e:
                st.error(f"Error: {e}")

def render_ap_workflow():
    st.subheader("AP Approval & Documents")
    vouchers = get_ap_vouchers()
    if not vouchers:
        st.warning("No vouchers available.")
        return
        
    for v in vouchers:
        with st.expander(f"🧾 AP: {v['invoice_no']} | Vendor: {v['vendor_name']} | Job: {v['job_no']} | Status: {v['status']}"):
            st.write(f"**Total:** {v['total']:,.2f} {v['currency']}")
            
            c1, c2 = st.columns(2)
            new_status = c1.selectbox(
                "Update Status", 
                ["DRAFT", "SUBMITTED", "UNDER_REVIEW", "APPROVED", "REJECTED", "POSTED", "CANCELLED"],
                index=["DRAFT", "SUBMITTED", "UNDER_REVIEW", "APPROVED", "REJECTED", "POSTED", "CANCELLED"].index(v['status']) if v['status'] in ["DRAFT", "SUBMITTED", "UNDER_REVIEW", "APPROVED", "REJECTED", "POSTED", "CANCELLED"] else 0,
                key=f"ap_stat_{v['id']}"
            )
            if new_status != v['status']:
                update_ap_voucher_status(v['id'], new_status, st.session_state.get('user'))
                st.rerun()
                
            render_document_section("ap_voucher", str(v['id']))

def render():
    st.title("💸 Accounts Payable (AP)")
    
    tab1, tab2, tab3 = st.tabs(["AP Register", "Register Invoice", "Approval & Documents"])
    
    with tab1:
        render_ap_list()
        
    with tab2:
        render_ap_create()
        
    with tab3:
        render_ap_workflow()
