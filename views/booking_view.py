"""Booking Confirmation view - CS-driven module."""
import streamlit as st
from datetime import date
import pandas as pd

from config import JOB_TYPES
from managers.booking_manager import (
    create_booking, get_booking, list_bookings, update_booking, delete_booking,
)
from managers.quotation_manager import list_quotations, get_quotation_by_no
from managers.customer_manager import list_customers
from managers.auth_manager import can_write


CARGO_TYPES = ["", "FCL", "LCL", "AIR", "TRUCK"]
STATUS_OPTIONS = ["Proceed", "Finished", "Closed", "Canceled"]


def render():
    user = st.session_state.get("user", {})
    role = user.get("role", "")
    can_edit = can_write(role, "booking")
    
    st.title("📑 Booking Confirmation")
    st.caption("Create booking confirmations · Pull from quotation · CY/CFS scheduling")
    
    tabs = ["📋 All Bookings"]
    if can_edit:
        tabs = ["➕ New Booking", "📋 All Bookings", "✏️ Edit Booking"]
    
    tab_objs = st.tabs(tabs)
    
    if can_edit:
        with tab_objs[0]:
            _create_form(user)
        with tab_objs[1]:
            _list_view()
        with tab_objs[2]:
            _edit_view()
    else:
        with tab_objs[0]:
            _list_view()


def _create_form(user):
    st.subheader("Create New Booking Confirmation")
    
    # Pull from quotation
    with st.expander("📥 Pull from existing Quotation"):
        quotations = list_quotations()
        q_options = [""] + [q["quotation_no"] for q in quotations[:50]]
        sel_q = st.selectbox("Select quotation", q_options, key="bk_pull_q")
        if sel_q and st.button("Pull data"):
            q = get_quotation_by_no(sel_q)
            if q:
                st.session_state["bk_prefill"] = {
                    "customer_name": q.get("customer_name", ""),
                    "shipper": q.get("shipper_cnee", ""),
                    "carrier": q.get("carrier", ""),
                    "pol": q.get("pol", ""),
                    "pod": q.get("pod", ""),
                    "commodity": q.get("commodity", ""),
                    "job_type": q.get("job_type", "SE"),
                }
                st.success(f"Pulled from {sel_q}")
                st.rerun()
    
    pre = st.session_state.get("bk_prefill", {})
    
    col1, col2, col3 = st.columns(3)
    with col1:
        job_type = st.selectbox("Job Type *", options=list(JOB_TYPES.keys()),
            format_func=lambda k: f"{k} — {JOB_TYPES[k]}",
            index=list(JOB_TYPES.keys()).index(pre.get("job_type", "SE"))
                if pre.get("job_type") in JOB_TYPES else 0,
            key="bk_jt")
        customer_name = st.text_input("Customer Name *",
            value=pre.get("customer_name", ""), key="bk_cust")
        shipper = st.text_input("Shipper",
            value=pre.get("shipper", ""), key="bk_shipper")
        consignee = st.text_input("Consignee", key="bk_cnee")
        notify_party = st.text_input("Notify Party", key="bk_notify")
        cargo_type = st.selectbox("Cargo Type", CARGO_TYPES, key="bk_cargo")
        commodity = st.text_input("Commodity",
            value=pre.get("commodity", ""), key="bk_commodity")
        quantity = st.text_input("Quantity", key="bk_qty")
    with col2:
        pol = st.text_input("POL (Port of Loading)",
            value=pre.get("pol", ""), key="bk_pol")
        por = st.text_input("POR (Port of Receipt)", key="bk_por")
        pod = st.text_input("POD (Port of Discharge)",
            value=pre.get("pod", ""), key="bk_pod")
        final_dest = st.text_input("Final Destination", key="bk_final")
        transhipment = st.text_input("Transhipment Port", key="bk_trans")
        carrier = st.text_input("Carrier",
            value=pre.get("carrier", ""), key="bk_carrier")
        m_vessel = st.text_input("M.Vessel", key="bk_mv")
        feeder = st.text_input("Feeder", key="bk_feeder")
        liner = st.text_input("Liner", key="bk_liner")
    with col3:
        etd = st.date_input("ETD", value=None, key="bk_etd")
        eta = st.date_input("ETA", value=None, key="bk_eta")
        cy_date = st.date_input("CY Date", value=None, key="bk_cydate")
        cy_place = st.text_input("CY Place", key="bk_cyplace")
        cfs_date = st.date_input("CFS Date", value=None, key="bk_cfsdate")
        cfs_place = st.text_input("CFS Place", key="bk_cfsplace")
        cust_return = st.date_input("Customer Return Date",
                                       value=None, key="bk_ret_date")
        return_place = st.text_input("Return Place", key="bk_retplace")
        closing_time = st.text_input("Closing Time", key="bk_closing")
    
    remark = st.text_area("Remark / Special Instructions",
                           height=80, key="bk_remark")
    
    if st.button("🚀 Create Booking", type="primary", use_container_width=True,
                 key="bk_btn_create"):
        if not customer_name:
            st.error("Customer Name is required")
        else:
            try:
                booking_no = create_booking({
                    "job_type": job_type, "customer_name": customer_name,
                    "shipper": shipper, "consignee": consignee,
                    "notify_party": notify_party,
                    "pol": pol, "por": por, "pod": pod,
                    "final_destination": final_dest,
                    "transhipment_port": transhipment,
                    "cy_date": cy_date.isoformat() if cy_date else None,
                    "cy_place": cy_place,
                    "cfs_date": cfs_date.isoformat() if cfs_date else None,
                    "cfs_place": cfs_place,
                    "customer_return_date": cust_return.isoformat() if cust_return else None,
                    "return_place": return_place,
                    "etd": etd.isoformat() if etd else None,
                    "eta": eta.isoformat() if eta else None,
                    "carrier": carrier, "m_vessel": m_vessel, "feeder": feeder,
                    "liner": liner, "closing_time": closing_time,
                    "cargo_type": cargo_type, "commodity": commodity,
                    "quantity": quantity, "remark": remark,
                    "created_by": user.get("username"),
                })
                st.success(f"✅ Booking **{booking_no}** created!")
                st.session_state.pop("bk_prefill", None)
                st.balloons()
            except Exception as ex:
                st.error(f"Failed: {ex}")


def _list_view():
    st.subheader("All Booking Confirmations")
    
    fc1, fc2 = st.columns(2)
    with fc1:
        f_status = st.selectbox("Status", ["All"] + STATUS_OPTIONS, key="bk_fs")
    with fc2:
        st.write(""); st.write("")
        st.button("🔄 Refresh", key="bk_refresh", use_container_width=True)
    
    rows = list_bookings(status=None if f_status == "All" else f_status)
    if not rows:
        st.info("No bookings found.")
        return
    
    df = pd.DataFrame(rows)
    display_cols = ["booking_no", "job_type", "customer_name", "shipper",
                    "pol", "pod", "carrier", "etd", "eta", "status"]
    display_cols = [c for c in display_cols if c in df.columns]
    st.dataframe(df[display_cols], use_container_width=True,
                 hide_index=True, height=500)


def _edit_view():
    st.subheader("Edit Booking")
    rows = list_bookings()
    if not rows:
        st.info("No bookings to edit.")
        return
    
    options = [f"{r['booking_no']} — {r.get('customer_name','')}" for r in rows]
    sel_idx = st.selectbox("Select", range(len(options)),
        format_func=lambda i: options[i], key="bk_edit_sel")
    sel = rows[sel_idx]
    
    with st.form("edit_bk_form"):
        col1, col2 = st.columns(2)
        with col1:
            new_status = st.selectbox("Status", STATUS_OPTIONS,
                index=STATUS_OPTIONS.index(sel.get("status","Proceed"))
                    if sel.get("status") in STATUS_OPTIONS else 0)
            new_carrier = st.text_input("Carrier",
                value=sel.get("carrier") or "")
            new_etd = st.date_input("ETD", value=_parse_date(sel.get("etd")))
            new_eta = st.date_input("ETA", value=_parse_date(sel.get("eta")))
        with col2:
            new_remark = st.text_area("Remark",
                value=sel.get("remark") or "", height=180)
        
        col_save, col_del = st.columns([1, 1])
        with col_save:
            save = st.form_submit_button("💾 Save", type="primary",
                use_container_width=True)
        with col_del:
            delete = st.form_submit_button("🗑️ Delete", use_container_width=True)
    
    if save:
        update_booking(sel["booking_no"], {
            "status": new_status, "carrier": new_carrier,
            "etd": new_etd.isoformat() if new_etd else None,
            "eta": new_eta.isoformat() if new_eta else None,
            "remark": new_remark,
        })
        st.success(f"✅ Updated {sel['booking_no']}")
        st.rerun()
    if delete:
        delete_booking(sel["booking_no"])
        st.success(f"🗑️ Deleted")
        st.rerun()


def _parse_date(val):
    if not val:
        return None
    if isinstance(val, str):
        try:
            return date.fromisoformat(val)
        except Exception:
            return None
    return val
