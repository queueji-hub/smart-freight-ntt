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

    # Fetch Customers for dropdowns
    try:
        customers = list_customers()
        cust_options = {c["id"]: c["company_name"] for c in customers}
    except Exception:
        cust_options = {}

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
                
                t1, t2, t3, t4 = st.tabs(["📋 General", "🗺️ Routing", "📦 Cargo & Weight", "🏢 Customs"])
                
                with t1:
                    st.subheader("Job Details")
                    col1, col2, col3 = st.columns(3)
                    job_type = col1.selectbox("Job Mode *", options=list(JOB_TYPES.keys()), format_func=lambda x: f"{x} - {JOB_TYPES[x]}")
                    customer_id = col2.selectbox("Customer *", options=[None] + list(cust_options.keys()), format_func=lambda x: cust_options.get(x, "Select Customer"))
                    booking_no = col3.text_input("Booking Reference No", placeholder="e.g. BK-2026-0801")
                    
                    col4, col5 = st.columns(2)
                    sales_person = col4.text_input("Sales Person")
                    operations_owner = col5.text_input("Operations Owner")
                    
                    col6, col7 = st.columns(2)
                    customer_reference = col6.text_input("Customer Ref")
                    quotation_no = col7.text_input("Quotation No")
                    
                    st.subheader("Parties")
                    col8, col9, col10 = st.columns(3)
                    shipper = col8.text_input("Shipper", placeholder="Origin Contact")
                    consignee = col9.text_input("Consignee", placeholder="Destination Contact")
                    notify_party = col10.text_input("Notify Party")

                with t2:
                    st.subheader("Routing & Transit")
                    rc1, rc2 = st.columns(2)
                    place_of_receipt = rc1.text_input("Place of Receipt (POR)")
                    pol = rc2.text_input("Port of Loading (POL) *", placeholder="e.g. THLCH")
                    
                    rc3, rc4 = st.columns(2)
                    transshipment_port = rc3.text_input("Transshipment Port")
                    pod = rc4.text_input("Port of Discharge (POD) *", placeholder="e.g. VNSGN")
                    
                    rc5, rc6 = st.columns(2)
                    place_of_delivery = rc5.text_input("Place of Delivery")
                    final_destination = rc6.text_input("Final Destination")
                    
                    rc7, rc8 = st.columns(2)
                    origin_country = rc7.text_input("Origin Country")
                    destination_country = rc8.text_input("Destination Country")

                    rc9, rc10, rc11 = st.columns(3)
                    etd = rc9.date_input("Estimated Time of Departure (ETD) *", value=date.today())
                    eta = rc10.date_input("Estimated Time of Arrival (ETA) *", value=date.today())
                    carrier = rc11.text_input("Carrier / Line")

                with t3:
                    st.subheader("Cargo Specifications")
                    cc1, cc2, cc3 = st.columns(3)
                    commodity = cc1.text_input("Commodity")
                    hs_code = cc2.text_input("HS Code")
                    cargo_type = cc3.selectbox("Cargo Category", options=CARGO_TYPES)
                    
                    cc4, cc5 = st.columns(2)
                    package_type = cc4.text_input("Package Type", placeholder="e.g. Pallets, Cartons")
                    package_quantity = cc5.number_input("Package Quantity", min_value=0, value=0)
                    
                    cc6, cc7, cc8, cc9 = st.columns(4)
                    gross_weight = cc6.number_input("Gross Weight (KG)", min_value=0.0, format="%.2f")
                    net_weight = cc7.number_input("Net Weight (KG)", min_value=0.0, format="%.2f")
                    cbm = cc8.number_input("Volume (CBM)", min_value=0.0, format="%.2f")
                    chargeable_weight = cc9.number_input("Chargeable Weight (KG)", min_value=0.0, format="%.2f")
                    
                    cc10, cc11 = st.columns(2)
                    is_dg = cc10.checkbox("Is Dangerous Goods (DG)?")
                    is_temp_controlled = cc11.checkbox("Temperature Controlled?")
                    
                    special_cargo_remarks = st.text_area("Special Cargo Remarks")

                with t4:
                    st.subheader("Customs & Documentation")
                    doc1, doc2 = st.columns(2)
                    bl_no = doc1.text_input("Bill of Lading (BL) No")
                    invoice_no = doc2.text_input("Internal Invoice No")
                    
                    doc3, doc4 = st.columns(2)
                    customs_declaration_no = doc3.text_input("Customs Declaration No")
                    customs_status = doc4.text_input("Customs Status")
                    
                    doc5, doc6 = st.columns(2)
                    customs_broker = doc5.text_input("Customs Broker")
                    customs_clearance_date = doc6.date_input("Customs Clearance Date", value=None)

                remark = st.text_area("Operational Remarks / Notes", placeholder="Special handling requirements, temperature specs, etc.")
                
                submit = st.form_submit_button("🚀 Submit & Register Shipment", use_container_width=True, type="primary")

                if submit:
                    errors = []
                    if not customer_id:
                        errors.append("Customer is required.")
                    if not pol:
                        errors.append("Port of Loading is required.")
                    if not pod:
                        errors.append("Port of Discharge is required.")
                    if etd and eta and eta < etd:
                        errors.append("ETA cannot be earlier than ETD.")
                        
                    if errors:
                        for err in errors:
                            st.error(f"⚠️ Validation Error: {err}")
                    else:
                        payload = {
                            "job_type": job_type,
                            "booking_no": booking_no.strip(),
                            "customer_id": customer_id,
                            "customer_name": cust_options.get(customer_id, ""),
                            "sales_person": sales_person.strip(),
                            "operations_owner": operations_owner.strip(),
                            "customer_reference": customer_reference.strip(),
                            "quotation_no": quotation_no.strip(),
                            "shipper": shipper.strip(),
                            "consignee": consignee.strip(),
                            "notify_party": notify_party.strip(),
                            "cargo_type": cargo_type,
                            "carrier": carrier.strip(),
                            "bl_no": bl_no.strip(),
                            "invoice_no": invoice_no.strip(),
                            "place_of_receipt": place_of_receipt.strip(),
                            "pol": pol.strip(),
                            "transshipment_port": transshipment_port.strip(),
                            "pod": pod.strip(),
                            "place_of_delivery": place_of_delivery.strip(),
                            "final_destination": final_destination.strip(),
                            "origin_country": origin_country.strip(),
                            "destination_country": destination_country.strip(),
                            "etd": str(etd) if etd else None,
                            "eta": str(eta) if eta else None,
                            "commodity": commodity.strip(),
                            "hs_code": hs_code.strip(),
                            "package_type": package_type.strip(),
                            "package_quantity": package_quantity,
                            "gross_weight": float(gross_weight),
                            "net_weight": float(net_weight),
                            "cbm": float(cbm),
                            "chargeable_weight": float(chargeable_weight),
                            "is_dg": bool(is_dg),
                            "is_temp_controlled": bool(is_temp_controlled),
                            "special_cargo_remarks": special_cargo_remarks.strip(),
                            "customs_declaration_no": customs_declaration_no.strip(),
                            "customs_status": customs_status.strip(),
                            "customs_broker": customs_broker.strip(),
                            "customs_clearance_date": str(customs_clearance_date) if customs_clearance_date else None,
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
                                details=f"Created shipment {new_job_no} for {cust_options.get(customer_id, '')}"
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

    tab_status, tab_edit, tab_containers, tab_milestones, tab_financials, tab_delete = st.tabs([
        "🔄 Status", "✏️ Edit Details", "📦 Containers", "⏱️ Milestones", "💰 Financials", "🗑️ Prune"
    ])

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
                et1, et2, et3, et4 = st.tabs(["📋 General", "🗺️ Routing", "📦 Cargo & Weight", "🏢 Customs"])
                
                with et1:
                    ec1, ec2, ec3 = st.columns(3)
                    idx_cust = list(cust_options.keys()).index(target_shipment.get("customer_id")) if target_shipment.get("customer_id") in cust_options else 0
                    edit_customer_id = ec1.selectbox("Customer *", options=[None] + list(cust_options.keys()), format_func=lambda x: cust_options.get(x, "Select Customer"), index=idx_cust + 1 if target_shipment.get("customer_id") else 0)
                    edit_mbl = ec2.text_input("Master BL", value=target_shipment.get("mbl_no", ""))
                    edit_hbl = ec3.text_input("House BL", value=target_shipment.get("hbl_no", ""))

                    edit_shipper = st.text_input("Shipper", value=target_shipment.get("shipper", ""))
                    edit_consignee = st.text_input("Consignee", value=target_shipment.get("consignee", ""))
                    
                    ec4, ec5, ec6 = st.columns(3)
                    edit_incoterm = ec4.text_input("Incoterm", value=target_shipment.get("incoterm", ""))
                    edit_service = ec5.text_input("Service Type", value=target_shipment.get("service_type", ""))
                    edit_freight = ec6.text_input("Freight Term", value=target_shipment.get("freight_term", ""))

                with et2:
                    ec7, ec8 = st.columns(2)
                    edit_pol = ec7.text_input("POL", value=target_shipment.get("pol", ""))
                    edit_pod = ec8.text_input("POD", value=target_shipment.get("pod", ""))
                    
                    ec9, ec10, ec11 = st.columns(3)
                    edit_vessel = ec9.text_input("Vessel", value=target_shipment.get("vessel", ""))
                    edit_voyage = ec10.text_input("Voyage", value=target_shipment.get("voyage", ""))
                    edit_carrier = ec11.text_input("Carrier", value=target_shipment.get("carrier", ""))

                    ec12, ec13 = st.columns(2)
                    edit_etd = ec12.date_input("ETD", value=_safe_date(target_shipment.get("etd")))
                    edit_eta = ec13.date_input("ETA", value=_safe_date(target_shipment.get("eta")))

                    ec14, ec15 = st.columns(2)
                    edit_actual_departure = ec14.date_input("Actual Departure", value=_safe_date(target_shipment.get("actual_departure")))
                    edit_actual_arrival = ec15.date_input("Actual Arrival", value=_safe_date(target_shipment.get("actual_arrival")))

                with et3:
                    ec16, ec17, ec18 = st.columns(3)
                    edit_gross_weight = ec16.number_input("Gross Weight (KG)", value=float(target_shipment.get("gross_weight", 0.0) or 0.0))
                    edit_cbm = ec17.number_input("Volume (CBM)", value=float(target_shipment.get("cbm", 0.0) or 0.0))
                    edit_package_qty = ec18.number_input("Package Qty", value=int(target_shipment.get("package_quantity", 0) or 0))

                with et4:
                    edit_customs_declaration = st.text_input("Customs Declaration No", value=target_shipment.get("customs_declaration_no", ""))
                    edit_customs_status = st.text_input("Customs Status", value=target_shipment.get("customs_status", ""))

                edit_remark = st.text_area("Remarks", value=target_shipment.get("remark", ""))

                save_edit = st.form_submit_button("💾 Save Operational Modifications", use_container_width=True)

                if save_edit:
                    errors = []
                    if not edit_customer_id:
                        errors.append("Customer is required.")
                    if edit_etd and edit_eta and edit_eta < edit_etd:
                        errors.append("ETA cannot be earlier than ETD.")
                        
                    if errors:
                        for err in errors:
                            st.error(f"⚠️ Validation Error: {err}")
                    else:
                        patch = {
                            "customer_id": edit_customer_id,
                            "customer_name": cust_options.get(edit_customer_id, ""),
                            "carrier": edit_carrier.strip(),
                            "mbl_no": edit_mbl.strip(),
                            "hbl_no": edit_hbl.strip(),
                            "incoterm": edit_incoterm.strip(),
                            "service_type": edit_service.strip(),
                            "freight_term": edit_freight.strip(),
                            "vessel": edit_vessel.strip(),
                            "voyage": edit_voyage.strip(),
                            "pol": edit_pol.strip(),
                            "pod": edit_pod.strip(),
                            "etd": str(edit_etd) if edit_etd else None,
                            "eta": str(edit_eta) if edit_eta else None,
                            "actual_departure": str(edit_actual_departure) if edit_actual_departure else None,
                            "actual_arrival": str(edit_actual_arrival) if edit_actual_arrival else None,
                            "shipper": edit_shipper.strip(),
                            "consignee": edit_consignee.strip(),
                            "gross_weight": float(edit_gross_weight),
                            "cbm": float(edit_cbm),
                            "package_quantity": int(edit_package_qty),
                            "customs_declaration_no": edit_customs_declaration.strip(),
                            "customs_status": edit_customs_status.strip(),
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
                        except ValueError as ve:
                            st.error(f"⚠️ Operation Rejected: {str(ve)}")
                        except Exception as save_err:
                            st.error(f"Failed to save modifications: {str(save_err)}")

    with tab_containers:
        st.markdown("#### 📦 Job Containers")
        from managers.shipment_manager import list_job_containers, add_job_container, delete_job_container
        
        try:
            from managers.shipment_manager import get_shipment # needed if not imported
            containers = list_job_containers(target_shipment["job_no"])
            if containers:
                df_containers = pd.DataFrame(containers)
                cols = ["id", "container_no", "container_size", "container_type", "seal_no", "vgm_kg"]
                display_cols = [c for c in cols if c in df_containers.columns]
                st.dataframe(df_containers[display_cols], use_container_width=True, hide_index=True)
                
                # Deletion UI
                del_id = st.selectbox("Select Container ID to Remove", options=[c["id"] for c in containers])
                if st.button("🗑️ Remove Selected Container"):
                    if delete_job_container(del_id):
                        st.success("Container removed.")
                        st.rerun()
            else:
                st.write("No containers linked yet.")
        except Exception as e:
            st.error(f"Could not load containers: {str(e)}")

        with st.expander("➕ Add Container"):
            with st.form("add_container_form"):
                cc1, cc2 = st.columns(2)
                c_no = cc1.text_input("Container No (e.g. TLLU1234567)")
                c_seal = cc2.text_input("Seal No")
                
                cc3, cc4, cc5 = st.columns(3)
                c_size = cc3.selectbox("Size", ["20DC", "40DC", "40HC", "45HC"])
                c_type = cc4.selectbox("Type", ["GP", "HQ", "RF", "OT", "FR"])
                c_vgm = cc5.number_input("VGM (KG)", min_value=0.0)
                
                c_sub = st.form_submit_button("Add Container")
                if c_sub and c_no:
                    try:
                        add_job_container({
                            "shipment_id": target_shipment["id"],
                            "job_no": target_shipment["job_no"],
                            "container_no": c_no,
                            "seal_no": c_seal,
                            "container_size": c_size,
                            "container_type": c_type,
                            "vgm_kg": float(c_vgm)
                        })
                        st.success("Container added!")
                        st.rerun()
                    except sqlite3.IntegrityError:
                        st.error("Duplicate Container: This container is already linked to this shipment.")
                    except Exception as e:
                        if "UNIQUE constraint" in str(e):
                            st.error("Duplicate Container: This container is already linked to this shipment.")
                        else:
                            st.error(f"Error adding container: {str(e)}")

    with tab_milestones:
        st.markdown("#### ⏱️ Shipment Milestones")
        from managers.shipment_manager import list_milestones, add_milestone
        try:
            milestones = list_milestones(target_shipment["job_no"])
            if milestones:
                for m in milestones:
                    st.markdown(f"- **{str(m['event_date'])[:16]}** | `{m['milestone_code']}` - {m['milestone_name']} (Loc: {m.get('location', '')})")
            else:
                st.write("No milestones logged yet.")
        except Exception as e:
            st.error(f"Could not load milestones: {str(e)}")
            
        with st.expander("Log New Milestone"):
            with st.form("new_milestone_form"):
                mc1, mc2 = st.columns(2)
                m_code = mc1.text_input("Event Code", placeholder="e.g. GATE_IN")
                m_name = mc2.text_input("Event Name", placeholder="e.g. Gate In at POL")
                m_date = st.date_input("Event Date")
                m_loc = st.text_input("Location")
                m_sub = st.form_submit_button("Log Milestone")
                if m_sub and m_code:
                    try:
                        add_milestone({
                            "shipment_id": target_shipment.get("id"),
                            "job_no": target_shipment["job_no"],
                            "milestone_code": m_code,
                            "milestone_name": m_name,
                            "event_date": str(m_date),
                            "location": m_loc,
                            "created_by": str(user.get("username", "operator"))
                        })
                        st.success("Milestone logged!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error logging milestone: {str(e)}")

    with tab_financials:
        st.markdown("#### 💰 Financial Summary")
        from managers.shipment_manager import get_job_financial_summary
        try:
            fin = get_job_financial_summary(target_shipment["id"])
            fc1, fc2, fc3, fc4 = st.columns(4)
            fc1.metric("Total Revenue (THB)", f"{fin['total_revenue_thb']:,.2f}")
            fc2.metric("Total Cost (THB)", f"{fin['total_cost_thb']:,.2f}")
            
            p_color = "normal" if fin['gross_profit_thb'] >= 0 else "inverse"
            fc3.metric("Gross Profit (THB)", f"{fin['gross_profit_thb']:,.2f}", delta=f"{fin['margin_percent']:.1f}% Margin", delta_color=p_color)
            
            st.info("💡 Real-time roll-up from `job_costs` (AP Ledger) and `invoices` (AR Ledger).")
        except Exception as e:
            st.error(f"Failed to load financials: {str(e)}")

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