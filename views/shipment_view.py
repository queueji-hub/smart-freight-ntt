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
from managers.bl_manager import (
    BL_STATUS_FLOW,
    BL_TYPES,
    LOCKED_STATUSES,
    create_bl,
    get_bl,
    list_bls,
    update_bl,
    update_bl_status,
    delete_bl,
    list_bl_containers,
    add_bl_container,
    remove_bl_container,
    can_transition_bl_status,
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


def _s(val, default=""):
    """NULL-safe string. Never returns literal 'None'."""
    if val is None:
        return default
    v = str(val).strip()
    return v if v and v.lower() != "none" else default


def render_bl_tab(job, allow_edit):
    """J4: Bill of Lading Data Module — B/L Ledger + Workspace + Container Mapping."""
    st.subheader("Bill of Lading Documents")
    job_no = job["job_no"]
    user = st.session_state.get("user", {})

    # --- B/L LEDGER ---
    bls = list_bls(job_no)
    if bls:
        ledger_rows = []
        for b in bls:
            ledger_rows.append({
                "ID":        b.get("id"),
                "B/L No":    _s(b.get("bl_no"), "—"),
                "Type":      _s(b.get("bl_type"), "—"),
                "Status":    _s(b.get("status"), "Draft"),
                "Shipper":   _s(b.get("shipper"), "—"),
                "Consignee": _s(b.get("consignee"), "—"),
                "POL":       _s(b.get("port_of_loading"), "—"),
                "POD":       _s(b.get("port_of_discharge"), "—"),
                "Vessel":    _s(b.get("vessel"), "—"),
                "Voyage":    _s(b.get("voyage"), "—"),
            })
        df_bl = pd.DataFrame(ledger_rows)
        st.dataframe(df_bl, use_container_width=True, hide_index=True)
    else:
        st.info("No B/L documents for this Job yet.")

    if allow_edit:
        st.markdown("#### Create New B/L from Job")
        with st.form("form_create_bl"):
            bl_type = st.selectbox("B/L Type", list(BL_TYPES))
            sub_create = st.form_submit_button("Create B/L (prefill from Job)")
            if sub_create:
                try:
                    new_id = create_bl(job_no, bl_type, user)
                    st.success(f"B/L created (id={new_id})")
                    st.rerun()
                except Exception as e:
                    st.error(str(e))

    # --- B/L WORKSPACE (select one) ---
    if not bls:
        return

    bl_options = {b["id"]: f"{_s(b.get('bl_no'))} [{_s(b.get('bl_type'))}] — {_s(b.get('status'))}" for b in bls}
    selected_bl_id = st.selectbox(
        "Select B/L to View / Edit",
        options=list(bl_options.keys()),
        format_func=lambda x: bl_options[x]
    )
    if not selected_bl_id:
        return

    bl = get_bl(selected_bl_id)
    if not bl:
        st.error("Could not load B/L record.")
        return

    bl_status = _s(bl.get("status"), "Draft")
    bl_locked = bl_status in LOCKED_STATUSES
    can_edit_bl = allow_edit and not bl_locked

    if bl_locked:
        st.warning(f"This B/L is **{bl_status}** and is locked from edits.")
    else:
        st.info(f"B/L Status: **{bl_status}**")

    # --- STATUS ACTIONS ---
    next_statuses = BL_STATUS_FLOW.get(bl_status, [])
    if can_edit_bl and next_statuses:
        action_cols = st.columns(len(next_statuses))
        for idx, ns in enumerate(next_statuses):
            with action_cols[idx]:
                if st.button(f"→ {ns}", key=f"bl_status_{selected_bl_id}_{ns}"):
                    try:
                        update_bl_status(selected_bl_id, ns)
                        st.success(f"B/L status changed to {ns}")
                        st.rerun()
                    except Exception as e:
                        st.error(str(e))

    # Delete button (Draft only)
    if can_edit_bl and bl_status == "Draft":
        if st.button("Delete This B/L (Draft only)", key=f"del_bl_{selected_bl_id}"):
            try:
                delete_bl(selected_bl_id)
                st.success("B/L deleted.")
                st.rerun()
    # --- PDF DOWNLOAD ACTION ---
    try:
        from pdf.bl_pdf import generate_bl_pdf
        pdf_path = generate_bl_pdf(selected_bl_id)
        if pdf_path and os.path.exists(pdf_path):
            with open(pdf_path, "rb") as pdf_file:
                st.download_button(
                    label=f"📥 Download {bl.get('bl_type', 'B/L')} PDF ({bl.get('bl_no', '')})",
                    data=pdf_file.read(),
                    file_name=os.path.basename(pdf_path),
                    mime="application/pdf",
                    key=f"dl_bl_pdf_{selected_bl_id}",
                    use_container_width=True,
                    type="primary"
                )
    except Exception as pdf_err:
        st.error(f"B/L PDF Compiler Warning: {pdf_err}")

    st.markdown("---")

    # --- B/L EDIT FORM ---
    with st.expander("Document Details", expanded=True):
        with st.form(f"form_edit_bl_{selected_bl_id}"):
            c1, c2, c3 = st.columns(3)
            bl_date  = c1.date_input("B/L Date",       value=_safe_date(bl.get("bl_date")),       disabled=not can_edit_bl)
            bl_place = c2.text_input("Place of Issue",  value=_s(bl.get("place_of_issue")),         disabled=not can_edit_bl)
            bl_orig  = c3.text_input("No. of Originals",value=_s(bl.get("number_of_originals")),   disabled=not can_edit_bl)

            st.markdown("**Parties**")
            shipper    = st.text_input("Shipper",      value=_s(bl.get("shipper")),      disabled=not can_edit_bl)
            consignee  = st.text_input("Consignee",    value=_s(bl.get("consignee")),    disabled=not can_edit_bl)
            notify     = st.text_input("Notify Party", value=_s(bl.get("notify_party")), disabled=not can_edit_bl)

            st.markdown("**Routing**")
            r1, r2 = st.columns(2)
            por = r1.text_input("Place of Receipt",    value=_s(bl.get("place_of_receipt")),  disabled=not can_edit_bl)
            pol = r2.text_input("Port of Loading",     value=_s(bl.get("port_of_loading")),   disabled=not can_edit_bl)
            r3, r4 = st.columns(2)
            pod = r3.text_input("Port of Discharge",   value=_s(bl.get("port_of_discharge")), disabled=not can_edit_bl)
            pde = r4.text_input("Place of Delivery",   value=_s(bl.get("place_of_delivery")), disabled=not can_edit_bl)
            fds = st.text_input("Final Destination",   value=_s(bl.get("final_destination")), disabled=not can_edit_bl)

            st.markdown("**Vessel / Voyage**")
            v1, v2 = st.columns(2)
            vessel = v1.text_input("Vessel", value=_s(bl.get("vessel")), disabled=not can_edit_bl)
            voyage = v2.text_input("Voyage", value=_s(bl.get("voyage")), disabled=not can_edit_bl)

            st.markdown("**Freight**")
            f1, f2 = st.columns(2)
            fterm = f1.text_input("Freight Term",       value=_s(bl.get("freight_term")),       disabled=not can_edit_bl)
            fpay  = f2.text_input("Freight Payable At", value=_s(bl.get("freight_payable_at")), disabled=not can_edit_bl)

            st.markdown("**Cargo**")
            g1, g2, g3 = st.columns(3)
            pkg_qty = g1.number_input("Package Qty", value=max(0, int(bl.get("package_qty") or 0)),
                                      step=1, min_value=0, disabled=not can_edit_bl)
            gw  = g2.number_input("Gross Weight (kg)", value=max(0.0, float(bl.get("gross_weight") or 0.0)),
                                   step=0.01, disabled=not can_edit_bl)
            cbm = g3.number_input("Measurement (CBM)",  value=max(0.0, float(bl.get("measurement_cbm") or 0.0)),
                                   step=0.001, disabled=not can_edit_bl)

            pkg_type = st.text_input("Package Type",        value=_s(bl.get("package_type")),        disabled=not can_edit_bl)
            goods    = st.text_area("Description of Goods", value=_s(bl.get("description_of_goods")), disabled=not can_edit_bl)
            marks    = st.text_area("Marks & Numbers",      value=_s(bl.get("marks_numbers")),        disabled=not can_edit_bl)
            hs       = st.text_input("HS Code",             value=_s(bl.get("hs_code")),              disabled=not can_edit_bl)

            st.markdown("**Remarks**")
            remarks = st.text_area("Remarks",              value=_s(bl.get("remarks")),              disabled=not can_edit_bl)
            special = st.text_area("Special Instructions", value=_s(bl.get("special_instructions")), disabled=not can_edit_bl)

            sub_edit = st.form_submit_button("Save B/L", disabled=not can_edit_bl)
            if sub_edit:
                try:
                    update_bl(selected_bl_id, {
                        "bl_date": bl_date, "place_of_issue": bl_place, "number_of_originals": bl_orig,
                        "shipper": shipper, "consignee": consignee, "notify_party": notify,
                        "place_of_receipt": por, "port_of_loading": pol,
                        "port_of_discharge": pod, "place_of_delivery": pde, "final_destination": fds,
                        "vessel": vessel, "voyage": voyage,
                        "freight_term": fterm, "freight_payable_at": fpay,
                        "package_qty": pkg_qty, "gross_weight": gw, "measurement_cbm": cbm,
                        "package_type": pkg_type, "description_of_goods": goods,
                        "marks_numbers": marks, "hs_code": hs,
                        "remarks": remarks, "special_instructions": special,
                    })
                    st.success("B/L saved!")
                    st.rerun()
                except Exception as e:
                    st.error(str(e))

    # --- CONTAINER MAPPING ---
    with st.expander("Container Mapping", expanded=False):
        st.caption("Link existing Job containers to this B/L. Editing mappings does NOT modify the container records.")

        # Containers linked to this B/L
        linked = list_bl_containers(selected_bl_id)
        linked_ids = {c["id"] for c in linked}

        if linked:
            st.markdown("**Linked Containers:**")
            df_linked = pd.DataFrame([{
                "Container No": _s(c.get("container_no"), "—"),
                "Size":         _s(c.get("container_size"), "—"),
                "Type":         _s(c.get("container_type"), "—"),
                "Seal":         _s(c.get("seal_no"), "—"),
                "VGM":          c.get("vgm_kg", 0),
                "Junct.ID":     c.get("junction_id"),
                "Cont.ID":      c.get("id"),
            } for c in linked])
            st.dataframe(df_linked, use_container_width=True, hide_index=True)

            if can_edit_bl:
                unlink_id = st.selectbox(
                    "Select container to unlink",
                    options=[c["id"] for c in linked],
                    format_func=lambda x: next((_s(c.get("container_no")) for c in linked if c["id"] == x), str(x)),
                    key=f"unlink_sel_{selected_bl_id}"
                )
                if st.button("Unlink Container", key=f"unlink_btn_{selected_bl_id}"):
                    try:
                        remove_bl_container(selected_bl_id, unlink_id)
                        st.success("Container unlinked.")
                        st.rerun()
                    except Exception as e:
                        st.error(str(e))
        else:
            st.info("No containers linked to this B/L.")

        if can_edit_bl:
            # Show all Job containers not yet linked
            job_ctrs = list_job_containers(job_no)
            available = [c for c in job_ctrs if c["id"] not in linked_ids]
            if available:
                st.markdown("**Available Job Containers (select to link):**")
                link_id = st.selectbox(
                    "Select container to link",
                    options=[c["id"] for c in available],
                    format_func=lambda x: next((_s(c.get("container_no")) for c in available if c["id"] == x), str(x)),
                    key=f"link_sel_{selected_bl_id}"
                )
                if st.button("Link Container to B/L", key=f"link_btn_{selected_bl_id}"):
                    try:
                        add_bl_container(selected_bl_id, link_id)
                        st.success("Container linked!")
                        st.rerun()
                    except Exception as e:
                        st.error(str(e))
            else:
                st.info("All Job containers are already linked, or no containers exist on this Job.")


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
        render_bl_tab(job, allow_edit)
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