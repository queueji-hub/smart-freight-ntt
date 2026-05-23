"""
Booking Confirmation View
Production-ready CS Booking Module

Features:
- Pull from quotation
- CY / CFS scheduling
- Booking management
- PDF generation
- Status workflow
- Edit / Delete booking
- Clean enterprise UI
"""

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
from managers.customer_manager import list_customers
from managers.quotation_manager import (
    get_quotation_by_no,
    list_quotations,
)


# =========================================================
# CONSTANTS
# =========================================================

CARGO_TYPES = [
    "",
    "FCL",
    "LCL",
    "AIR",
    "TRUCK",
]

STATUS_OPTIONS = [
    "Proceed",
    "Finished",
    "Closed",
    "Canceled",
]


# =========================================================
# MAIN RENDER
# =========================================================

def render():

    user = st.session_state.get("user", {})
    role = user.get("role", "")

    can_edit = can_write(role, "booking")

    st.title("📑 Booking Confirmation")
    st.caption(
        "CS Booking Management · CY/CFS Scheduling"
    )

    if can_edit:

        tabs = st.tabs([
            "➕ Create Booking",
            "📋 Booking List",
            "✏️ Edit Booking",
        ])

        with tabs[0]:
            _create_form(user)

        with tabs[1]:
            _list_view()

        with tabs[2]:
            _edit_view()

    else:

        _list_view()


# =========================================================
# CREATE BOOKING
# =========================================================

def _create_form(user):

    st.subheader("Create New Booking")

    # =====================================================
    # QUOTATION PULL
    # =====================================================

    with st.expander(
        "📥 Pull Data From Quotation"
    ):

        quotations = list_quotations()

        q_options = [""] + [
            q["quotation_no"]
            for q in quotations[:100]
        ]

        selected_q = st.selectbox(
            "Select Quotation",
            q_options,
        )

        if (
            selected_q
            and
            st.button("Pull Quotation")
        ):

            q = get_quotation_by_no(
                selected_q
            )

            if q:

                st.session_state[
                    "booking_prefill"
                ] = {
                    "customer_name":
                        q.get(
                            "customer_name",
                            "",
                        ),

                    "shipper":
                        q.get(
                            "shipper_cnee",
                            "",
                        ),

                    "carrier":
                        q.get(
                            "carrier",
                            "",
                        ),

                    "pol":
                        q.get(
                            "pol",
                            "",
                        ),

                    "pod":
                        q.get(
                            "pod",
                            "",
                        ),

                    "commodity":
                        q.get(
                            "commodity",
                            "",
                        ),

                    "job_type":
                        q.get(
                            "job_type",
                            "SE",
                        ),
                }

                st.success(
                    f"Pulled from {selected_q}"
                )

                st.rerun()

    pre = st.session_state.get(
        "booking_prefill",
        {},
    )

    # =====================================================
    # FORM
    # =====================================================

    c1, c2, c3 = st.columns(3)

    # =====================================================
    # COLUMN 1
    # =====================================================

    with c1:

        job_type = st.selectbox(
            "Job Type *",
            options=list(JOB_TYPES.keys()),
            format_func=lambda x:
            f"{x} — {JOB_TYPES[x]}",
            index=(
                list(JOB_TYPES.keys()).index(
                    pre.get(
                        "job_type",
                        "SE",
                    )
                )
                if pre.get("job_type")
                in JOB_TYPES
                else 0
            ),
        )

        customer_name = st.text_input(
            "Customer Name *",
            value=pre.get(
                "customer_name",
                "",
            ),
        )

        shipper = st.text_input(
            "Shipper",
            value=pre.get(
                "shipper",
                "",
            ),
        )

        consignee = st.text_input(
            "Consignee",
        )

        notify_party = st.text_input(
            "Notify Party",
        )

        cargo_type = st.selectbox(
            "Cargo Type",
            CARGO_TYPES,
        )

        commodity = st.text_input(
            "Commodity",
            value=pre.get(
                "commodity",
                "",
            ),
        )

        quantity = st.text_input(
            "Quantity",
        )

    # =====================================================
    # COLUMN 2
    # =====================================================

    with c2:

        pol = st.text_input(
            "POL",
            value=pre.get(
                "pol",
                "",
            ),
        )

        por = st.text_input(
            "POR",
        )

        pod = st.text_input(
            "POD",
            value=pre.get(
                "pod",
                "",
            ),
        )

        final_destination = st.text_input(
            "Final Destination",
        )

        transhipment_port = st.text_input(
            "Transhipment Port",
        )

        carrier = st.text_input(
            "Carrier",
            value=pre.get(
                "carrier",
                "",
            ),
        )

        m_vessel = st.text_input(
            "Mother Vessel",
        )

        feeder = st.text_input(
            "Feeder Vessel",
        )

        liner = st.text_input(
            "Liner",
        )

    # =====================================================
    # COLUMN 3
    # =====================================================

    with c3:

        etd = st.date_input(
            "ETD",
            value=None,
        )

        eta = st.date_input(
            "ETA",
            value=None,
        )

        cy_date = st.date_input(
            "CY Date",
            value=None,
        )

        cy_place = st.text_input(
            "CY Place",
        )

        cfs_date = st.date_input(
            "CFS Date",
            value=None,
        )

        cfs_place = st.text_input(
            "CFS Place",
        )

        customer_return_date = st.date_input(
            "Customer Return Date",
            value=None,
        )

        return_place = st.text_input(
            "Return Place",
        )

        closing_time = st.text_input(
            "Closing Time",
        )

    # =====================================================
    # REMARK
    # =====================================================

    remark = st.text_area(
        "Remark / Special Instruction",
        height=100,
    )

    # =====================================================
    # SUBMIT
    # =====================================================

    if st.button(
        "🚀 Create Booking",
        type="primary",
        use_container_width=True,
    ):

        if not customer_name:

            st.error(
                "Customer Name is required"
            )

            return

        payload = {
            "job_type": job_type,
            "customer_name": customer_name,
            "shipper": shipper,
            "consignee": consignee,
            "notify_party": notify_party,

            "pol": pol,
            "por": por,
            "pod": pod,

            "final_destination":
                final_destination,

            "transhipment_port":
                transhipment_port,

            "cy_date":
                cy_date.isoformat()
                if cy_date
                else None,

            "cy_place": cy_place,

            "cfs_date":
                cfs_date.isoformat()
                if cfs_date
                else None,

            "cfs_place": cfs_place,

            "customer_return_date":
                customer_return_date.isoformat()
                if customer_return_date
                else None,

            "return_place": return_place,

            "etd":
                etd.isoformat()
                if etd
                else None,

            "eta":
                eta.isoformat()
                if eta
                else None,

            "carrier": carrier,
            "m_vessel": m_vessel,
            "feeder": feeder,
            "liner": liner,

            "closing_time":
                closing_time,

            "cargo_type":
                cargo_type,

            "commodity":
                commodity,

            "quantity":
                quantity,

            "remark":
                remark,

            "created_by":
                user.get(
                    "username",
                    "",
                ),
        }

        try:

            booking_no = create_booking(
                payload
            )

            st.success(
                f"✅ Booking Created : "
                f"{booking_no}"
            )

            st.session_state.pop(
                "booking_prefill",
                None,
            )

            st.balloons()

        except Exception as ex:

            st.error(
                f"Create failed : {ex}"
            )


# =========================================================
# LIST VIEW
# =========================================================

def _list_view():

    st.subheader(
        "Booking Confirmation List"
    )

    f1, f2 = st.columns(2)

    with f1:

        filter_status = st.selectbox(
            "Status",
            ["All"] + STATUS_OPTIONS,
        )

    with f2:

        st.write("")
        st.write("")

        st.button(
            "🔄 Refresh",
            use_container_width=True,
        )

    rows = list_bookings(
        status=None
        if filter_status == "All"
        else filter_status
    )

    if not rows:

        st.info("No booking found")
        return

    df = pd.DataFrame(rows)

    cols = [
        "booking_no",
        "job_type",
        "customer_name",
        "shipper",
        "pol",
        "pod",
        "carrier",
        "etd",
        "eta",
        "status",
    ]

    cols = [
        c
        for c in cols
        if c in df.columns
    ]

    st.dataframe(
        df[cols],
        use_container_width=True,
        hide_index=True,
        height=450,
    )

    # =====================================================
    # EXPORT CSV
    # =====================================================

    csv = df[cols].to_csv(
        index=False
    ).encode("utf-8-sig")

    st.download_button(
        "📥 Export CSV",
        data=csv,
        file_name="booking_confirmations.csv",
        mime="text/csv",
    )

    # =====================================================
    # PDF
    # =====================================================

    st.divider()

    st.subheader(
        "Generate Booking PDF"
    )

    options = [
        (
            r["booking_no"],
            f"{r['booking_no']} — "
            f"{r.get('customer_name', '')}"
        )
        for r in rows
    ]

    selected = st.selectbox(
        "Select Booking",
        [o[0] for o in options],
        format_func=lambda x:
        next(
            o[1]
            for o in options
            if o[0] == x
        ),
    )

    if st.button(
        "📥 Generate PDF",
        type="primary",
    ):

        try:

            from pdf.booking_pdf import (
                generate_booking_pdf
            )

            booking = get_booking(
                selected
            )

            if booking:

                pdf_path = generate_booking_pdf(
                    booking
                )

                with open(
                    pdf_path,
                    "rb",
                ) as f:

                    st.download_button(
                        f"📥 Download BC_{selected}.pdf",
                        f.read(),
                        file_name=f"BC_{selected}.pdf",
                        mime="application/pdf",
                    )

                st.success(
                    f"PDF generated : "
                    f"{selected}"
                )

        except Exception as ex:

            st.error(
                f"PDF generation failed : "
                f"{ex}"
            )


# =========================================================
# EDIT VIEW
# =========================================================

def _edit_view():

    st.subheader("Edit Booking")

    rows = list_bookings()

    if not rows:

        st.info("No booking found")
        return

    options = [
        (
            r["booking_no"],
            f"{r['booking_no']} — "
            f"{r.get('customer_name', '')}"
        )
        for r in rows
    ]

    idx = st.selectbox(
        "Select Booking",
        range(len(options)),
        format_func=lambda i:
        options[i][1],
    )

    selected = rows[idx]

    with st.form(
        "edit_booking_form"
    ):

        c1, c2 = st.columns(2)

        with c1:

            status = st.selectbox(
                "Status",
                STATUS_OPTIONS,
                index=(
                    STATUS_OPTIONS.index(
                        selected.get(
                            "status",
                            "Proceed",
                        )
                    )
                    if selected.get("status")
                    in STATUS_OPTIONS
                    else 0
                ),
            )

            carrier = st.text_input(
                "Carrier",
                value=selected.get(
                    "carrier",
                    "",
                ),
            )

            etd = st.date_input(
                "ETD",
                value=_parse_date(
                    selected.get("etd")
                ),
            )

            eta = st.date_input(
                "ETA",
                value=_parse_date(
                    selected.get("eta")
                ),
            )

        with c2:

            remark = st.text_area(
                "Remark",
                value=selected.get(
                    "remark",
                    "",
                ),
                height=180,
            )

        save_col, del_col = st.columns(2)

        with save_col:

            save = st.form_submit_button(
                "💾 Save",
                type="primary",
                use_container_width=True,
            )

        with del_col:

            delete = st.form_submit_button(
                "🗑 Delete",
                use_container_width=True,
            )

    # SAVE
    if save:

        update_booking(
            selected["booking_no"],
            {
                "status": status,
                "carrier": carrier,
                "etd":
                    etd.isoformat()
                    if etd
                    else None,

                "eta":
                    eta.isoformat()
                    if eta
                    else None,

                "remark":
                    remark,
            },
        )

        st.success(
            f"✅ Updated : "
            f"{selected['booking_no']}"
        )

        st.rerun()

    # DELETE
    if delete:

        delete_booking(
            selected["booking_no"]
        )

        st.success(
            f"🗑 Deleted : "
            f"{selected['booking_no']}"
        )

        st.rerun()


# =========================================================
# HELPERS
# =========================================================

def _parse_date(value):

    if not value:
        return None

    if isinstance(value, str):

        try:
            return date.fromisoformat(
                value
            )

        except Exception:
            return None

    return value