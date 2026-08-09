"""
Shipment Operations & Job Pipe Management Workspace
PostgreSQL Connected - 100% Professional ERP Grade Interface
"""

from datetime import date, datetime
import pandas as pd
import streamlit as st

from config import JOB_TYPES, CARGO_TYPES
from managers.auth_manager import can_write
from managers.shipment_manager import (
    create_shipment,
    delete_shipment,
    get_dashboard_stats,
    get_shipment,
    list_shipments,
    update_shipment,
    STATUS_FLOW,
)
from core.audit import log_action


# =========================================================
# GLOBAL CONSTANTS & HELPERS
# =========================================================
STATUS_OPTIONS = ["All"] + STATUS_FLOW


def _safe_date(val):
    """Parses date string or returns default date."""
    if not val:
        return date.today()
    if isinstance(val, (date, datetime)):
        return val if isinstance(val, date) else val.date()
    try:
        return datetime.strptime(str(val)[:10], "%Y-%m-%d").date()
    except Exception:
        return date.today()


# =========================================================
# RENDER PIPELINE ENTRYPOINT
# =========================================================
def render():
    user = st.session_state.get("user", {})
    role = str(user.get("role", "")).lower()
    can_edit = can_write(role, "shipment")

    st.markdown(
        "<p style='color: #38BDF8; font-weight: 700; font-size: 13px; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 2px;'>Supply Chain Infrastructure</p>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<h2 style='margin-top: 0px; font-weight: 800; color:#F8FAFC;'>📦 Shipment Operations (Job Pipeline)</h2>",
        unsafe_allow_html=True,
    )
    st.caption(
        "Manage real-time intermodal freight movements, track container milestones, update job lifecycles, and monitor cargo logistics statuses."
    )

    # ---------------------------------------------------------
    # 1. EXECUTIVE KPI SUMMARY METRICS
    # ---------------------------------------------------------
    try:
        stats = get_dashboard_stats() or {}
    except Exception as e:
        stats = {}
        st.warning(f"⚠️ Could not load KPI statistics: {str(e)}")

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Total Jobs Logged", f"{stats.get('total', 0):,}")
    c2.metric("Active (Proceed)", f"{stats.get('proceed', 0):,}")
    c3.metric("Completed (Finished)", f"{stats.get('finished', 0):,}")
    c4.metric("Closed Jobs", f"{stats.get('closed', 0):,}")
    c5.metric("Canceled Jobs", f"{stats.get('canceled', 0):,}")

    st.markdown("---")

    # ---------------------------------------------------------
    # 2. CREATE NEW SHIPMENT / JOB ACTION
    # ---------------------------------------------------------
    if can_edit:
        with st.expander("➕ Create New Freight Shipment (Job Entry)", expanded=False):
            with st.form("create_shipment_form"):
                col1, col2, col3 = st.columns(3)

                job_type = col1.selectbox("Job Mode *", options=list(JOB_TYPES.keys()), format_func=lambda x: f"{x} - {JOB_TYPES[x]}")
                customer_name = col2.text_input("Customer / Corporate Account Name *", placeholder="e.g. Siam Implement Co., Ltd.")
                booking_no = col3.text_input("Booking Reference No", placeholder="e.g. BK-2026-0801")

                col4, col5 = st.columns(2)
                shipper = col4.text_input("Shipper Name & Origin Contact", placeholder="e.g. Nattayaraat Co., Ltd.")
                consignee = col5.text_input("Consignee Name & Destination Contact", placeholder="e.g. Overseas Trading Corp.")

                col6, col7, col8 = st.columns(3)
                cargo_type = col6.selectbox("Cargo Category", options=CARGO_TYPES)
                carrier = col7.text_input("Carrier / Shipping Line", placeholder="e.g. ONE Line / Evergreen")
                bl_no = col8.text_input("Bill of Lading (BL) No", placeholder="e.g. ONEYBKKGT1413800")

                col9, col10, col11, col12 = st.columns(4)
                pol = col9.text_input("Port of Loading (POL)", placeholder="e.g. Laem Chabang (THLCH)")
                pod = col10.text_input("Port of Discharge (POD)", placeholder="e.g. Ho Chi Minh (VNSGN)")
                etd = col11.date_input("Estimated Time of Departure (ETD)", value=date.today())
                eta = col12.date_input("Estimated Time of Arrival (ETA)", value=date.today())

                remark = st.text_area("Operational Remarks / Notes", placeholder="Special handling requirements, temperature specs, etc.")

                submit = st.form_submit_button("🚀 Submit & Register Shipment", use_container_width=True, type="primary")

                if submit:
                    if not customer_name.strip():
                        st.error("⚠️ Customer Name is required.")
                    else:
                        payload = {
                            "job_type": job_type,
                            "booking_no": booking_no.strip(),
                            "customer_name": customer_name.strip(),
                            "shipper": shipper.strip(),
                            "consignee": consignee.strip(),
                            "cargo_type": cargo_type,
                            "carrier": carrier.strip(),
                            "bl_no": bl_no.strip(),
                            "pol": pol.strip(),
                            "pod": pod.strip(),
                            "etd": str(etd),
                            "eta": str(eta),
                            "remark": remark.strip(),
                            "status": "Proceed",
                            "created_by": str(user.get("username", "operator")),
                        }
                        try:
                            new_job_no = create_shipment(payload)
                            log_action(
                                user_id=user.get("id", 0),
                                tenant_id="default",
                                entity="shipment",
                                entity_id=new_job_no,
                                action="CREATE",
                                details=f"Created shipment {new_job_no} for {customer_name}"
                            )
                            st.toast(f"✅ Shipment {new_job_no} registered successfully!", icon="📦")
                            st.rerun()
                        except Exception as create_err:
                            st.error(f"🚨 Failed to create shipment: {str(create_err)}")

    # ---------------------------------------------------------
    # 3. FILTER & SEARCH REGISTRY
    # ---------------------------------------------------------
    st.markdown("### 📋 Active Shipment Registry")
    f_col1, f_col2, f_col3 = st.columns([2, 1, 1])

    search_query = f_col1.text_input("🔍 Quick Search (Job No, Customer, BL No, Carrier)", placeholder="Type to filter...")
    status_filter = f_col2.selectbox("Filter Status", options=STATUS_OPTIONS)
    job_type_filter = f_col3.selectbox("Filter Job Mode", options=["All"] + list(JOB_TYPES.keys()))

    # Fetch shipments from database
    try:
        status_param = None if status_filter == "All" else status_filter
        shipments = list_shipments(status=status_param, limit=300) or []
    except Exception as fetch_err:
        st.error(f"Failed to extract shipment registry: {str(fetch_err)}")
        shipments = []

    # Client-side filtering
    filtered_ships = shipments
    if job_type_filter != "All":
        filtered_ships = [s for s in filtered_ships if s.get("job_type") == job_type_filter]

    if search_query.strip():
        sq = search_query.strip().lower()
        filtered_ships = [
            s for s in filtered_ships
            if sq in str(s.get("job_no", "")).lower()
            or sq in str(s.get("customer_name", "")).lower()
            or sq in str(s.get("bl_no", "")).lower()
            or sq in str(s.get("carrier", "")).lower()
            or sq in str(s.get("pol", "")).lower()
            or sq in str(s.get("pod", "")).lower()
        ]

    if not filtered_ships:
        st.info("ℹ️ No shipment operations match the active search criteria.")
        return

    # Render DataFrame Table
    df = pd.DataFrame(filtered_ships)
    cols_display = [c for c in ["job_no", "status", "job_type", "customer_name", "carrier", "pol", "pod", "etd", "eta", "bl_no"] if c in df.columns]

    column_config = {
        "job_no": st.column_config.TextColumn("Job Number", width="medium"),
        "status": st.column_config.TextColumn("Status", width="small"),
        "job_type": st.column_config.TextColumn("Mode", width="small"),
        "customer_name": st.column_config.TextColumn("Customer", width="medium"),
        "carrier": st.column_config.TextColumn("Carrier", width="small"),
        "pol": st.column_config.TextColumn("POL", width="small"),
        "pod": st.column_config.TextColumn("POD", width="small"),
        "etd": st.column_config.DateColumn("ETD", format="YYYY-MM-DD"),
        "eta": st.column_config.DateColumn("ETA", format="YYYY-MM-DD"),
        "bl_no": st.column_config.TextColumn("BL No", width="small"),
    }

    st.dataframe(df[cols_display], use_container_width=True, hide_index=True, column_config=column_config)

    # ---------------------------------------------------------
    # 4. SHIPMENT WORKFLOW ACTIONS & STATUS UPDATES
    # ---------------------------------------------------------
    st.markdown("---")
    st.markdown("### ⚙️ Shipment Lifecycle Actions")

    ship_map = {f"📦 {s['job_no']} — {s.get('customer_name', 'Customer')} ({s.get('status', 'Proceed')})": s for s in filtered_ships}
    selected_label = st.selectbox("Select Target Shipment Job", list(ship_map.keys()), key="shipment_action_selector")
    target_shipment = ship_map[selected_label]

    tab_status, tab_edit, tab_delete = st.tabs(["🔄 Update Lifecycle Status", "✏️ Edit Details", "🗑️ Prune Job"])

    with tab_status:
        st.markdown(f"Current Status of **{target_shipment['job_no']}**: `{target_shipment.get('status', 'Proceed')}`")
        new_status = st.selectbox(
            "Select New Status Transition",
            options=STATUS_FLOW,
            index=STATUS_FLOW.index(target_shipment.get("status", "Proceed")) if target_shipment.get("status") in STATUS_FLOW else 0,
            key=f"status_select_{target_shipment['job_no']}"
        )
        status_remark = st.text_input("Status Update Note / Log", key=f"status_note_{target_shipment['job_no']}")

        if st.button("Update Status Lifecycle", type="primary", use_container_width=True):
            if can_edit:
                try:
                    update_shipment(target_shipment["job_no"], {
                        "status": new_status,
                        "remark": f"{target_shipment.get('remark','')}\n[{datetime.now().strftime('%Y-%m-%d %H:%M')}] Status -> {new_status}: {status_remark}".strip(),
                        "updated_by": str(user.get("username", "operator"))
                    })
                    log_action(
                        user_id=user.get("id", 0),
                        tenant_id="default",
                        entity="shipment",
                        entity_id=target_shipment["job_no"],
                        action="UPDATE_STATUS",
                        details=f"Updated status to {new_status}"
                    )
                    st.toast(f"✅ Status updated to {new_status}", icon="🔄")
                    st.rerun()
                except Exception as update_err:
                    st.error(f"Failed to update shipment status: {str(update_err)}")
            else:
                st.error("🔒 Access Denied: Your account role does not have permission to modify shipment operations.")

    with tab_edit:
        if not can_edit:
            st.warning("🔒 Edit permission required.")
        else:
            with st.form(f"edit_shipment_form_{target_shipment['job_no']}"):
                ec1, ec2, ec3 = st.columns(3)
                edit_cust = ec1.text_input("Customer Name", value=target_shipment.get("customer_name", ""))
                edit_carrier = ec2.text_input("Carrier / Line", value=target_shipment.get("carrier", ""))
                edit_bl = ec3.text_input("BL Number", value=target_shipment.get("bl_no", ""))

                ec4, ec5, ec6, ec7 = st.columns(4)
                edit_pol = ec4.text_input("POL", value=target_shipment.get("pol", ""))
                edit_pod = ec5.text_input("POD", value=target_shipment.get("pod", ""))
                edit_etd = ec6.date_input("ETD", value=_safe_date(target_shipment.get("etd")))
                edit_eta = ec7.date_input("ETA", value=_safe_date(target_shipment.get("eta")))

                edit_shipper = st.text_input("Shipper", value=target_shipment.get("shipper", ""))
                edit_consignee = st.text_input("Consignee", value=target_shipment.get("consignee", ""))
                edit_remark = st.text_area("Remarks", value=target_shipment.get("remark", ""))

                save_edit = st.form_submit_button("💾 Save Operational Modifications", use_container_width=True)

                if save_edit:
                    patch = {
                        "customer_name": edit_cust.strip(),
                        "carrier": edit_carrier.strip(),
                        "bl_no": edit_bl.strip(),
                        "pol": edit_pol.strip(),
                        "pod": edit_pod.strip(),
                        "etd": str(edit_etd),
                        "eta": str(edit_eta),
                        "shipper": edit_shipper.strip(),
                        "consignee": edit_consignee.strip(),
                        "remark": edit_remark.strip(),
                        "updated_by": str(user.get("username", "operator"))
                    }
                    try:
                        update_shipment(target_shipment["job_no"], patch)
                        log_action(
                            user_id=user.get("id", 0),
                            tenant_id="default",
                            entity="shipment",
                            entity_id=target_shipment["job_no"],
                            action="UPDATE",
                            details="Edited shipment details"
                        )
                        st.toast("✅ Shipment modifications saved!", icon="💾")
                        st.rerun()
                    except Exception as save_err:
                        st.error(f"Failed to save modifications: {str(save_err)}")

    with tab_delete:
        if not can_edit:
            st.warning("🔒 Delete permission required.")
        else:
            st.error(f"⚠️ CAUTION: Deleting `{target_shipment['job_no']}` is permanent!")
            confirm_del = st.checkbox(f"Confirm deletion of job {target_shipment['job_no']}", key=f"confirm_del_{target_shipment['job_no']}")
            if st.button("🗑️ Permanently Delete Shipment Record", type="primary", disabled=not confirm_del):
                try:
                    delete_shipment(target_shipment["job_no"])
                    log_action(
                        user_id=user.get("id", 0),
                        tenant_id="default",
                        entity="shipment",
                        entity_id=target_shipment["job_no"],
                        action="DELETE",
                        details=f"Deleted shipment {target_shipment['job_no']}"
                    )
                    st.toast(f"🗑️ Shipment {target_shipment['job_no']} deleted.", icon="🗑️")
                    st.rerun()
                except Exception as del_err:
                    st.error(f"Failed to delete shipment: {str(del_err)}")