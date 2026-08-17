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
    st.subheader("Register Vendor Invoice / Disbursement (เบิกจ่ายสายเรือ / Vendor)")
    
    from managers.shipment_manager import list_shipments
    from managers.profit_manager import get_cost_lines
    
    vendors = get_vendors()
    if not vendors:
        st.error("Please create a vendor first.")
        return
        
    v_opts = {f"{v['vendor_code']} - {v['legal_name']}": v['id'] for v in vendors}
    jobs = list_shipments(limit=100) or []
    job_choices = ["— None (General Expense) —"] + [j["job_no"] for j in jobs]
    
    st.markdown("##### 📥 Pull Verified Cost from Job (ดึงยอดต้นทุนจากฝ่ายปฏิบัติการ)")
    sel_job = st.selectbox("Select Job No. to pull costs", job_choices, key="ap_pull_job_select")
    
    prefill_vendor_id = None
    prefill_amount = 0.0
    prefill_currency = "THB"
    prefill_desc = ""
    
    if sel_job and not sel_job.startswith("—"):
        job_rec = next((j for j in jobs if j["job_no"] == sel_job), None)
        if job_rec:
            c_lines = get_cost_lines(job_rec["id"], cost_type="AP")
            if c_lines:
                st.write(f"**Verified Cost Lines for {sel_job}:**")
                c_opts = {f"#{c['id']} - {c.get('category')}: {c.get('description')} ({c.get('supplier','—')}) | {float(c.get('amount',0)):,.2f} {c.get('currency','THB')}": c for c in c_lines}
                chosen_cost = st.selectbox("Choose cost line to create payment voucher", list(c_opts.keys()), key="ap_chosen_cost_line")
                if chosen_cost:
                    c_data = c_opts[chosen_cost]
                    prefill_amount = float(c_data.get("amount") or 0)
                    prefill_currency = c_data.get("currency") or "THB"
                    prefill_desc = c_data.get("description") or ""
                    # try to match vendor
                    sup_name = str(c_data.get("supplier") or "").lower()
                    for v_label, v_id in v_opts.items():
                        if sup_name and (sup_name in v_label.lower()):
                            prefill_vendor_id = v_id
                            break
            else:
                st.info(f"No cost lines recorded for Job {sel_job}. Operation has not added costs yet.")

    with st.form("new_ap_form"):
        col1, col2 = st.columns(2)
        default_v_idx = 0
        if prefill_vendor_id:
            for idx, vid in enumerate(v_opts.values()):
                if vid == prefill_vendor_id:
                    default_v_idx = idx
                    break
        v_sel = col1.selectbox("Select Vendor*", list(v_opts.keys()), index=default_v_idx)
        job_no = col2.text_input("Job / Shipment No.", value="" if sel_job.startswith("—") else sel_job)
        
        c1, c2, c3 = st.columns(3)
        inv_no = c1.text_input("Vendor Invoice / Ref No.*", value=f"V-{sel_job}" if not sel_job.startswith("—") else "")
        inv_date = c2.date_input("Invoice Date*")
        due_date = c3.date_input("Due Date")
        
        fc1, fc2, fc3, fc4 = st.columns(4)
        curr = fc1.text_input("Currency", value=prefill_currency)
        subtotal = fc2.number_input("Subtotal", min_value=0.0, format="%.2f", value=prefill_amount)
        tax = fc3.number_input("Tax / VAT", min_value=0.0, format="%.2f", value=0.0)
        total = fc4.number_input("Total Amount", min_value=0.0, format="%.2f", value=subtotal+tax)
        
        wht_col1, wht_col2 = st.columns(2)
        wht_type = wht_col1.selectbox("Withholding Tax (หัก ณ ที่จ่าย WHT)", ["None (0%)", "Transport (1%) - ค่าขนส่ง", "Service (3%) - ค่าบริการ/จัดการ", "Rent (5%) - ค่าเช่า"], index=0)
        wht_rate = 0.01 if "1%" in wht_type else (0.03 if "3%" in wht_type else (0.05 if "5%" in wht_type else 0.0))
        wht_amt = subtotal * wht_rate
        net_payable = total - wht_amt
        wht_col2.metric("Net Payable Amount (ยอดจ่ายสุทธิหลังหักภาษี)", f"{net_payable:,.2f} {curr}")
        
        submit = st.form_submit_button("Register AP Payment Voucher", type="primary", use_container_width=True)
        if submit:
            if not inv_no:
                st.error("Invoice No is required.")
                return
            
            try:
                ap_id = create_ap_voucher({
                    "vendor_id": v_opts[v_sel],
                    "job_no": job_no.strip() or None,
                    "invoice_no": inv_no.strip(),
                    "invoice_date": inv_date.strftime("%Y-%m-%d"),
                    "due_date": due_date.strftime("%Y-%m-%d"),
                    "currency": curr.strip(),
                    "subtotal": subtotal,
                    "tax": tax,
                    "total": total
                }, st.session_state.get('user'))
                st.success(f"AP Payment Voucher for {inv_no} created successfully! (ID: {ap_id})")
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
