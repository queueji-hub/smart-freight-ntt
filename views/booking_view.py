from datetime import date
import pandas as pd
import streamlit as st

from config import JOB_TYPES
from managers.auth_manager import can_write
from managers.booking_manager import (
    create_booking,
    delete_booking,
    get_booking,
    list_bookings,
    update_booking,
)
from managers.quotation_manager import (
    get_quotation_by_no,
    list_quotations
)

from core.audit import log_action
from pdf.booking_pdf import generate_booking_pdf


# =========================================================
# CONSTANTS
# =========================================================

CARGO_TYPES = ["", "FCL", "LCL", "AIR", "TRUCK"]
STATUS_OPTIONS = ["Proceed", "Finished", "Closed", "Canceled"]


# =========================================================
# SAFE CACHE (NO STALE CRITICAL DATA)
# =========================================================

def get_bookings(status=None):
    return list_bookings(status=status)


# =========================================================
# DATE PARSER
# =========================================================

def _parse_date(value):
    if not value:
        return None
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value)[:10])
    except:
        return None


# =========================================================
# MAIN RENDER
# =========================================================

def render():

    user = st.session_state.get("user", {})
    role = user.get("role", "")
    tenant_id = user.get("tenant_id", "demo")

    can_edit = can_write(role, "booking")

    st.title("📑 Booking System (SaaS Production)")
    st.caption("Quotation → Booking → Job Pipeline")

    if can_edit:
        tabs = st.tabs(["➕ Create", "📋 List", "✏️ Edit"])

        with tabs[0]:
            _create_form(user, tenant_id)

        with tabs[1]:
            _list_view(tenant_id)

        with tabs[2]:
            _edit_view(tenant_id)

    else:
        _list_view(tenant_id)


# =========================================================
# CREATE FORM (FROM QUOTATION PIPELINE READY)
# =========================================================

def _create_form(user, tenant_id):

    st.subheader("Create Booking")

    # =========================
    # QUOTATION PULL (SAFE)
    # =========================
    with st.expander("📥 Pull From Quotation"):

        quotations = list_quotations(tenant_id)
        q_options = [""] + [q["quotation_no"] for q in quotations]

        selected_q = st.selectbox(
            "Select Quotation",
            q_options,
            key="quotation_selector"
        )

        if selected_q and st.button("Pull Data", key="pull_q_btn"):

            q = get_quotation_by_no(selected_q)

            if q:
                st.session_state["booking_prefill"] = q
                st.success(f"Loaded: {selected_q}")
                st.rerun()

    pre = st.session_state.get("booking_prefill", {})

    # =========================
    # FORM INPUTS
    # =========================
    c1, c2, c3 = st.columns(3)

    with c1:
        job_type = st.selectbox("Job Type", list(JOB_TYPES.keys()), key="job_type")
        customer_name = st.text_input("Customer", value=pre.get("customer_name", ""), key="cust")
        shipper = st.text_input("Shipper", value=pre.get("shipper_cnee", ""), key="shipper")

    with c2:
        pol = st.text_input("POL", value=pre.get("pol", ""), key="pol")
        pod = st.text_input("POD", value=pre.get("pod", ""), key="pod")
        carrier = st.text_input("Carrier", value=pre.get("carrier", ""), key="carrier")

    with c3:
        etd = st.date_input("ETD", key="etd")
        eta = st.date_input("ETA", key="eta")

    remark = st.text_area("Remark", key="remark")

    # =========================
    # CREATE BOOKING
    # =========================
    if st.button("🚀 Create Booking", type="primary", key="create_booking_btn"):

        if not customer_name:
            st.error("Customer required")
            return

        if etd and eta and eta < etd:
            st.warning("ETA < ETD")
            return

        payload = {
            "job_type": job_type,
            "customer_name": customer_name,
            "shipper": shipper,
            "pol": pol,
            "pod": pod,
            "carrier": carrier,
            "etd": etd.isoformat() if etd else None,
            "eta": eta.isoformat() if eta else None,
            "remark": remark,
            "created_by": user.get("username")
        }

        booking_no = create_booking(payload)

        log_action(
            user.get("id"),
            tenant_id,
            "booking",
            booking_no,
            "CREATE"
        )

        st.success(f"Created: {booking_no}")
        st.session_state.pop("booking_prefill", None)
        st.balloons()


# =========================================================
# LIST VIEW (SIMPLE + SCALABLE)
# =========================================================

def _list_view(tenant_id):

    st.subheader("Booking List")

    status_filter = st.selectbox(
        "Status",
        ["All"] + STATUS_OPTIONS,
        key="status_filter"
    )

    rows = get_bookings(None if status_filter == "All" else status_filter)

    if not rows:
        st.info("No data")
        return

    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, hide_index=True)

    # =========================
    # PDF EXPORT
    # =========================
    st.divider()

    booking_no = st.selectbox(
        "Generate PDF",
        df["booking_no"].tolist(),
        key="pdf_select"
    )

    if st.button("📥 Generate PDF", key="pdf_btn"):

        booking = get_booking(booking_no)

        pdf_file = generate_booking_pdf(booking)

        with open(pdf_file, "rb") as f:
            st.download_button(
                "Download PDF",
                f,
                file_name=f"BC_{booking_no}.pdf",
                mime="application/pdf",
                key="download_pdf"
            )


# =========================================================
# EDIT VIEW (SAFE UI FLOW)
# =========================================================

def _edit_view(tenant_id):

    st.subheader("Edit Booking")

    rows = get_bookings()

    if not rows:
        st.info("No booking")
        return

    selected = st.selectbox(
        "Select Booking",
        rows,
        format_func=lambda x: x["booking_no"],
        key="edit_select"
    )

    with st.form("edit_form"):

        status = st.selectbox(
            "Status",
            STATUS_OPTIONS,
            index=STATUS_OPTIONS.index(selected.get("status", "Proceed"))
        )

        remark = st.text_area(
            "Remark",
            value=selected.get("remark", "")
        )

        save = st.form_submit_button("Save")
        delete = st.form_submit_button("Delete")

        if save:
            update_booking(
                selected["booking_no"],
                {
                    "status": status,
                    "remark": remark
                }
            )
            st.success("Updated")
            st.rerun()

        if delete:
            delete_booking(selected["booking_no"])
            st.warning("Deleted")
            st.rerun()