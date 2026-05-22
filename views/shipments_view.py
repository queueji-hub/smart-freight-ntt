"""Shipment / Job Control view with Pull Data + Clone features."""
import streamlit as st
from datetime import date
import pandas as pd

from config import JOB_TYPES
from managers.shipment_manager import (
    create_shipment, update_shipment, delete_shipment,
    get_shipment, list_shipments, clone_shipment,
)
from managers.quotation_manager import list_quotations, get_quotation_by_no
from managers.booking_manager import list_bookings, get_booking
from managers.customer_manager import list_customers, get_customer
from managers.auth_manager import can_write


STATUS_OPTIONS = ["Proceed", "Finished", "Closed", "Canceled"]
SIZE_OPTIONS = ["1x20'GP", "1x40'GP", "1x40'HC", "1x40'HQ",
                "1x20'OT", "1x40'OT", "1x20'FR", "Other"]
CARGO_TYPES = ["", "FCL", "LCL", "AIR", "TRUCK"]


def render():
    user = st.session_state.get("user", {})
    role = user.get("role", "")
    can_edit = can_write(role, "shipment")
    
    st.title("📦 Shipment / Job Control")
    st.caption("Job creation · B/L generation · Status workflow")
    
    tabs = ["📋 All Shipments"]
    if can_edit:
        tabs = ["➕ New Shipment", "📋 All Shipments", "✏️ Edit / Update"]
    
    tab_objs = st.tabs(tabs)
    
    if can_edit:
        with tab_objs[0]:
            _create_form(user)
        with tab_objs[1]:
            _list_view()
        with tab_objs[2]:
            _edit_view(can_edit)
    else:
        with tab_objs[0]:
            _list_view()


def _create_form(user):
    st.subheader("Create New Shipment")
    
    # ===== PULL DATA =====
    with st.expander("📥 Pull data from existing Quotation / Booking"):
        col_q, col_b = st.columns(2)
        with col_q:
            quotations = list_quotations()
            q_options = [""] + [q["quotation_no"] for q in quotations[:50]]
            sel_q = st.selectbox("From Quotation", q_options, key="ship_pull_q")
            if sel_q and st.button("Pull from Quotation"):
                q = get_quotation_by_no(sel_q)
                if q:
                    for k, v in q.items():
                        if k.startswith(("ship_pre_", "_")):
                            continue
                    _set_prefilled({
                        "customer_name": q.get("customer_name", ""),
                        "carrier": q.get("carrier", ""),
                        "pol": q.get("pol", ""),
                        "pod": q.get("pod", ""),
                        "commodity": q.get("commodity", ""),
                        "job_type": q.get("job_type", "SE"),
                    })
                    st.success(f"Pulled from {sel_q}")
                    st.rerun()
        with col_b:
            bookings = list_bookings(limit=50)
            b_options = [""] + [b["booking_no"] for b in bookings]
            sel_b = st.selectbox("From Booking", b_options, key="ship_pull_b")
            if sel_b and st.button("Pull from Booking"):
                b = get_booking(sel_b)
                if b:
                    _set_prefilled({
                        "customer_name": b.get("customer_name", ""),
                        "shipper": b.get("shipper", ""),
                        "consignee": b.get("consignee", ""),
                        "notify_party": b.get("notify_party", ""),
                        "carrier": b.get("carrier", ""),
                        "m_vessel": b.get("m_vessel", ""),
                        "feeder": b.get("feeder", ""),
                        "pol": b.get("pol", ""),
                        "por": b.get("por", ""),
                        "pod": b.get("pod", ""),
                        "final_destination": b.get("final_destination", ""),
                        "transhipment_port": b.get("transhipment_port", ""),
                        "etd": b.get("etd", ""),
                        "eta": b.get("eta", ""),
                        "commodity": b.get("commodity", ""),
                        "cargo_type": b.get("cargo_type", ""),
                        "closing_time": b.get("closing_time", ""),
                        "booking_no": sel_b,
                        "job_type": b.get("job_type", "SE"),
                    })
                    st.success(f"Pulled from {sel_b}")
                    st.rerun()
    
    pre = st.session_state.get("ship_prefill", {})
    
    col1, col2, col3 = st.columns(3)
    with col1:
        job_type = st.selectbox("Job Type *",
            options=list(JOB_TYPES.keys()),
            format_func=lambda k: f"{k} — {JOB_TYPES[k]}",
            index=list(JOB_TYPES.keys()).index(pre.get("job_type", "SE"))
                if pre.get("job_type") in JOB_TYPES else 0,
            key="ship_job_type")
        booking_no = st.text_input("Booking No.",
            value=pre.get("booking_no", ""), key="ship_booking")
        customer_name = st.text_input("Customer / Shipper",
            value=pre.get("customer_name", ""), key="ship_customer")
        shipper = st.text_input("Shipper",
            value=pre.get("shipper", ""), key="ship_shipper")
        consignee = st.text_input("Consignee",
            value=pre.get("consignee", ""), key="ship_consignee")
        notify_party = st.text_input("Notify Party",
            value=pre.get("notify_party", ""), key="ship_notify")
        cargo_type = st.selectbox("Cargo Type", CARGO_TYPES,
            index=CARGO_TYPES.index(pre.get("cargo_type", ""))
                if pre.get("cargo_type") in CARGO_TYPES else 0,
            key="ship_cargo")
    with col2:
        carrier = st.text_input("Carrier",
            value=pre.get("carrier", ""), key="ship_carrier")
        m_vessel = st.text_input("M.Vessel",
            value=pre.get("m_vessel", ""), key="ship_mvessel")
        feeder = st.text_input("Feeder",
            value=pre.get("feeder", ""), key="ship_feeder")
        pol = st.text_input("POL (Port of Loading)",
            value=pre.get("pol", ""), key="ship_pol")
        por = st.text_input("POR (Port of Receipt)",
            value=pre.get("por", ""), key="ship_por")
        pod = st.text_input("POD (Port of Discharge)",
            value=pre.get("pod", ""), key="ship_pod")
        final_dest = st.text_input("Final Destination",
            value=pre.get("final_destination", ""), key="ship_final")
        transhipment = st.text_input("Transhipment Port",
            value=pre.get("transhipment_port", ""), key="ship_trans")
    with col3:
        etd = st.date_input("ETD",
            value=_parse_date(pre.get("etd")), key="ship_etd")
        eta = st.date_input("ETA",
            value=_parse_date(pre.get("eta")), key="ship_eta")
        closing_time = st.text_input("Closing Time",
            value=pre.get("closing_time", ""), key="ship_closing")
        container_size = st.selectbox("Container Size", [""] + SIZE_OPTIONS,
            key="ship_size")
        container_no = st.text_input("Container No.", key="ship_cnt_no")
        seal_no = st.text_input("Seal No.", key="ship_seal")
        commodity = st.text_input("Commodity",
            value=pre.get("commodity", ""), key="ship_commodity")
    
    st.markdown("---")
    col_extra, col_remark = st.columns(2)
    with col_extra:
        c1, c2 = st.columns(2)
        with c1:
            pickup = st.date_input("Pick Up Date", value=None, key="ship_pickup")
            stuff = st.date_input("Stuffing Date", value=None, key="ship_stuff")
        with c2:
            ret_date = st.date_input("Return Date", value=None, key="ship_return")
            status = st.selectbox("Status", STATUS_OPTIONS,
                                   index=0, key="ship_status_new")
    with col_remark:
        remark = st.text_area("Remark / Note", height=130, key="ship_remark")
    
    if st.button("🚀 Create Shipment", type="primary", use_container_width=True,
                 key="ship_btn_create"):
        if not customer_name and not booking_no:
            st.error("Please enter at least Customer Name or Booking No.")
        else:
            try:
                data = {
                    "job_type": job_type, "booking_no": booking_no,
                    "customer_name": customer_name,
                    "shipper": shipper, "consignee": consignee,
                    "notify_party": notify_party,
                    "cargo_type": cargo_type, "commodity": commodity,
                    "carrier": carrier, "m_vessel": m_vessel, "feeder": feeder,
                    "pol": pol, "por": por, "pod": pod,
                    "final_destination": final_dest,
                    "transhipment_port": transhipment,
                    "container_no": container_no, "seal_no": seal_no,
                    "container_size": container_size,
                    "etd": etd.isoformat() if etd else None,
                    "eta": eta.isoformat() if eta else None,
                    "pick_up_date": pickup.isoformat() if pickup else None,
                    "stuffing_date": stuff.isoformat() if stuff else None,
                    "return_date": ret_date.isoformat() if ret_date else None,
                    "closing_time": closing_time,
                    "status": status, "remark": remark,
                    "created_by": user.get("username"),
                }
                job_no = create_shipment(data)
                st.success(f"✅ Shipment **{job_no}** created!")
                st.session_state.pop("ship_prefill", None)
                st.balloons()
            except Exception as ex:
                st.error(f"Failed: {ex}")


def _list_view():
    st.subheader("All Shipments")
    
    fc1, fc2, fc3, fc4 = st.columns(4)
    with fc1:
        f_type = st.selectbox("Job Type",
            ["All"] + list(JOB_TYPES.keys()), key="ship_filter_type")
    with fc2:
        f_status = st.selectbox("Status",
            ["All"] + STATUS_OPTIONS, key="ship_filter_status")
    with fc3:
        f_carrier = st.text_input("Carrier contains", key="ship_filter_carrier")
    with fc4:
        st.write("")
        st.button("🔄 Refresh", use_container_width=True, key="ship_refresh")
    
    rows = list_shipments(
        job_type=None if f_type == "All" else f_type,
        status=None if f_status == "All" else f_status,
    )
    if f_carrier:
        rows = [r for r in rows
                if f_carrier.lower() in (r.get("carrier") or "").lower()]
    
    if not rows:
        st.info("No shipments found.")
    else:
        df = pd.DataFrame(rows)
        display_cols = [
            "job_no", "customer_name", "pol", "pod", "carrier",
            "container_size", "etd", "status", "remark",
        ]
        display_cols = [c for c in display_cols if c in df.columns]
        st.dataframe(df[display_cols], use_container_width=True,
                     hide_index=True, height=400)
        
        col_csv, col_bl = st.columns([1, 2])
        with col_csv:
            csv = df[display_cols].to_csv(index=False).encode("utf-8-sig")
            st.download_button("📥 Export CSV", data=csv,
                file_name="shipments.csv", mime="text/csv",
                use_container_width=True, key="ship_export")
        
        # ===== B/L PDF Generation =====
        st.markdown("---")
        st.markdown("##### 📄 Generate Bill of Lading (B/L)")
        bl_options = [r["job_no"] for r in rows]
        sel_bl = st.selectbox("Select shipment for B/L",
            bl_options, key="ship_bl_sel",
            format_func=lambda x: f"{x} — {next((r.get('customer_name','') for r in rows if r['job_no']==x), '')}")
        if st.button("📥 Generate B/L PDF", type="primary", key="ship_bl_btn"):
            try:
                from pdf.bl_pdf import generate_bl_pdf
                ship = get_shipment(sel_bl)
                if ship:
                    pdf_path = generate_bl_pdf(ship)
                    with open(pdf_path, "rb") as f:
                        bl_no = ship.get("bl_no") or ship.get("job_no")
                        st.download_button(
                            f"📥 Download BL_{bl_no}.pdf", f.read(),
                            f"BL_{bl_no}.pdf", "application/pdf",
                            type="primary", key="ship_bl_dl")
                    st.success(f"B/L PDF generated")
            except Exception as ex:
                st.error(f"B/L generation failed: {ex}")


def _edit_view(can_edit):
    st.subheader("Edit / Update Shipment")
    rows = list_shipments()
    if not rows:
        st.info("No shipments to edit.")
        return
    
    options = [f"{r['job_no']} — {r.get('customer_name','')}" for r in rows]
    sel_idx = st.selectbox("Select Shipment", range(len(options)),
        format_func=lambda i: options[i], key="ship_sel_idx")
    sel = rows[sel_idx]
    
    # Action buttons
    col_clone, col_del = st.columns([1, 1])
    with col_clone:
        if st.button("📑 Clone this Job", use_container_width=True):
            new_no = clone_shipment(sel["job_no"])
            if new_no:
                st.success(f"✅ Cloned → {new_no}")
                st.rerun()
    with col_del:
        if st.button("🗑️ Delete", use_container_width=True):
            delete_shipment(sel["job_no"])
            st.success(f"🗑️ Deleted {sel['job_no']}")
            st.rerun()
    
    with st.form("edit_ship_form"):
        c1, c2, c3 = st.columns(3)
        with c1:
            new_status = st.selectbox("Status", STATUS_OPTIONS,
                index=STATUS_OPTIONS.index(sel.get("status","Proceed"))
                    if sel.get("status") in STATUS_OPTIONS else 0)
            new_bl_no = st.text_input("B/L No.",
                value=sel.get("bl_no") or "")
            new_container_no = st.text_input("Container No.",
                value=sel.get("container_no") or "")
            new_seal_no = st.text_input("Seal No.",
                value=sel.get("seal_no") or "")
            new_carrier = st.text_input("Carrier",
                value=sel.get("carrier") or "")
        with c2:
            new_pol = st.text_input("POL", value=sel.get("pol") or "")
            new_pod = st.text_input("POD", value=sel.get("pod") or "")
            new_etd = st.date_input("ETD",
                value=_parse_date(sel.get("etd")))
            new_eta = st.date_input("ETA",
                value=_parse_date(sel.get("eta")))
            new_invoice = st.text_input("Invoice No.",
                value=sel.get("invoice_no") or "")
        with c3:
            new_paid = st.checkbox("Customer Paid",
                value=bool(sel.get("customer_paid", 0)))
            new_dn_no = st.text_input("D/N No.",
                value=sel.get("dn_no") or "")
            new_remark = st.text_area("Remark",
                value=sel.get("remark") or "", height=180)
        
        save = st.form_submit_button("💾 Save Changes", type="primary",
                                      use_container_width=True)
    
    if save:
        update_shipment(sel["job_no"], {
            "status": new_status, "bl_no": new_bl_no,
            "container_no": new_container_no, "seal_no": new_seal_no,
            "carrier": new_carrier, "pol": new_pol, "pod": new_pod,
            "etd": new_etd.isoformat() if new_etd else None,
            "eta": new_eta.isoformat() if new_eta else None,
            "invoice_no": new_invoice,
            "customer_paid": 1 if new_paid else 0,
            "dn_no": new_dn_no, "remark": new_remark,
        })
        st.success(f"✅ Updated {sel['job_no']}")
        st.rerun()


def _set_prefilled(data: dict):
    st.session_state["ship_prefill"] = data


def _parse_date(val):
    if not val:
        return None
    if isinstance(val, str):
        try:
            return date.fromisoformat(val)
        except Exception:
            return None
    return val
