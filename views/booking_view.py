"""
Booking Confirmation View
Production-ready CS Booking Module
"""

from datetime import date, datetime
import pandas as pd
import streamlit as st

from config import JOB_TYPES
from managers.auth_manager import can_write
from managers.booking_manager import (
    create_booking, delete_booking, get_booking, list_bookings, update_booking,
)
from managers.quotation_manager import get_quotation_by_no, list_quotations

# Constants
CARGO_TYPES = ["", "FCL", "LCL", "AIR", "TRUCK"]
STATUS_OPTIONS = ["Proceed", "Finished", "Closed", "Canceled"]

# Cache Manager
@st.cache_data(ttl=30)
def cached_list_bookings(status=None):
    return list_bookings(status=status)

def _parse_date(value):
    if not value: return None
    if isinstance(value, date): return value
    if isinstance(value, str):
        try: return date.fromisoformat(value[:10])
        except: return None
    return None

# =========================================================
# MAIN RENDER
# =========================================================
def render():
    user = st.session_state.get("user", {})
    role = user.get("role", "")
    can_edit = can_write(role, "booking")

    st.title("📑 Booking Confirmation")
    st.caption("CS Booking Management · CY/CFS Scheduling")

    if can_edit:
        tabs = st.tabs(["➕ Create", "📋 List", "✏️ Edit"])
        with tabs[0]: _create_form(user)
        with tabs[1]: _list_view()
        with tabs[2]: _edit_view()
    else:
        _list_view()

# =========================================================
# CREATE FORM
# =========================================================
def _create_form(user):
    st.subheader("Create New Booking")
    
    with st.expander("📥 Pull Data From Quotation"):
        quotations = list_quotations()
        q_options = [""] + [q["quotation_no"] for q in quotations[:100]]
        selected_q = st.selectbox("Select Quotation", q_options)
        if selected_q and st.button("Pull Data"):
            q = get_quotation_by_no(selected_q)
            if q:
                st.session_state["booking_prefill"] = q
                st.success(f"Pulled: {selected_q}"); st.rerun()

    pre = st.session_state.get("booking_prefill", {})
    c1, c2, c3 = st.columns(3)

    with c1:
        job_type = st.selectbox("Job Type *", list(JOB_TYPES.keys()))
        customer_name = st.text_input("Customer Name *", value=pre.get("customer_name", ""))
        shipper = st.text_input("Shipper", value=pre.get("shipper_cnee", ""))
        cargo_type = st.selectbox("Cargo Type", CARGO_TYPES)
        commodity = st.text_input("Commodity", value=pre.get("commodity", ""))

    with c2:
        pol = st.text_input("POL", value=pre.get("pol", ""))
        pod = st.text_input("POD", value=pre.get("pod", ""))
        carrier = st.text_input("Carrier", value=pre.get("carrier", ""))

    with c3:
        etd = st.date_input("ETD", value=None)
        eta = st.date_input("ETA", value=None)
        
    remark = st.text_area("Remark")

    if st.button("🚀 Create Booking", type="primary", use_container_width=True):
        if not customer_name: st.error("Customer Name is required"); return
        if eta and etd and eta < etd: st.warning("ETA is earlier than ETD!"); return
        
        payload = {
            "job_type": job_type, "customer_name": customer_name, "shipper": shipper,
            "pol": pol, "pod": pod, "carrier": carrier,
            "etd": etd.isoformat() if etd else None,
            "eta": eta.isoformat() if eta else None,
            "remark": remark, "created_by": user.get("username", "")
        }
        try:
            booking_no = create_booking(payload)
            st.success(f"✅ Created: {booking_no}")
            st.session_state.pop("booking_prefill", None); st.balloons()
        except Exception as e: st.error(f"Error: {e}")

# =========================================================
# LIST VIEW
# =========================================================
def _list_view():
    st.subheader("Booking Confirmation List")
    status_filter = st.selectbox("Filter Status", ["All"] + STATUS_OPTIONS)
    rows = cached_list_bookings(None if status_filter == "All" else status_filter)
    
    if not rows: st.info("No bookings found"); return
    
    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, hide_index=True)
    
    # PDF Generation area
    st.divider()
    selected_doc = st.selectbox("Select for PDF", df["booking_no"].tolist())
    if st.button("📥 Generate PDF"):
        from pdf.booking_pdf import generate_booking_pdf
        booking = get_booking(selected_doc)
        pdf_path = generate_booking_pdf(booking)
        with open(pdf_path, "rb") as f:
            st.download_button("Download PDF", f, f"BC_{selected_doc}.pdf", "application/pdf")

# =========================================================
# EDIT VIEW
# =========================================================
def _edit_view():
    st.subheader("Edit/Delete Booking")
    rows = cached_list_bookings()
    if not rows: st.info("No booking found"); return
    
    selected_idx = st.selectbox("Select Booking", range(len(rows)), format_func=lambda i: rows[i]["booking_no"])
    selected = rows[selected_idx]
    
    with st.form("edit_form"):
        status = st.selectbox("Status", STATUS_OPTIONS, index=STATUS_OPTIONS.index(selected.get("status", "Proceed")))
        remark = st.text_area("Remark", value=selected.get("remark", ""))
        
        col_s, col_d = st.columns(2)
        save = col_s.form_submit_button("💾 Save Changes", type="primary")
        delete = col_d.form_submit_button("🗑 Delete Booking")
        
        if save:
            update_booking(selected["booking_no"], {"status": status, "remark": remark})
            st.success("Updated!"); st.rerun()
        if delete:
            # ใช้ st.session_state เพื่อทำ Confirmation flow
            st.warning("Are you sure? This action cannot be undone.")
            if st.button("Confirm Delete", key="del_confirm"):
                delete_booking(selected["booking_no"])
                st.rerun()