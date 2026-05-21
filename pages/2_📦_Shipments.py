"""Shipment Job Control page (Streamlit native multi-page)."""
import streamlit as st
from datetime import date
import pandas as pd

st.set_page_config(page_title="Shipments - Smart Freight NTT",
                   page_icon="📦", layout="wide",
                   initial_sidebar_state="expanded")

# Clear stale state from other pages
for k in list(st.session_state.keys()):
    if k.startswith(("cc_", "compact_", "create_", "edit_", "all_", "search_qno")):
        del st.session_state[k]

from config import JOB_TYPES
from database.connection import init_database
from managers.shipment_manager import (
    create_shipment, update_shipment, delete_shipment, list_shipments,
)
from utils.nav import setup_sidebar

init_database()
setup_sidebar()
st.title("📦 Shipment Job Control")
st.caption("ใบคุมงาน - บันทึกและติดตามสถานะ shipment ทุกประเภทงาน")

tab_create, tab_list, tab_edit = st.tabs([
    "➕ New Shipment", "📋 All Shipments", "✏️ Edit / Update Status",
])

STATUS_OPTIONS = ["In-Progress", "Finished", "Cancelled", "SOC", "On-Hold"]
SIZE_OPTIONS = ["1x20'GP", "1x40'GP", "1x40'HC", "1x40'HQ",
                "1x20'OT", "1x40'OT", "1x20'FR", "Other"]
FULL_HALF = ["", "FULL", "HALF", "CANCEL"]


# =================== CREATE TAB ===================
with tab_create:
    st.subheader("Create New Shipment")
    col1, col2, col3 = st.columns(3)
    with col1:
        job_type = st.selectbox("Job Type *", options=list(JOB_TYPES.keys()),
            format_func=lambda k: f"{k} — {JOB_TYPES[k]}", key="ship_job_type")
        booking_no = st.text_input("Booking No.", key="ship_booking")
        customer_name = st.text_input("Customer / Shipper", key="ship_customer")
        brand = st.text_input("Brand / Cigarette Brand", key="ship_brand")
        commodity = st.text_input("Commodity", key="ship_commodity")
        combine_commodity = st.text_input("Combine With Commodity?", key="ship_combine")
        full_or_half = st.selectbox("Full / Half", FULL_HALF, key="ship_fullhalf")
    with col2:
        carrier = st.text_input("Carrier (สายการเรือ)", key="ship_carrier")
        pol = st.text_input("POL (Port of Loading)", key="ship_pol")
        pod = st.text_input("POD (Port of Discharge)", key="ship_pod")
        container_size = st.selectbox("Container Size", [""] + SIZE_OPTIONS, key="ship_size")
        container_no = st.text_input("Container No.", key="ship_cnt_no")
        seal_no = st.text_input("Seal No.", key="ship_seal")
        bl_status = st.selectbox("BL", ["", "✓ Issued", "✘ Not yet", "Pending"],
                                  key="ship_bl")
    with col3:
        pick_up_date = st.date_input("Pick Up Date", value=None, key="ship_pickup")
        stuffing_date = st.date_input("Stuffing Date", value=None, key="ship_stuffing")
        return_date = st.date_input("Return Date", value=None, key="ship_return")
        etd = st.date_input("ETD", value=None, key="ship_etd")
        eta = st.date_input("ETA", value=None, key="ship_eta")
        weight_origin = st.text_input("น้ำหนักเขาดิน (Origin)", key="ship_w_origin")
        weight_port = st.text_input("น้ำหนักแหลม (Port)", key="ship_w_port")

    st.markdown("---")
    col4, col5, col6 = st.columns(3)
    with col4:
        invoice_no = st.text_input("Invoice No.", key="ship_invoice")
        dn_type = st.selectbox("D/N Type",
            ["", "TRUCK", "FRT", "FRT+TRUCK", "FRT/TRUCK"], key="ship_dntype")
        dn_no = st.text_input("D/N No.", key="ship_dnno")
    with col5:
        overnight_trucking = st.number_input(
            "Overnight Trucking (count)", min_value=0, value=0, step=1,
            key="ship_overnight")
        customer_paid = st.checkbox("ลูกค้าชำระเงินแล้ว", key="ship_paid")
        status = st.selectbox("Status", STATUS_OPTIONS, index=0, key="ship_status")
    with col6:
        remark = st.text_area("Remark / Note", height=120, key="ship_remark")

    if st.button("🚀 Create Shipment", type="primary", key="ship_btn_create"):
        if not customer_name and not booking_no:
            st.error("Please enter at least Customer Name or Booking No.")
        else:
            try:
                data = {
                    "job_type": job_type, "booking_no": booking_no,
                    "customer_name": customer_name, "brand": brand,
                    "commodity": commodity, "combine_commodity": combine_commodity,
                    "full_or_half": full_or_half,
                    "pick_up_date": pick_up_date.isoformat() if pick_up_date else None,
                    "stuffing_date": stuffing_date.isoformat() if stuffing_date else None,
                    "return_date": return_date.isoformat() if return_date else None,
                    "etd": etd.isoformat() if etd else None,
                    "eta": eta.isoformat() if eta else None,
                    "container_no": container_no, "seal_no": seal_no,
                    "container_size": container_size,
                    "weight_origin": weight_origin, "weight_port": weight_port,
                    "carrier": carrier, "pol": pol, "pod": pod,
                    "bl_status": bl_status,
                    "overnight_trucking": int(overnight_trucking),
                    "status": status, "invoice_no": invoice_no,
                    "customer_paid": 1 if customer_paid else 0,
                    "dn_type": dn_type, "dn_no": dn_no, "remark": remark,
                }
                job_no = create_shipment(data)
                st.success(f"✅ Shipment **{job_no}** created successfully!")
                st.balloons()
            except Exception as ex:
                st.error(f"Failed to create shipment: {ex}")


# =================== LIST TAB ===================
with tab_list:
    st.subheader("All Shipments")
    fcol1, fcol2, fcol3, fcol4 = st.columns(4)
    with fcol1:
        f_type = st.selectbox("Job Type",
            ["All"] + list(JOB_TYPES.keys()), key="ship_filter_type")
    with fcol2:
        f_status = st.selectbox("Status",
            ["All"] + STATUS_OPTIONS, key="ship_filter_status")
    with fcol3:
        f_carrier = st.text_input("Carrier contains", key="ship_filter_carrier")
    with fcol4:
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
            "job_no", "booking_no", "customer_name", "brand",
            "carrier", "pol", "pod", "container_size", "container_no",
            "pick_up_date", "etd", "status", "invoice_no", "remark",
        ]
        display_cols = [c for c in display_cols if c in df.columns]
        st.dataframe(df[display_cols], use_container_width=True,
                     hide_index=True, height=500)
        st.markdown("---")
        col_a, _ = st.columns([1, 5])
        with col_a:
            csv = df[display_cols].to_csv(index=False).encode("utf-8-sig")
            st.download_button("📥 Export CSV", data=csv,
                file_name="shipments.csv", mime="text/csv",
                use_container_width=True, key="ship_export")


# =================== EDIT TAB ===================
with tab_edit:
    st.subheader("Edit / Update Status")
    rows = list_shipments()
    if not rows:
        st.info("No shipments to edit.")
    else:
        job_options = [f"{r['job_no']} — {r.get('customer_name','')}" for r in rows]
        sel_idx = st.selectbox("Select Shipment", range(len(job_options)),
            format_func=lambda i: job_options[i], key="ship_sel_idx")
        selected = rows[sel_idx]

        with st.form("edit_form"):
            ec1, ec2, ec3 = st.columns(3)
            with ec1:
                new_status = st.selectbox("Status", STATUS_OPTIONS,
                    index=STATUS_OPTIONS.index(selected.get("status","In-Progress"))
                        if selected.get("status") in STATUS_OPTIONS else 0)
                new_container_no = st.text_input("Container No.",
                    value=selected.get("container_no") or "")
                new_seal_no = st.text_input("Seal No.",
                    value=selected.get("seal_no") or "")
                new_invoice = st.text_input("Invoice No.",
                    value=selected.get("invoice_no") or "")
            with ec2:
                new_paid = st.checkbox("ลูกค้าชำระแล้ว",
                    value=bool(selected.get("customer_paid", 0)))
                new_dn_no = st.text_input("D/N No.",
                    value=selected.get("dn_no") or "")
                new_carrier = st.text_input("Carrier",
                    value=selected.get("carrier") or "")
                new_pod = st.text_input("POD", value=selected.get("pod") or "")
            with ec3:
                new_etd_raw = selected.get("etd")
                new_etd = st.date_input("ETD",
                    value=date.fromisoformat(new_etd_raw) if new_etd_raw else None)
                new_remark = st.text_area("Remark",
                    value=selected.get("remark") or "", height=120)

            ucol1, ucol2 = st.columns([1, 1])
            with ucol1:
                save = st.form_submit_button("💾 Save Changes",
                    type="primary", use_container_width=True)
            with ucol2:
                delete = st.form_submit_button("🗑️ Delete Shipment",
                    use_container_width=True)

        if save:
            updates = {
                "status": new_status, "container_no": new_container_no,
                "seal_no": new_seal_no, "invoice_no": new_invoice,
                "customer_paid": 1 if new_paid else 0,
                "dn_no": new_dn_no, "carrier": new_carrier, "pod": new_pod,
                "etd": new_etd.isoformat() if new_etd else None,
                "remark": new_remark,
            }
            if update_shipment(selected["job_no"], updates):
                st.success(f"✅ Updated {selected['job_no']}")
                st.rerun()
            else:
                st.error("Update failed")
        if delete:
            if delete_shipment(selected["job_no"]):
                st.success(f"🗑️ Deleted {selected['job_no']}")
                st.rerun()
            else:
                st.error("Delete failed")
