"""
Booking Control Center & Operational Dispatch Workspace
Phase B Hardened — Full Ledger, Multi-Tab Workspace, Revision Control & Historical PDF Generator
"""

import os
from datetime import date, datetime
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
    can_transition_booking_status,
    convert_booking_to_job,
    create_booking_revision,
    get_revision_history,
    get_booking_revision,
)
from managers.quotation_manager import (
    get_quotation_by_no,
    list_quotations,
)

from core.audit import log_action
from pdf.booking_pdf import generate_booking_pdf

# =========================================================
# GLOBAL CONSTANTS & HELPERS
# =========================================================
CARGO_TYPES = ["", "FCL", "LCL", "AIR", "TRUCK"]
STATUS_OPTIONS = ["DRAFT", "SUBMITTED", "CONFIRMED", "CONVERTED TO JOB", "CANCELLED"]


def _parse_date(value):
    """Safely converts dynamic input formats to concrete python date objects."""
    if not value:
        return None
    if isinstance(value, date):
        return value
    if isinstance(value, datetime):
        return value.date()
    try:
        return date.fromisoformat(str(value)[:10])
    except (ValueError, TypeError):
        return None


def _s(val, default="") -> str:
    if val is None:
        return default
    v = str(val).strip()
    return default if not v or v.lower() in ("none", "nan", "nat") else v


# =========================================================
# MAIN PRESENTATION ROUTER
# =========================================================
def render():
    user = st.session_state.get("user", {})
    role = str(user.get("role", "")).lower()
    tenant_id = user.get("tenant_id", "default")
    can_edit = can_write(role, "booking")

    st.markdown(
        "<p style='color: #38BDF8; font-weight: 700; font-size: 13px; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 2px;'>Operational Pipeline Control</p>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<h2 style='margin-top: 0px; font-weight: 800; color:#F8FAFC;'>📑 Freight Booking Control Center</h2>",
        unsafe_allow_html=True,
    )
    st.caption(
        "Commercial Quotation ➡️ Active Booking Manifest (Ledger / Revisions) ➡️ Operational Job Conversion."
    )

    if can_edit:
        tabs = st.tabs([
            "📋 Booking Ledger",
            "✏️ Booking Workspace & Revisions",
            "➕ Construct New Booking",
        ])

        with tabs[0]:
            _ledger_view(tenant_id, can_edit, user)

        with tabs[1]:
            _workspace_view(tenant_id, can_edit, user)

        with tabs[2]:
            _create_form(user, tenant_id)
    else:
        # Read-Only Enforcement Mode
        tabs = st.tabs(["📋 Booking Ledger", "👁️ View Workspace"])
        with tabs[0]:
            _ledger_view(tenant_id, False, user)
        with tabs[1]:
            _workspace_view(tenant_id, False, user)


# =========================================================
# COMPONENT 1: BOOKING LEDGER (LANDING EXPERIENCE)
# =========================================================
def _ledger_view(tenant_id, can_edit, user):
    st.markdown(
        "<h4 style='font-size:16px; color:#F1F5F9; font-weight:700;'>📋 Operational Booking Manifest Ledger</h4>",
        unsafe_allow_html=True,
    )

    # --- FILTERS ROW ---
    c_f1, c_f2, c_f3, c_f4 = st.columns(4)
    with c_f1:
        status_filter = st.selectbox(
            "Status Filter",
            options=["All Statuses"] + STATUS_OPTIONS,
            key="bk_ledger_status_filter",
        )
    with c_f2:
        job_type_filter = st.selectbox(
            "Job Type Filter",
            options=["All Types"] + list(JOB_TYPES.keys()),
            key="bk_ledger_jobtype_filter",
        )
    with c_f3:
        search_query = st.text_input(
            "Search (Booking / Job / Customer / POL / POD / Vessel)",
            placeholder="e.g. BK2608, SE2608, Customer",
            key="bk_ledger_search",
        )
    with c_f4:
        st.write("")
        st.write("")
        if st.button("🔄 Refresh Data", use_container_width=True, key="bk_ledger_refresh"):
            st.rerun()

    with st.expander("📅 Advanced Date Filters", expanded=False):
        d_f1, d_f2, d_f3, d_f4 = st.columns(4)
        etd_start = d_f1.date_input("ETD From", value=None, key="bk_ledger_etd_start")
        etd_end = d_f2.date_input("ETD To", value=None, key="bk_ledger_etd_end")
        eta_start = d_f3.date_input("ETA From", value=None, key="bk_ledger_eta_start")
        eta_end = d_f4.date_input("ETA To", value=None, key="bk_ledger_eta_end")

    if etd_start and etd_end and etd_start > etd_end:
        st.error("⚠️ ETD From cannot be after ETD To")
        return
        
    if eta_start and eta_end and eta_start > eta_end:
        st.error("⚠️ ETA From cannot be after ETA To")
        return

    # Load data via manager
    filter_status = None if status_filter == "All Statuses" else status_filter
    try:
        rows = list_bookings(
            tenant_id=tenant_id,
            status=filter_status,
            job_type=job_type_filter,
            search_query=search_query,
            etd_start=etd_start,
            etd_end=etd_end,
            eta_start=eta_start,
            eta_end=eta_end,
            limit=200
        ) or []
    except Exception as e:
        st.error(f"Failed to fetch bookings: {e}")
        rows = []

    if not rows:
        st.info("ℹ️ No booking records match the selected filter criteria.")
        return

    # Dataframe display matching exact spec:
    # BOOKING NO | REV | CUSTOMER | POL | POD | VESSEL | ETD | ETA | STATUS | JOB NO
    ledger_display = []
    for r in rows:
        rev_no = r.get("revision_no", 0)
        rev_str = f"REV {rev_no}" if rev_no is not None else "REV 0"
        vessel_voyage = f"{_s(r.get('vessel'))} {_s(r.get('voyage'))}".strip() or "—"
        
        ledger_display.append({
            "BOOKING NO": _s(r.get("booking_no")),
            "REV": rev_str,
            "CUSTOMER": _s(r.get("customer_name")),
            "POL": _s(r.get("pol"), "—"),
            "POD": _s(r.get("pod"), "—"),
            "VESSEL": vessel_voyage,
            "ETD": _s(r.get("etd"), "—"),
            "ETA": _s(r.get("eta"), "—"),
            "STATUS": _s(r.get("status")),
            "JOB NO": _s(r.get("job_no"), "—"),
        })

    df_display = pd.DataFrame(ledger_display)
    st.dataframe(df_display, use_container_width=True, hide_index=True)

    # --- PER-ROW ACTION CONTROL PANEL ---
    st.markdown("---")
    st.markdown(
        "<h5 style='font-size:14px; color:#F1F5F9; font-weight:700;'>⚡ Target Booking Actions & PDF Compiler</h5>",
        unsafe_allow_html=True,
    )

    col_sel, col_act1, col_act2, col_act3 = st.columns([3, 1.2, 1.2, 1.4])
    booking_nos = [r.get("booking_no") for r in rows if r.get("booking_no")]

    with col_sel:
        target_bno = st.selectbox(
            "Select Target Booking",
            options=booking_nos,
            key="bk_ledger_target_bno",
            label_visibility="collapsed",
        )

    if target_bno:
        target_rec = next((r for r in rows if r.get("booking_no") == target_bno), None)
        with col_act1:
            if st.button("👁️ Open", use_container_width=True, key=f"bk_open_btn_{target_bno}"):
                st.session_state["selected_booking_no"] = target_bno
                st.session_state["active_workspace_tab"] = "view"
                st.toast(f"Loaded {target_bno} in Workspace", icon="📑")
                st.rerun()

        with col_act2:
            if st.button("✏️ Edit / Revise", use_container_width=True, key=f"bk_edit_btn_{target_bno}"):
                st.session_state["selected_booking_no"] = target_bno
                st.session_state["active_workspace_tab"] = "edit"
                st.toast(f"Editing {target_bno} in Workspace", icon="✏️")
                st.rerun()

        with col_act3:
            if target_rec:
                try:
                    pdf_path = generate_booking_pdf(target_rec)
                    if pdf_path and os.path.exists(pdf_path):
                        with open(pdf_path, "rb") as f:
                            rev_label = target_rec.get("revision_no", 0)
                            st.download_button(
                                label=f"📄 PDF (REV {rev_label})",
                                data=f.read(),
                                file_name=os.path.basename(pdf_path),
                                mime="application/pdf",
                                key=f"dl_pdf_ledger_{target_bno}",
                                use_container_width=True,
                                type="primary",
                            )
                except Exception as pdf_err:
                    st.error(f"PDF Error: {pdf_err}")


# =========================================================
# COMPONENT 2: BOOKING WORKSPACE & REVISION ENGINE
# =========================================================
def _workspace_view(tenant_id, can_edit, user):
    st.markdown(
        "<h4 style='font-size:16px; color:#F1F5F9; font-weight:700;'>✏️ Booking Detail Workspace & Revision Control</h4>",
        unsafe_allow_html=True,
    )

    try:
        all_rows = list_bookings(tenant_id=tenant_id, limit=200) or []
    except Exception as e:
        st.error(f"Failed to fetch bookings: {e}")
        return

    if not all_rows:
        st.info("ℹ️ No bookings exist in database.")
        return

    b_options = [r["booking_no"] for r in all_rows if "booking_no" in r]

    # Pre-select from session state if set in ledger
    default_index = 0
    if "selected_booking_no" in st.session_state and st.session_state["selected_booking_no"] in b_options:
        default_index = b_options.index(st.session_state["selected_booking_no"])

    selected_no = st.selectbox(
        "Select Booking Record to Inspect / Edit",
        options=b_options,
        index=default_index,
        key="bk_ws_selector",
    )

    selected = get_booking(selected_no, tenant_id)
    if not selected:
        st.error("Could not load booking details.")
        return

    curr_status = str(selected.get("status", "DRAFT")).upper()
    rev_no = selected.get("revision_no", 0)
    is_locked = curr_status in ["CONVERTED", "CONVERTED TO JOB", "CANCELLED"]
    is_confirmed = curr_status == "CONFIRMED"
    allow_full_edit = can_edit and not is_locked and not is_confirmed

    # Top Header Card (Phase C Requirements)
    st.markdown(
        f"""
        <div style="padding: 16px; border: 1px solid #334155; background-color: #0F172A; border-radius:10px; margin-bottom: 16px;">
            <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap;">
                <div>
                    <span style="font-size:18px; font-weight:800; color:#F8FAFC;">BOOKING CONFIRMATION: BC-{selected.get('booking_no')}</span>
                    <span style="margin-left: 12px; background: #1E293B; border: 1px solid #475569; padding: 2px 10px; border-radius: 12px; font-size:12px; font-weight:700; color:#38BDF8;">REV {rev_no}</span>
                </div>
                <div style="margin-top: 4px;">
                    <span style="font-size:13px; color:#94A3B8; margin-right: 16px;">Customer: <b>{selected.get('customer_name','—')}</b></span>
                    <span style="font-size:13px; color:#94A3B8; margin-right: 16px;">Status: <b style="color:#F1F5F9;">{curr_status}</b></span>
                    <span style="font-size:12px; color:#64748B;">Updated: {_s(selected.get('updated_at') or selected.get('created_at'), '—')}</span>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Top Action Bar (Phase C & K Requirements)
    st_act1, st_act2, st_act3, st_act4 = st.columns([1.5, 2, 2, 2])

    with st_act1:
        if st.button("← Refresh", key=f"ws_ref_btn_{selected_no}", use_container_width=True):
            st.rerun()

    with st_act2:
        # Controlled Status Transitions
        if can_edit and not is_locked:
            if curr_status == "DRAFT":
                if st.button("🚀 Submit Booking", key=f"btn_sub_{selected_no}", type="secondary", use_container_width=True):
                    try:
                        update_booking(selected_no, {"status": "SUBMITTED"}, tenant_id)
                        st.success("Booking SUBMITTED")
                        st.rerun()
                    except Exception as ex:
                        st.error(str(ex))
            elif curr_status == "SUBMITTED":
                if st.button("✅ Confirm Booking", key=f"btn_cnf_{selected_no}", type="primary", use_container_width=True):
                    try:
                        update_booking(selected_no, {"status": "CONFIRMED"}, tenant_id)
                        st.success("Booking CONFIRMED")
                        st.rerun()
                    except Exception as ex:
                        st.error(str(ex))

    with st_act3:
        if is_confirmed and can_edit:
            st.markdown(
                "<span style='color:#F59E0B; font-weight:700; font-size:12px;'>🔒 CONFIRMED (Edit Locked)</span>",
                unsafe_allow_html=True,
            )

    with st_act4:
        try:
            pdf_path = generate_booking_pdf(selected)
            if pdf_path and os.path.exists(pdf_path):
                with open(pdf_path, "rb") as f:
                    st.download_button(
                        label=f"📄 Current REV {rev_no} PDF",
                        data=f.read(),
                        file_name=os.path.basename(pdf_path),
                        mime="application/pdf",
                        key=f"dl_pdf_ws_top_{selected_no}",
                        use_container_width=True,
                        type="primary",
                    )
        except Exception as pdf_err:
            st.error(f"PDF Error: {pdf_err}")

    # Controlled Revision Workflow for CONFIRMED bookings
    if is_confirmed and can_edit:
        st.info("ℹ️ This Booking is CONFIRMED. Direct editing is locked. To modify fields, click below to create a Controlled Revision.")
        with st.expander("🚀 Create Controlled Revision (Unlock for Edit)", expanded=True):
            with st.form(f"form_create_rev_{selected_no}"):
                st.markdown("**Controlled Revision Details**")
                rev_reason = st.text_input(
                    "Revision Reason *",
                    placeholder="e.g. Customer requested POL change from BKK to LCH",
                    key=f"rev_reason_input_{selected_no}",
                )
                sub_rev = st.form_submit_button("🚀 Confirm & Create Revision", type="primary", use_container_width=True)

                if sub_rev:
                    if not rev_reason.strip():
                        st.error("⚠️ Revision reason is required.")
                    else:
                        try:
                            new_rev = create_booking_revision(selected_no, rev_reason.strip(), user, tenant_id)
                            st.success(f"✅ Controlled Revision REV {new_rev} created! Booking reset to DRAFT for edits.")
                            st.rerun()
                        except Exception as rev_err:
                            st.error(f"Revision creation failed: {rev_err}")

    # Job Conversion Block (for CONFIRMED Bookings)
    if curr_status == "CONFIRMED" and can_edit:
        st.markdown("---")
        with st.expander("⚡ Convert Booking to Operational Job", expanded=False):
            st.caption("Converts this confirmed booking into a billable operational job (shipment).")
            if st.button("🚀 Convert to Job Now", key=f"btn_cvt_job_{selected_no}", type="primary", use_container_width=True):
                try:
                    job_no = convert_booking_to_job(selected_no, user)
                    st.success(f"✅ Booking converted to Operational Job '{job_no}'!")
                    st.rerun()
                except Exception as cvt_err:
                    st.error(f"Conversion failed: {cvt_err}")

    st.markdown("---")

    # Multi-Tab Detailed Editor Workspace
    t1, t2, t3, t4, t5, t6, t7, t8 = st.tabs([
        "1. Parties & Header",
        "2. Routing Details",
        "3. Vessel / Flight",
        "4. Cut-offs & Terminals",
        "5. Cargo & Containers",
        "6. Commercial & Remarks",
        "7. 🕘 Revision History",
        "8. 📎 Documents"
    ])

    with st.form(f"bk_ws_detail_form_{selected_no}"):
        with t1:
            st.markdown("#### Parties & Header Metadata")
            c1, c2, c3, c4 = st.columns(4)
            c1.text_input("Booking No", value=_s(selected.get("booking_no")), disabled=True)
            c1.text_input("Quotation Ref", value=_s(selected.get("quotation_no")), disabled=True)

            cust = c2.text_input("Customer Name *", value=_s(selected.get("customer_name")), disabled=not allow_full_edit)
            jtype = c2.selectbox(
                "Job Type *",
                options=list(JOB_TYPES.keys()),
                index=list(JOB_TYPES.keys()).index(selected.get("job_type", "SE")) if selected.get("job_type", "SE") in JOB_TYPES else 0,
                disabled=not allow_full_edit,
            )

            shipper = c3.text_input("Shipper", value=_s(selected.get("shipper")), disabled=not allow_full_edit)
            consignee = c3.text_input("Consignee", value=_s(selected.get("consignee")), disabled=not allow_full_edit)
            notify = c4.text_input("Notify Party", value=_s(selected.get("notify_party")), disabled=not allow_full_edit)

        with t2:
            st.markdown("#### Routing Ports")
            r1, r2, r3, r4, r5 = st.columns(5)
            por = r1.text_input("POR (Place of Receipt)", value=_s(selected.get("por")), disabled=not allow_full_edit)
            pol = r2.text_input("POL (Port of Loading)", value=_s(selected.get("pol")), disabled=not allow_full_edit)
            tranship = r3.text_input("Transhipment Port", value=_s(selected.get("transhipment_port")), disabled=not allow_full_edit)
            pod = r4.text_input("POD (Port of Discharge)", value=_s(selected.get("pod")), disabled=not allow_full_edit)
            dest = r5.text_input("Final Destination", value=_s(selected.get("final_destination")), disabled=not allow_full_edit)

        with t3:
            st.markdown("#### Transport & Schedule")
            v1, v2, v3, v4 = st.columns(4)
            carrier = v1.text_input("Carrier", value=_s(selected.get("carrier")), disabled=not allow_full_edit)
            liner = v1.text_input("Liner", value=_s(selected.get("liner")), disabled=not allow_full_edit)
            vessel = v2.text_input("Vessel", value=_s(selected.get("vessel")), disabled=not allow_full_edit)
            voyage = v2.text_input("Voyage", value=_s(selected.get("voyage")), disabled=not allow_full_edit)
            mvessel = v3.text_input("Mother Vessel", value=_s(selected.get("m_vessel")), disabled=not allow_full_edit)
            feeder = v3.text_input("Feeder", value=_s(selected.get("feeder")), disabled=not allow_full_edit)

            etd = v4.date_input("ETD", value=_parse_date(selected.get("etd")), disabled=not allow_full_edit)
            eta = v4.date_input("ETA", value=_parse_date(selected.get("eta")), disabled=not allow_full_edit)

        with t4:
            st.markdown("#### Cut-Off Dates & Terminal Locations")
            u1, u2, u3, u4 = st.columns(4)
            cy_date = u1.date_input("CY Date", value=_parse_date(selected.get("cy_date")), disabled=not allow_full_edit)
            cy_place = u1.text_input("CY Place", value=_s(selected.get("cy_place")), disabled=not allow_full_edit)
            cfs_date = u2.date_input("CFS Date", value=_parse_date(selected.get("cfs_date")), disabled=not allow_full_edit)
            cfs_place = u2.text_input("CFS Place", value=_s(selected.get("cfs_place")), disabled=not allow_full_edit)
            ret_date = u3.date_input("Return Date", value=_parse_date(selected.get("customer_return_date")), disabled=not allow_full_edit)
            ret_place = u3.text_input("Return Place", value=_s(selected.get("return_place")), disabled=not allow_full_edit)
            closing = u4.text_input("Closing Time", value=_s(selected.get("closing_time")), disabled=not allow_full_edit)

        with t5:
            st.markdown("#### Cargo Specifications & Container Summary")
            g1, g2, g3, g4 = st.columns(4)
            ctype = g1.selectbox(
                "Cargo Type",
                options=CARGO_TYPES,
                index=CARGO_TYPES.index(selected.get("cargo_type", "")) if selected.get("cargo_type") in CARGO_TYPES else 0,
                disabled=not allow_full_edit,
            )
            commodity = g1.text_input("Commodity", value=_s(selected.get("commodity")), disabled=not allow_full_edit)
            gw = g2.number_input("Gross Weight (KG)", value=float(selected.get("gross_weight") or 0.0), disabled=not allow_full_edit)
            cbm = g2.number_input("Measurement (CBM)", value=float(selected.get("measurement_cbm") or 0.0), disabled=not allow_full_edit)
            pqty = g3.number_input("Package Qty", value=int(selected.get("package_qty") or 0), step=1, disabled=not allow_full_edit)
            punit = g3.text_input("Package Unit", value=_s(selected.get("package_unit"), "PKGS"), disabled=not allow_full_edit)
            cnt_sum = g4.text_input("Container Summary", value=_s(selected.get("container_summary")), disabled=not allow_full_edit)

        with t6:
            st.markdown("#### Commercial Terms & Remarks")
            fterm = st.selectbox(
                "Freight Term",
                options=["", "PREPAID", "COLLECT"],
                index=["", "PREPAID", "COLLECT"].index(selected.get("freight_term")) if selected.get("freight_term") in ["", "PREPAID", "COLLECT"] else 0,
                disabled=not allow_full_edit,
            )
            remark = st.text_area("Remarks", value=_s(selected.get("remark")), disabled=not allow_full_edit)

        save_details = st.form_submit_button("💾 Save Workspace Changes", type="primary", use_container_width=True, disabled=not allow_full_edit)

    if save_details:
        try:
            update_data = {
                "customer_name": cust.strip() if cust else None,
                "job_type": jtype,
                "shipper": shipper.strip() if shipper else None,
                "consignee": consignee.strip() if consignee else None,
                "notify_party": notify.strip() if notify else None,
                "por": por.strip() if por else None,
                "pol": pol.strip() if pol else None,
                "transhipment_port": tranship.strip() if tranship else None,
                "pod": pod.strip() if pod else None,
                "final_destination": dest.strip() if dest else None,
                "carrier": carrier.strip() if carrier else None,
                "liner": liner.strip() if liner else None,
                "vessel": vessel.strip() if vessel else None,
                "voyage": voyage.strip() if voyage else None,
                "m_vessel": mvessel.strip() if mvessel else None,
                "feeder": feeder.strip() if feeder else None,
                "etd": etd.isoformat() if etd else None,
                "eta": eta.isoformat() if eta else None,
                "cy_date": cy_date.isoformat() if cy_date else None,
                "cy_place": cy_place.strip() if cy_place else None,
                "cfs_date": cfs_date.isoformat() if cfs_date else None,
                "cfs_place": cfs_place.strip() if cfs_place else None,
                "customer_return_date": ret_date.isoformat() if ret_date else None,
                "return_place": ret_place.strip() if ret_place else None,
                "closing_time": closing.strip() if closing else None,
                "cargo_type": ctype,
                "commodity": commodity.strip() if commodity else None,
                "gross_weight": float(gw) if gw else None,
                "measurement_cbm": float(cbm) if cbm else None,
                "package_qty": int(pqty) if pqty else None,
                "package_unit": punit.strip() if punit else None,
                "container_summary": cnt_sum.strip() if cnt_sum else None,
                "freight_term": fterm,
                "remark": remark.strip() if remark else None,
            }
            update_booking(selected_no, update_data, tenant_id)
            st.success(f"✅ Workspace updates committed for {selected_no}!")
            st.rerun()
        except Exception as save_err:
            st.error(f"Save Failed: {save_err}")

    # Tab 7: Revision History Outside Form (Phase D Requirements)
    with t7:
        st.markdown("#### 🕘 Controlled Revision Audit Trail & Historical PDF Compiler")
        rev_history = get_revision_history(selected_no)
        if rev_history:
            rev_table_rows = []
            for rh in rev_history:
                rev_table_rows.append({
                    "Revision": f"REV {rh.get('revision_no')}",
                    "Date": _s(rh.get("revised_at") or rh.get("created_at")),
                    "Reason": _s(rh.get("revision_reason")),
                    "Created By": _s(rh.get("revised_by")),
                    "Status": "HISTORICAL SNAPSHOT",
                })
            st.dataframe(pd.DataFrame(rev_table_rows), use_container_width=True, hide_index=True)

            st.markdown("---")
            st.markdown("##### 📄 Download Historical Revision PDF")
            st.caption("Loads the exact historical JSON snapshot saved during revision creation. Does not reconstruct from current Booking data.")

            h_col1, h_col2 = st.columns([3, 2])
            with h_col1:
                selected_hist_rev = st.selectbox(
                    "Select Historical Revision Version",
                    options=[rh.get("revision_no") for rh in rev_history],
                    format_func=lambda x: f"REV {x} Snapshot",
                    key=f"hist_rev_sel_{selected_no}",
                )

            with h_col2:
                st.write("")
                st.write("")
                if selected_hist_rev is not None:
                    hist_item = next((rh for rh in rev_history if rh.get("revision_no") == selected_hist_rev), None)
                    if hist_item and hist_item.get("parsed_snapshot"):
                        try:
                            # Generate PDF from historical snapshot dict
                            hist_pdf_path = generate_booking_pdf(hist_item["parsed_snapshot"])
                            if hist_pdf_path and os.path.exists(hist_pdf_path):
                                with open(hist_pdf_path, "rb") as hf:
                                    st.download_button(
                                        label=f"📥 Download REV {selected_hist_rev} PDF",
                                        data=hf.read(),
                                        file_name=os.path.basename(hist_pdf_path),
                                        mime="application/pdf",
                                        key=f"dl_hist_pdf_btn_{selected_no}_{selected_hist_rev}",
                                        type="primary",
                                        use_container_width=True,
                                    )
                        except Exception as hpdf_e:
                            st.error(f"Historical PDF Error: {hpdf_e}")
        else:
            st.info("ℹ️ No historical revisions recorded for this Booking yet. Current active version is REV 0.")

    with t8:
        from views.document_ui import render_document_section
        st.subheader("📎 Documents")
        render_document_section("BOOKING", selected_no)


# =========================================================
# COMPONENT 3: CREATION FORM (PULL FROM QUOTATION)
# =========================================================
def _create_form(user, tenant_id):
    st.markdown(
        "<h4 style='font-size:16px; color:#F1F5F9; font-weight:700;'>➕ Construct New Booking Entry</h4>",
        unsafe_allow_html=True,
    )

    with st.expander("📥 Pull Data From Quotation", expanded=False):
        try:
            quotations = list_quotations() or []
            q_options = ["-- Select Target Reference --"] + [
                str(q["quotation_no"]) for q in quotations if "quotation_no" in q
            ]
        except Exception as e:
            st.warning(f"Unable to read quotations: {e}")
            q_options = ["-- Select Target Reference --"]

        selected_q = st.selectbox("Target Quotation No", options=q_options, key="b_create_q_sel")

        if selected_q and selected_q != "-- Select Target Reference --":
            if st.button("⚡ Autopopulate from Quotation", key="b_create_pull_btn", type="secondary", use_container_width=True):
                try:
                    q = get_quotation_by_no(selected_q)
                    if q:
                        st.session_state["booking_prefill"] = q
                        st.toast(f"Data mapped from {selected_q}", icon="⚡")
                        st.rerun()
                except Exception as ex:
                    st.error(f"Pull failed: {ex}")

    pre = st.session_state.get("booking_prefill", {})

    with st.form(key="b_create_main_form"):
        st.markdown("#### 1. Parties & Booking Reference")
        c0, c1, c2 = st.columns(3)
        custom_bno = c0.text_input("Carrier Booking No. (เลข Booking จากสายเรือ)", value="", placeholder="e.g. ONEBKK2608001 (ว่างไว้หากให้ออกอัตโนมัติ)")
        job_type = c1.selectbox(
            "Job Type *",
            options=list(JOB_TYPES.keys()),
            format_func=lambda x: JOB_TYPES.get(x, x),
            index=list(JOB_TYPES.keys()).index(pre.get("job_type", "SE")) if pre.get("job_type", "SE") in JOB_TYPES else 0,
        )
        customer_name = c1.text_input("Customer Name *", value=_s(pre.get("customer_name")))
        shipper = c2.text_input("Shipper", value=_s(pre.get("shipper")))
        consignee = c2.text_input("Consignee", value=_s(pre.get("consignee")))
        notify_party = c2.text_input("Notify Party", value=_s(pre.get("notify_party")))

        st.markdown("#### 2. Routing")
        r1, r2, r3, r4, r5 = st.columns(5)
        por = r1.text_input("POR (Receipt)", value=_s(pre.get("por")))
        pol = r2.text_input("POL (Load)", value=_s(pre.get("pol")))
        transhipment_port = r3.text_input("Transhipment", value=_s(pre.get("transhipment_port")))
        pod = r4.text_input("POD (Discharge)", value=_s(pre.get("pod")))
        final_destination = r5.text_input("Final Destination", value=_s(pre.get("final_destination")))

        st.markdown("#### 3. Vessel / Flight Details")
        v1, v2, v3, v4 = st.columns(4)
        carrier = v1.text_input("Carrier", value=_s(pre.get("carrier")))
        liner = v1.text_input("Liner", value=_s(pre.get("liner")))
        vessel = v2.text_input("Vessel", value=_s(pre.get("vessel")))
        voyage = v2.text_input("Voyage", value=_s(pre.get("voyage")))
        m_vessel = v3.text_input("Mother Vessel", value=_s(pre.get("m_vessel")))
        feeder = v3.text_input("Feeder", value=_s(pre.get("feeder")))

        pre_etd = _parse_date(pre.get("etd")) or date.today()
        pre_eta = _parse_date(pre.get("eta")) or (date.today() + pd.Timedelta(days=14))
        etd = v4.date_input("ETD *", value=pre_etd)
        eta = v4.date_input("ETA *", value=pre_eta)

        st.markdown("#### 4. Cut-Offs & Terminals")
        t1, t2, t3, t4 = st.columns(4)
        cy_date = t1.date_input("CY Date", value=_parse_date(pre.get("cy_date")))
        cy_place = t1.text_input("CY Place", value=_s(pre.get("cy_place")))
        cfs_date = t2.date_input("CFS Date", value=_parse_date(pre.get("cfs_date")))
        cfs_place = t2.text_input("CFS Place", value=_s(pre.get("cfs_place")))
        customer_return_date = t3.date_input("Return Date", value=_parse_date(pre.get("customer_return_date")))
        return_place = t3.text_input("Return Place", value=_s(pre.get("return_place")))
        closing_time = t4.text_input("Closing Time", value=_s(pre.get("closing_time")))

        st.markdown("#### 5. Cargo & Containers")
        g1, g2, g3, g4 = st.columns(4)
        cargo_type = g1.selectbox("Cargo Type", options=CARGO_TYPES, index=CARGO_TYPES.index(pre.get("cargo_type", "")) if pre.get("cargo_type") in CARGO_TYPES else 0)
        commodity = g1.text_input("Commodity", value=_s(pre.get("commodity")))

        gross_weight = g2.number_input("Gross Weight (KG)", value=float(pre.get("gross_weight") or pre.get("weight_kg") or 0.0))
        measurement_cbm = g2.number_input("Measurement (CBM)", value=float(pre.get("measurement_cbm") or pre.get("volume_cbm") or 0.0))

        package_qty = g3.number_input("Package Qty", value=int(pre.get("package_qty") or 0), step=1)
        package_unit = g3.text_input("Package Unit", value=_s(pre.get("package_unit"), "PKGS"))

        default_cnt = ""
        if pre.get("container_type") and pre.get("container_quantity"):
            default_cnt = f"{pre['container_quantity']}x {pre['container_type']}"
        container_summary = g4.text_input("Container Summary (e.g. 2x 40HC)", value=_s(pre.get("container_summary") or default_cnt))
        freight_term = g4.selectbox("Freight Term", options=["", "PREPAID", "COLLECT"], index=["", "PREPAID", "COLLECT"].index(pre.get("freight_term")) if pre.get("freight_term") in ["", "PREPAID", "COLLECT"] else 0)

        st.markdown("#### 6. Remarks")
        remark = st.text_area("Remark", value=_s(pre.get("remark")))

        submit_btn = st.form_submit_button("🚀 Finalize and Commit Booking", type="primary", use_container_width=True)

    if submit_btn:
        errors = []
        if not customer_name.strip():
            errors.append("Customer Name is required.")
        if etd and eta and eta < etd:
            errors.append("ETA cannot be before ETD.")
        if gross_weight < 0: errors.append("Gross Weight cannot be negative.")
        if measurement_cbm < 0: errors.append("Measurement CBM cannot be negative.")
        if package_qty < 0: errors.append("Package Quantity cannot be negative.")

        if errors:
            for err in errors:
                st.error(f"⚠️ Validation Failure: {err}")
            return

        try:
            payload = {
                "booking_no": custom_bno.strip() if custom_bno.strip() else None,
                "quotation_id": pre.get("id"),
                "quotation_no": _s(pre.get("quotation_no")),
                "job_type": job_type,
                "customer_name": customer_name.strip(),
                "shipper": shipper.strip() if shipper else None,
                "consignee": consignee.strip() if consignee else None,
                "notify_party": notify_party.strip() if notify_party else None,
                "pol": pol.strip() if pol else None,
                "por": por.strip() if por else None,
                "pod": pod.strip() if pod else None,
                "final_destination": final_destination.strip() if final_destination else None,
                "transhipment_port": transhipment_port.strip() if transhipment_port else None,
                "carrier": carrier.strip() if carrier else None,
                "liner": liner.strip() if liner else None,
                "vessel": vessel.strip() if vessel else None,
                "voyage": voyage.strip() if voyage else None,
                "m_vessel": m_vessel.strip() if m_vessel else None,
                "feeder": feeder.strip() if feeder else None,
                "etd": etd.isoformat() if etd else None,
                "eta": eta.isoformat() if eta else None,
                "cy_date": cy_date.isoformat() if cy_date else None,
                "cy_place": cy_place.strip() if cy_place else None,
                "cfs_date": cfs_date.isoformat() if cfs_date else None,
                "cfs_place": cfs_place.strip() if cfs_place else None,
                "customer_return_date": customer_return_date.isoformat() if customer_return_date else None,
                "return_place": return_place.strip() if return_place else None,
                "closing_time": closing_time.strip() if closing_time else None,
                "cargo_type": cargo_type,
                "commodity": commodity.strip() if commodity else None,
                "gross_weight": float(gross_weight) if gross_weight else None,
                "measurement_cbm": float(measurement_cbm) if measurement_cbm else None,
                "package_qty": int(package_qty) if package_qty else None,
                "package_unit": package_unit.strip() if package_unit else None,
                "container_summary": container_summary.strip() if container_summary else None,
                "freight_term": freight_term,
                "remark": remark.strip() if remark else None,
                "created_by": str(user.get("username", "system_actor")),
            }

            booking_no = create_booking(payload, user)
            log_action(user.get("id", 1), tenant_id, "booking", booking_no, "CREATE")

            st.success(f"✅ Booking Manifest created: {booking_no}")
            st.session_state.pop("booking_prefill", None)
            st.balloons()
            st.rerun()
        except Exception as commit_ex:
            st.error(f"Creation Error: {commit_ex}")