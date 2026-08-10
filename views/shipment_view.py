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
    list_job_containers,
    add_job_container,
    delete_job_container,
    list_milestones,
    add_milestone,
    delete_milestone,
)
from managers.customer_manager import list_customers
from core.audit import log_action


# =========================================================
# GLOBAL CONSTANTS & HELPERS
# =========================================================
STATUS_OPTIONS = ["All"] + STATUS_FLOW


def _safe_date(val):
    """Parses date string or returns default date."""
    if not val:
        return None
    if isinstance(val, (date, datetime)):
        return val if isinstance(val, date) else val.date()
    try:
        return datetime.strptime(str(val)[:10], "%Y-%m-%d").date()
    except Exception:
        return None


# =========================================================
# RENDER PIPELINE ENTRYPOINT
# =========================================================
def render_job_ledger(jobs):
    if not jobs:
        st.info("No jobs found for the selected criteria.")
        return

    df = pd.DataFrame(jobs)
    
    # Select critical columns
    display_cols = [
        "job_no", "status", "job_type", "booking_no", "quotation_no",
        "customer_name", "pol", "pod", "vessel", "voyage", 
        "etd", "eta", "actual_departure", "actual_arrival"
    ]
    
    # Ensure all columns exist to prevent KeyError
    for col in display_cols:
        if col not in df.columns:
            df[col] = None
            
    df = df[display_cols].fillna("")
    
    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "job_no": "Job No",
            "status": "Status",
            "job_type": "Mode",
            "booking_no": "Booking No",
            "quotation_no": "Quotation No",
            "customer_name": "Customer",
            "pol": "POL",
            "pod": "POD",
            "etd": "ETD",
            "eta": "ETA",
            "actual_departure": "ATD",
            "actual_arrival": "ATA",
        }
    )

def render_container_tab(job, allow_edit):
    st.subheader("Containers")
    job_no = job['job_no']
    
    # List Existing
    containers = list_job_containers(job_no)
    if containers:
        df_c = pd.DataFrame(containers)
        df_c = df_c[['id', 'container_no', 'container_size', 'container_type', 'seal_no', 'vgm_kg', 'tare_weight', 'gross_weight', 'status']]
        st.dataframe(df_c, use_container_width=True, hide_index=True)
        
        if allow_edit:
            del_id = st.selectbox("Select Container to Delete", options=[c['id'] for c in containers], format_func=lambda x: next((c['container_no'] for c in containers if c['id'] == x), x))
            if st.button("Delete Container"):
                try:
                    delete_job_container(del_id, job_no)
                    st.success("Deleted!")
                    st.rerun()
                except Exception as e:
                    st.error(str(e))
    else:
        st.info("No containers attached.")
        
    # Add New
    if allow_edit:
        st.markdown("#### Add Container")
        with st.form("form_add_container"):
            c1, c2, c3 = st.columns(3)
            c_no = c1.text_input("Container No*")
            c_sz = c2.selectbox("Size", ["20GP", "40GP", "40HC", "45HC", "LCL"])
            c_ty = c3.selectbox("Type", ["GP", "HQ", "RF", "OT", "FR", "TK"])
            
            c4, c5, c6, c7 = st.columns(4)
            seal = c4.text_input("Seal No")
            vgm = c5.number_input("VGM (kg)", min_value=0.0, step=100.0)
            tare = c6.number_input("Tare Weight", min_value=0.0, step=100.0)
            gross = c7.number_input("Gross Weight", min_value=0.0, step=100.0)
            
            sub = st.form_submit_button("Add Container")
            if sub:
                try:
                    add_job_container({
                        "job_no": job_no,
                        "shipment_id": job['id'],
                        "container_no": c_no,
                        "container_size": c_sz,
                        "container_type": c_ty,
                        "seal_no": seal,
                        "vgm_kg": vgm,
                        "tare_weight": tare,
                        "gross_weight": gross
                    })
                    st.success("Container Added!")
                    st.rerun()
                except Exception as e:
                    st.error(str(e))

def render_milestone_tab(job, allow_edit):
    st.subheader("Milestones Timeline")
    job_no = job['job_no']
    
    milestones = list_milestones(job_no)
    if milestones:
        for m in milestones:
            st.markdown(f"**{m['event_date'][:16]}** | `{m['milestone_code']}` - {m['milestone_name']} (Loc: {m.get('location', '')})")
            if m.get('remark'):
                st.caption(f"Remark: {m['remark']}")
        
        if allow_edit:
            st.markdown("---")
            del_id = st.selectbox("Select Milestone to Delete", options=[m['id'] for m in milestones], format_func=lambda x: next((f"{m['milestone_code']} ({m['event_date'][:16]})" for m in milestones if m['id'] == x), x))
            if st.button("Delete Milestone"):
                try:
                    delete_milestone(del_id, job_no)
                    st.success("Deleted!")
                    st.rerun()
                except Exception as e:
                    st.error(str(e))
    else:
        st.info("No milestones recorded.")
        
    if allow_edit:
        st.markdown("#### Log New Milestone")
        with st.form("form_add_milestone"):
            c1, c2 = st.columns(2)
            m_code = c1.selectbox("Event Code", ["BOOKING_CONFIRMED", "GATE_IN", "LOADED", "DEPARTED", "ARRIVED", "GATE_OUT", "DELIVERED", "CUSTOMS_CLEARED", "OTHER"])
            m_name = c2.text_input("Event Name", value="Status Update")
            
            c3, c4 = st.columns(2)
            m_date = c3.date_input("Event Date", value=datetime.now().date())
            m_time = c4.time_input("Event Time", value=datetime.now().time())
            
            loc = st.text_input("Location")
            rem = st.text_area("Remark")
            
            sub = st.form_submit_button("Log Milestone")
            if sub:
                dt_str = f"{m_date} {m_time.strftime('%H:%M:%S')}"
                try:
                    add_milestone({
                        "job_no": job_no,
                        "shipment_id": job['id'],
                        "milestone_code": m_code,
                        "milestone_name": m_name,
                        "event_date": dt_str,
                        "location": loc,
                        "remark": rem,
                        "created_by": st.session_state.get("user", {}).get("username", "system")
                    })
                    st.success("Milestone Logged!")
                    st.rerun()
                except Exception as e:
                    st.error(str(e))

def render_job_workspace(job, can_edit):
    st.markdown(f"### Job Workspace: {job['job_no']} ({job['status']})")
    
    # Edit Lock Logic
    is_locked = job['status'] in ["Finished", "Closed", "Canceled"]
    allow_edit = can_edit and not is_locked
    
    if is_locked:
        st.warning(f"🔒 This Job is {job['status']} and is protected from routine operational edits.")
        
    t1, t2, t3, t4, t5, t6, t7, t8, t9 = st.tabs([
        "Overview", "Parties", "Routing", "Vessel/Voyage", 
        "Cargo", "Containers", "Milestones", "Documents", "Financials"
    ])
    
    with t1:
        st.subheader("Overview")
        with st.form("form_overview"):
            col1, col2 = st.columns(2)
            new_status = col1.selectbox("Status", options=STATUS_FLOW, index=STATUS_FLOW.index(job['status']) if job['status'] in STATUS_FLOW else 0, disabled=not can_edit)
            job_type = col2.selectbox("Job Type", options=list(JOB_TYPES.keys()), index=list(JOB_TYPES.keys()).index(job.get('job_type', 'SE')) if job.get('job_type') in JOB_TYPES else 0, disabled=not allow_edit)
            
            c3, c4 = st.columns(2)
            booking_no = c3.text_input("Booking No", value=job.get('booking_no', ''), disabled=True)
            quotation_no = c4.text_input("Quotation No", value=job.get('quotation_no', ''), disabled=True)
            
            sub = st.form_submit_button("Update Overview", disabled=not can_edit)
            if sub:
                try:
                    update_shipment(job['job_no'], {"status": new_status, "job_type": job_type})
                    st.success("Overview updated!")
                    st.rerun()
                except Exception as e:
                    st.error(str(e))
                    
    with t2:
        st.subheader("Parties")
        with st.form("form_parties"):
            c1, c2 = st.columns(2)
            customer = c1.text_input("Customer", value=job.get('customer_name', ''), disabled=not allow_edit)
            notify = c2.text_input("Notify Party", value=job.get('notify_party', ''), disabled=not allow_edit)
            
            c3, c4 = st.columns(2)
            shipper = c3.text_input("Shipper", value=job.get('shipper', ''), disabled=not allow_edit)
            consignee = c4.text_input("Consignee", value=job.get('consignee', ''), disabled=not allow_edit)
            
            sub = st.form_submit_button("Update Parties", disabled=not allow_edit)
            if sub:
                update_shipment(job['job_no'], {
                    "customer_name": customer, "notify_party": notify,
                    "shipper": shipper, "consignee": consignee
                })
                st.success("Parties updated!")
                st.rerun()
                
    with t3:
        st.subheader("Routing & Dates")
        with st.form("form_routing"):
            c1, c2 = st.columns(2)
            pol = c1.text_input("POL", value=job.get('pol', ''), disabled=not allow_edit)
            pod = c2.text_input("POD", value=job.get('pod', ''), disabled=not allow_edit)
            
            c3, c4 = st.columns(2)
            etd = c3.date_input("ETD (Planned)", value=_safe_date(job.get('etd')), disabled=not allow_edit)
            eta = c4.date_input("ETA (Planned)", value=_safe_date(job.get('eta')), disabled=not allow_edit)
            
            c5, c6 = st.columns(2)
            atd = c5.date_input("Actual Departure", value=_safe_date(job.get('actual_departure')), disabled=not can_edit)
            ata = c6.date_input("Actual Arrival", value=_safe_date(job.get('actual_arrival')), disabled=not can_edit)
            
            sub = st.form_submit_button("Update Routing", disabled=not can_edit)
            if sub:
                payload = {
                    "pol": pol, "pod": pod,
                    "etd": etd, "eta": eta,
                    "actual_departure": atd,
                    "actual_arrival": ata
                }
                try:
                    update_shipment(job['job_no'], payload)
                    st.success("Routing updated!")
                    st.rerun()
                except Exception as e:
                    st.error(str(e))
                
    with t4:
        st.subheader("Vessel / Voyage")
        with st.form("form_vessel"):
            c1, c2 = st.columns(2)
            vessel = c1.text_input("Vessel", value=job.get('vessel', ''), disabled=not allow_edit)
            voyage = c2.text_input("Voyage", value=job.get('voyage', ''), disabled=not allow_edit)
            carrier = st.text_input("Carrier", value=job.get('carrier', ''), disabled=not allow_edit)
            
            sub = st.form_submit_button("Update Vessel", disabled=not allow_edit)
            if sub:
                update_shipment(job['job_no'], {"vessel": vessel, "voyage": voyage, "carrier": carrier})
                st.success("Vessel updated!")
                st.rerun()
                
    with t5:
        st.subheader("Cargo")
        with st.form("form_cargo"):
            c1, c2, c3 = st.columns(3)
            gross = c1.number_input("Gross Weight", value=float(job.get('gross_weight') or 0.0), disabled=not allow_edit)
            cbm = c2.number_input("CBM", value=float(job.get('cbm') or 0.0), disabled=not allow_edit)
            qty = c3.number_input("Package Qty", value=int(job.get('package_quantity') or 0), disabled=not allow_edit)
            
            commodity = st.text_input("Commodity", value=job.get('commodity', ''), disabled=not allow_edit)
            
            sub = st.form_submit_button("Update Cargo", disabled=not allow_edit)
            if sub:
                update_shipment(job['job_no'], {"gross_weight": gross, "cbm": cbm, "package_quantity": qty, "commodity": commodity})
                st.success("Cargo updated!")
                st.rerun()
                
    with t6:
        render_container_tab(job, allow_edit)
    with t7:
        render_milestone_tab(job, allow_edit)
    with t8:
        st.info("🚧 Documents (B/L, etc.) will be implemented in a future phase.")
    with t9:
        st.info("🚧 Financials (AP/AR) will be implemented in a future phase.")

def render():
    user = st.session_state.get("user", {})
    role = str(user.get("role", "")).lower()
    can_edit = can_write(role, "shipment")

    st.markdown("<h2 style='margin-top: 0px; font-weight: 800;'>📦 Job Control Center</h2>", unsafe_allow_html=True)
    st.caption("Phase J2 - Operational CRUD and Job Ledger")

    # Load Jobs
    filter_status = st.selectbox("Filter Status", options=STATUS_OPTIONS, index=0)
    
    try:
        jobs = list_shipments(status=None if filter_status == "All" else filter_status)
    except Exception as e:
        jobs = []
        st.error(f"Failed to load jobs: {e}")

    render_job_ledger(jobs)

    st.markdown("---")
    
    if jobs:
        st.subheader("Job Detail Workspace")
        selected_job_no = st.selectbox("Select Job to Edit/View", options=[j['job_no'] for j in jobs])
        
        if selected_job_no:
            job_data = get_shipment(selected_job_no)
            if job_data:
                render_job_workspace(job_data, can_edit)
            else:
                st.error("Could not load job details.")