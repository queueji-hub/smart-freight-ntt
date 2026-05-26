"""
Booking Confirmation & Job Pipe Management View Workspace
PostgreSQL Connected - 100% Professional ERP Grade Interface
"""

import io
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
)
from managers.quotation_manager import (
    get_quotation_by_no,
    list_quotations
)

from core.audit import log_action
from pdf.booking_pdf import generate_booking_pdf

# =========================================================
# GLOBAL CONSTANTS DEFINITIONS
# =========================================================
CARGO_TYPES = ["", "FCL", "LCL", "AIR", "TRUCK"]
STATUS_OPTIONS = ["Proceed", "Finished", "Closed", "Canceled"]


# =========================================================
# PERFORMANCE & DATA INTELLIGENCE LAYER
# =========================================================
def get_bookings(status=None):
    """Fetches transactional booking registries matching optional status filter."""
    try:
        return list_bookings(status=status) or []
    except Exception as e:
        st.error(f"Failed to fetch booking indices: {str(e)}")
        return []


# =========================================================
# SECURE DATE PARSER IMPLEMENTATION
# =========================================================
def _parse_date(value):
    """Safely converts dynamic input formats to concrete python date objects."""
    if not value:
        return date.today()
    if isinstance(value, date):
        return value
    if isinstance(value, datetime):
        return value.date()
    try:
        return date.fromisoformat(str(value)[:10])
    except (ValueError, TypeError):
        return date.today()


# =========================================================
# MAIN PRESENTATION ENGINE壳 ROUTER
# =========================================================
def render():
    user = st.session_state.get("user", {})
    role = str(user.get("role", "")).lower()
    tenant_id = user.get("tenant_id", "demo")

    can_edit = can_write(role, "booking")

    st.markdown("<p style='color: #38BDF8; font-weight: 700; font-size: 13px; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 2px;'>Operational Pipeline Control</p>", unsafe_allow_html=True)
    st.markdown("<h2 style='margin-top: 0px; font-weight: 800; color:#F8FAFC;'>📑 Freight Booking System</h2>", unsafe_allow_html=True)
    st.caption("Secure Operational Dispatch — Smooth translation engine for Commercial Quotation ➡️ Active Booking Manifest ➡️ Billable Job Pipeline.")

    if can_edit:
        tabs = st.tabs(["➕ Structural Creation Engine", "📋 Historical Manifest Ledger", "✏️ Document Reconciliation"])

        with tabs[0]:
            _create_form(user, tenant_id)

        with tabs[1]:
            _list_view(tenant_id)

        with tabs[2]:
            _edit_view(tenant_id)
    else:
        # Read-Only Enforcement Mode Block
        _list_view(tenant_id)


# =========================================================
# COMPONENT: STRUCTURAL CREATION ENGINE FORM
# =========================================================
def _create_form(user, tenant_id):
    st.markdown("<h4 style='font-size:16px; color:#F1F5F9; font-weight:700;'>➕ Construct New Booking Entry</h4>", unsafe_allow_html=True)

    # --- PIPELINE INTELLIGENCE INTEGRATION (QUOTATION PULL) ---
    with st.expander("📥 Pipeline Automation — Pull Pro-Forma From Registered Quotation", expanded=False):
        try:
            quotations = list_quotations(tenant_id) or []
            q_options = ["-- Select Active Target Reference --"] + [str(q["quotation_no"]) for q in quotations if "quotation_no" in q]
        except Exception as e:
            st.warning(f"Unable to read commercial index tracking records: {str(e)}")
            q_options = ["-- Select Active Target Reference --"]

        selected_q = st.selectbox(
            "Target Commercial Document Reference Number",
            options=q_options,
            key="booking_creation_quotation_selector"
        )

        if selected_q and selected_q != "-- Select Active Target Reference --":
            if st.button("⚡ Autopopulate Structural Parameters", key="booking_creation_pull_data_trigger", type="secondary", use_container_width=True):
                with st.spinner("Injecting relational parameters..."):
                    try:
                        q = get_quotation_by_no(selected_q)
                        if q:
                            st.session_state["booking_prefill"] = q
                            st.toast(f"✅ Data mapped from: {selected_q}", icon="⚡")
                            st.rerun()
                        else:
                            st.error("Target data structure returned empty parameters.")
                    except Exception as pull_ex:
                        st.error(f"Mapping pipeline failed: {str(pull_ex)}")

    pre = st.session_state.get("booking_prefill", {})

    # --- MAIN TRANSACTION PARAMETERS GRID ---
    with st.container(border=True):
        st.markdown("**📋 General Manifest Specifications**")
        c1, c2, c3 = st.columns(3)

        with c1:
            job_type = st.selectbox(
                "Operational Execution Vector (Job Type) *", 
                options=list(JOB_TYPES.keys()), 
                format_func=lambda x: JOB_TYPES.get(x, x),
                key="booking_creation_job_type_input"
            )
            customer_name = st.text_input("Legal Consignor Entity (Customer) *", value=str(pre.get("customer_name", "")), key="booking_creation_customer_input")
            shipper = st.text_input("Cargo Originator Profile (Shipper)", value=str(pre.get("shipper_cnee", "")), key="booking_creation_shipper_input")

        with c2:
            pol = st.text_input("Port of Loading (POL)", value=str(pre.get("pol", "")), key="booking_creation_pol_input", placeholder="e.g., THLCH")
            pod = st.text_input("Port of Discharge (POD)", value=str(pre.get("pod", "")), key="booking_creation_pod_input", placeholder="e.g., USLAX")
            carrier = st.text_input("Intermodal Transport Operator (Carrier)", value=str(pre.get("carrier", "")), key="booking_creation_carrier_input")

        with c3:
            # PostgreSQL Safe Isoformat Parsing Guard
            pre_etd = _parse_date(pre.get("etd")) if "etd" in pre else date.today()
            pre_eta = _parse_date(pre.get("eta")) if "eta" in pre else (date.today() + pd.Timedelta(days=14))
            
            etd = st.date_input("Estimated Time of Departure (ETD) *", value=pre_etd, key="booking_creation_etd_input")
            eta = st.date_input("Estimated Time of Arrival (ETA) *", value=pre_eta, key="booking_creation_eta_input")

        remark = st.text_area("Operational Notes / Custom Handling Directives", value=str(pre.get("remark", "")), key="booking_creation_remark_input", placeholder="Type cross-docking instructions, special temp control requirements...")

    # --- TRANSACTIONAL PERSISTENCE EXECUTION ---
    if st.button("🚀 Finalize and Commit Booking to Ledger", type="primary", key="booking_creation_commit_btn", use_container_width=True):
        if not customer_name.strip():
            st.error("⚠️ Validation Failure: Legal Consignor Entity parameter is strictly required.")
            return

        if etd and eta and eta < etd:
            st.warning("⚠️ Discrepancy Flagged: Estimated Departure (ETD) cannot fall after Arrival (ETA).")
            return

        with st.spinner("Committing secure operational entry transaction..."):
            try:
                payload = {
                    "job_type": job_type,
                    "customer_name": customer_name.strip(),
                    "shipper": shipper.strip() if shipper else None,
                    "pol": pol.strip() if pol else None,
                    "pod": pod.strip() if pod else None,
                    "carrier": carrier.strip() if carrier else None,
                    "etd": etd.isoformat() if etd else None,
                    "eta": eta.isoformat() if eta else None,
                    "remark": remark.strip() if remark else None,
                    "created_by": str(user.get("username", "system_actor"))
                }

                booking_no = create_booking(payload)

                # Append secure transactional integrity trail
                log_action(
                    user_id=user.get("id", 1),
                    tenant_id=tenant_id,
                    entity="booking",
                    entity_id=booking_no,
                    action="CREATE"
                )

                st.success(f"✅ Booking Manifest successfully committed to production ledger indices: {booking_no}")
                st.session_state.pop("booking_prefill", None)
                st.balloons()
                st.rerun()
            except Exception as commit_ex:
                st.error(f"🚨 Relational Engine Error Intercepted: {str(commit_ex)}")


# =========================================================
# COMPONENT: LEDGER SEARCH & HIGH PERFORMANCE DIRECTORY
# =========================================================
def _list_view(tenant_id):
    st.markdown("<h4 style='font-size:16px; color:#F1F5F9; font-weight:700;'>📋 Historical Manifest Ledger</h4>", unsafe_allow_html=True)

    status_filter = st.selectbox(
        "Filter by Operational Status Index",
        options=["All Profiles"] + STATUS_OPTIONS,
        key="booking_list_status_filter_input"
    )

    with st.spinner("Quoting active database tables..."):
        filter_param = None if status_filter == "All Profiles" else status_filter
        rows = get_bookings(filter_param)

    if not rows:
        st.info("ℹ️ No active operational logs match the provided parameters.")
        return

    # Modern Enterprise UI Data Frame Presentation Layout
    df = pd.DataFrame(rows)
    
    column_mapping = {
        "booking_no": "Booking ID",
        "job_type": "Track Type",
        "customer_name": "Consignor Principal",
        "pol": "POL",
        "pod": "POD",
        "carrier": "Vessel Line",
        "etd": "Departure Date",
        "eta": "Arrival Date",
        "status": "Operational Status"
    }
    
    existing_cols = [col for col in df.columns if col in column_mapping]
    df_display = df[existing_cols].rename(columns=column_mapping)

    st.dataframe(df_display, use_container_width=True, hide_index=True)

    # --- 1-CLICK INSTANT GENERATE & DOWNLOAD STREAM ARCHITECTURE ---
    st.markdown("<div style='margin-top: 20px;'></div>", unsafe_allow_html=True)
    st.markdown("---")
    st.markdown("<h5 style='font-size:14px; color:#F1F5F9; font-weight:700;'>📥 Instant Document Compilation Engine</h5>", unsafe_allow_html=True)
    
    col_pdf_sel, col_pdf_action = st.columns([3, 1])
    
    with col_pdf_sel:
        target_pdf_no = st.selectbox(
            "Select Registry ID for Document Output Compilation",
            options=df["booking_no"].tolist() if "booking_no" in df.columns else [],
            key="booking_list_pdf_selection_box",
            label_visibility="collapsed"
        )

    with col_pdf_action:
        if target_pdf_no:
            try:
                # Compile PDF file structure on the fly cleanly inside context parameters
                target_booking_record = next((r for r in rows if r.get("booking_no") == target_pdf_no), None)
                if target_booking_record:
                    compiled_pdf_path = generate_booking_pdf(target_booking_record)
                    
                    if compiled_pdf_path and os.path.exists(compiled_pdf_path):
                        with open(compiled_pdf_path, "rb") as pdf_file_bytes:
                            st.download_button(
                                label="📥 Download PDF",
                                data=pdf_file_bytes.read(),
                                file_name=f"BC_{target_pdf_no}.pdf",
                                mime="application/pdf",
                                key=f"booking_list_download_trigger_{target_pdf_no}",
                                use_container_width=True,
                                type="primary"
                            )
                    else:
                        st.button("⚠️ Build Refused", disabled=True, use_container_width=True)
                else:
                    st.button("❌ File Missing", disabled=True, use_container_width=True)
            except Exception as pdf_err:
                st.error(f"Compilation Intercept Failure: {str(pdf_err)}")


# =========================================================
# COMPONENT: DATA RECONCILIATION & RE-ENGINEERING
# =========================================================
def _edit_view(tenant_id):
    st.markdown("<h4 style='font-size:16px; color:#F1F5F9; font-weight:700;'>✏️ Modify Existing Booking Matrix</h4>", unsafe_allow_html=True)

    rows = get_bookings()
    if not rows:
        st.info("ℹ️ Modification target paths empty: Ledger contains zero rows.")
        return

    # Structured selector configuration safely isolated
    booking_mapping = {r["booking_no"]: r for r in rows if "booking_no" in r}
    selected_no = st.selectbox(
        "Active Checkout Working Target Document",
        options=list(booking_mapping.keys()),
        key="booking_edit_target_checkout_selector"
    )

    selected = booking_mapping.get(selected_no)

    if selected:
        st.markdown(f"<div style='padding: 20px; border: 1px solid #334155; background-color: #0F172A; border-radius:10px; margin-top:10px;'>", unsafe_allow_html=True)
        st.markdown(f"##### 🔒 Checked out Profile: Entry `{selected_no}`")
        
        # Enforce distinct dynamic Form Block IDs per distinct selection path safely
        with st.form(key=f"booking_reconciliation_isolated_panel_{selected_no}"):
            current_status = str(selected.get("status", "Proceed"))
            status_index = STATUS_OPTIONS.index(current_status) if current_status in STATUS_OPTIONS else 0
            
            status = st.selectbox(
                "Operational Milestone Status Descriptor",
                options=STATUS_OPTIONS,
                index=status_index,
                key=f"booking_edit_status_field_{selected_no}"
            )

            remark = st.text_area(
                "Amend Remarks / Log Updates Context",
                value=str(selected.get("remark", "") or ""),
                key=f"booking_edit_remark_field_{selected_no}"
            )

            col_action_save, col_action_del = st.columns([1, 1])
            
            save_triggered = col_action_save.form_submit_button("💾 Save Matrix Parameters", type="primary", use_container_width=True)
            delete_triggered = col_action_del.form_submit_button("🗑️ Purge Records Completely", use_container_width=True)

        # Process non-nested logical state outside the layout containment securely
        if save_triggered:
            with st.spinner("Applying tracking mutations..."):
                try:
                    update_booking(
                        selected["booking_no"],
                        {
                            "status": status,
                            "remark": remark.strip()
                        }
                    )
                    st.toast("💾 Operational Parameters altered successfully.", icon="✅")
                    st.rerun()
                except Exception as ex_save:
                    st.error(f"Database rejection caught on alteration routine: {str(ex_save)}")

        if delete_triggered:
            with st.spinner("Injecting purge scheme..."):
                try:
                    delete_booking(selected["booking_no"])
                    st.toast("🗑️ Tracking profile cleanly removed from indexes.", icon="⚠️")
                    st.rerun()
                except Exception as ex_del:
                    st.error(f"Database security policy rejected deletion block: {str(ex_del)}")

        st.markdown("</div>", unsafe_allow_html=True)