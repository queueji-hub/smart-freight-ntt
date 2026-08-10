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
STATUS_OPTIONS = ["DRAFT", "SUBMITTED", "CONFIRMED", "CONVERTED TO JOB", "CANCELLED"]


# =========================================================
# PERFORMANCE & DATA INTELLIGENCE LAYER
# =========================================================
def get_bookings(tenant_id="default", status=None):
    """Fetches transactional booking registries matching optional status filter."""
    try:
        return list_bookings(tenant_id=tenant_id, status=status) or []
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
            quotations = list_quotations() or []
            q_options = ["-- Select Target Reference --"] + [str(q["quotation_no"]) for q in quotations if "quotation_no" in q]
        except Exception as e:
            st.warning(f"Unable to read quotations: {str(e)}")
            q_options = ["-- Select Target Reference --"]

        selected_q = st.selectbox(
            "Target Quotation No",
            options=q_options,
            key="booking_creation_quotation_selector"
        )

        if selected_q and selected_q != "-- Select Target Reference --":
            if st.button("⚡ Autopopulate from Quotation", key="booking_creation_pull_data_trigger", type="secondary", use_container_width=True):
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
        
        with st.form(key="booking_creation_form"):
            st.markdown("#### 1. Parties")
            c1, c2, c3, c4 = st.columns(4)
            with c1:
                job_type = st.selectbox(
                    "Job Type *", 
                    options=list(JOB_TYPES.keys()), 
                    format_func=lambda x: JOB_TYPES.get(x, x),
                    index=list(JOB_TYPES.keys()).index(pre.get("job_type", "SE")) if pre.get("job_type", "SE") in JOB_TYPES else 0
                )
                customer_name = st.text_input("Customer Name *", value=str(pre.get("customer_name", "")))
            with c2:
                shipper = st.text_input("Shipper", value=str(pre.get("shipper", "")))
            with c3:
                consignee = st.text_input("Consignee", value=str(pre.get("consignee", "")))
            with c4:
                notify_party = st.text_input("Notify Party", value=str(pre.get("notify_party", "")))

            st.markdown("#### 2. Routing")
            r1, r2, r3, r4, r5 = st.columns(5)
            with r1:
                por = st.text_input("POR (Receipt)", value=str(pre.get("por", "")))
            with r2:
                pol = st.text_input("POL (Load)", value=str(pre.get("pol", "")))
            with r3:
                transhipment_port = st.text_input("Transhipment", value=str(pre.get("transhipment_port", "")))
            with r4:
                pod = st.text_input("POD (Discharge)", value=str(pre.get("pod", "")))
            with r5:
                final_destination = st.text_input("Final Destination", value=str(pre.get("final_destination", "")))

            st.markdown("#### 3. Vessel / Flight Details")
            v1, v2, v3, v4 = st.columns(4)
            with v1:
                carrier = st.text_input("Carrier", value=str(pre.get("carrier", "")))
                liner = st.text_input("Liner", value=str(pre.get("liner", "")))
            with v2:
                vessel = st.text_input("Vessel", value=str(pre.get("vessel", "")))
                voyage = st.text_input("Voyage", value=str(pre.get("voyage", "")))
            with v3:
                m_vessel = st.text_input("Mother Vessel", value=str(pre.get("m_vessel", "")))
                feeder = st.text_input("Feeder", value=str(pre.get("feeder", "")))
            with v4:
                pre_etd = _parse_date(pre.get("etd")) if "etd" in pre else date.today()
                pre_eta = _parse_date(pre.get("eta")) if "eta" in pre else (date.today() + pd.Timedelta(days=14))
                etd = st.date_input("ETD *", value=pre_etd)
                eta = st.date_input("ETA *", value=pre_eta)

            st.markdown("#### 4. Cut-Offs & Terminals")
            t1, t2, t3, t4 = st.columns(4)
            with t1:
                cy_date = st.date_input("CY Date", value=_parse_date(pre.get("cy_date")) if pre.get("cy_date") else None)
                cy_place = st.text_input("CY Place", value=str(pre.get("cy_place", "")))
            with t2:
                cfs_date = st.date_input("CFS Date", value=_parse_date(pre.get("cfs_date")) if pre.get("cfs_date") else None)
                cfs_place = st.text_input("CFS Place", value=str(pre.get("cfs_place", "")))
            with t3:
                customer_return_date = st.date_input("Return Date", value=_parse_date(pre.get("customer_return_date")) if pre.get("customer_return_date") else None)
                return_place = st.text_input("Return Place", value=str(pre.get("return_place", "")))
            with t4:
                closing_time_str = str(pre.get("closing_time", ""))
                closing_time = st.text_input("Closing Time (Text/Time)", value=closing_time_str)

            st.markdown("#### 5. Cargo & Containers")
            g1, g2, g3, g4 = st.columns(4)
            with g1:
                cargo_type = st.selectbox("Cargo Type", options=CARGO_TYPES, index=CARGO_TYPES.index(pre.get("cargo_type", "")) if pre.get("cargo_type") in CARGO_TYPES else 0)
                commodity = st.text_input("Commodity", value=str(pre.get("commodity", "")))
            with g2:
                gross_weight = st.number_input("Gross Weight (KG)", value=float(pre.get("gross_weight") or pre.get("weight_kg") or 0.0))
                measurement_cbm = st.number_input("Measurement (CBM)", value=float(pre.get("measurement_cbm") or pre.get("volume_cbm") or 0.0))
            with g3:
                package_qty = st.number_input("Package Qty", value=int(pre.get("package_qty") or 0), step=1)
                package_unit = st.text_input("Package Unit", value=str(pre.get("package_unit", "PKGS")))
            with g4:
                # Quotation container requirements mapped to container summary
                default_cnt = ""
                if pre.get("container_type") and pre.get("container_quantity"):
                    default_cnt = f"{pre['container_quantity']}x {pre['container_type']}"
                container_summary = st.text_input("Container Summary (e.g. 2x 40HC)", value=str(pre.get("container_summary") or default_cnt))
                freight_term = st.selectbox("Freight Term", options=["", "PREPAID", "COLLECT"], index=["", "PREPAID", "COLLECT"].index(pre.get("freight_term")) if pre.get("freight_term") in ["", "PREPAID", "COLLECT"] else 0)

            st.markdown("#### 6. Additional")
            remark = st.text_area("Remark", value=str(pre.get("remark", "")))

            submit_btn = st.form_submit_button("🚀 Finalize and Commit Booking", type="primary", use_container_width=True)

    # --- TRANSACTIONAL PERSISTENCE EXECUTION ---
    if submit_btn:
        errors = []
        if not customer_name.strip():
            errors.append("Customer Name is required.")
        if etd and eta and eta < etd:
            errors.append("ETA cannot be before ETD.")
            
        if gross_weight < 0: errors.append("Gross Weight cannot be negative.")
        if measurement_cbm < 0: errors.append("Measurement CBM cannot be negative.")
        if package_qty < 0: errors.append("Package Quantity cannot be negative.")
            
        if job_type in ["SE", "SI"]: # SEA
            if not pol.strip(): errors.append("POL is required for Sea Freight.")
            if not pod.strip(): errors.append("POD is required for Sea Freight.")
            if cargo_type == "FCL" and not container_summary.strip():
                errors.append("Container Summary is required for FCL (e.g. 1x 20GP).")
            if cargo_type == "LCL" and not cfs_date:
                errors.append("CFS Date is required for LCL.")
        elif job_type in ["AE", "AI"]: # AIR
            if not pol.strip(): errors.append("Origin Airport (POL) is required for Air Freight.")
            if not pod.strip(): errors.append("Destination Airport (POD) is required for Air Freight.")
        elif job_type == "TR": # TRUCKING
            if not pol.strip(): errors.append("Origin (POL) is required for Trucking.")
            if not pod.strip(): errors.append("Destination (POD) is required for Trucking.")

        if errors:
            for err in errors:
                st.error(f"⚠️ Validation Failure: {err}")
            return

        with st.spinner("Committing secure operational entry transaction..."):
            try:
                payload = {
                    "quotation_id": pre.get("id"),
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
                    "created_by": str(user.get("username", "system_actor"))
                }

                booking_no = create_booking(payload, user)

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

    with st.spinner("Loading database..."):
        filter_param = None if status_filter == "All Profiles" else status_filter
        rows = get_bookings(tenant_id, filter_param)

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
    st.markdown("<h4 style='font-size:16px; color:#F1F5F9; font-weight:700;'>✏️ Modify Existing Booking</h4>", unsafe_allow_html=True)

    rows = get_bookings(tenant_id)
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
                    from managers.booking_manager import update_booking
                    update_booking(
                        selected["booking_no"],
                        {
                            "status": status,
                            "remark": remark.strip()
                        },
                        tenant_id
                    )
                    st.success(f"✅ Update successfully committed for Index: {selected['booking_no']}")
                    st.rerun()
                except Exception as update_err:
                    st.error(f"🚨 Mutation Engine Failure: {str(update_err)}")
        
        if delete_triggered:
            with st.spinner("Executing secure destructive sequence..."):
                try:
                    from managers.booking_manager import delete_booking
                    if delete_booking(selected["booking_no"], tenant_id):
                        st.warning(f"✅ Deleted Index: {selected['booking_no']}")
                        st.rerun()
                    else:
                        st.error("🚨 Purge failed: Ledger row inaccessible.")
                except Exception as del_err:
                    st.error(f"🚨 Purge System Failure: {str(del_err)}")

        st.markdown("---")
        st.markdown("#### 🚀 Operational Hand-off")
        
        if current_status == "CONFIRMED":
            if st.button("🔄 Convert to Job (Shipment)", type="primary", use_container_width=True, key=f"convert_job_{selected_no}"):
                with st.spinner("Translating Booking into Job..."):
                    try:
                        from managers.booking_manager import convert_booking_to_job
                        new_job = convert_booking_to_job(selected_no, st.session_state.get("user", {"tenant_id": tenant_id}))
                        st.success(f"✅ Successfully converted to Job: {new_job}")
                        st.balloons()
                        st.rerun()
                    except Exception as e:
                        st.error(f"🚨 Conversion Failed: {str(e)}")
        elif current_status == "CONVERTED TO JOB":
            st.info("ℹ️ This booking has already been converted to an active Job.")
        else:
            st.info("ℹ️ Booking must be in CONFIRMED status to convert into an active Job.")

        st.markdown("</div>", unsafe_allow_html=True)