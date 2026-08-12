"""
Phase 30 Consolidated Job Control Center & Job 360 Workspace
"""
import streamlit as st
import pandas as pd
from datetime import datetime, date

from managers.auth_manager import can_write
from managers.shipment_manager import (
    list_shipments, get_shipment, create_shipment, update_shipment, 
    STATUS_FLOW, list_job_containers, list_milestones, add_job_container
)
from managers.profit_manager import get_profit_summary
from managers.document_manager import list_documents
from managers.transport_manager import list_transport_orders_by_job
from managers.regulatory_manager import list_submissions_by_job
from core.audit import list_audit_logs

def render():
    st.subheader("Job Ledger")
    jobs = list_shipments()
    
    # 1. Job Ledger (Simplified Columns)
    if jobs:
        df = pd.DataFrame(jobs)
        display_cols = ["job_no", "customer_name", "mode", "pol", "pod", "etd", "eta", "status", "sales_person"]
        # Ensure all columns exist in dataframe, fill missing with None
        for col in display_cols:
            if col not in df.columns:
                df[col] = None
        
        st.dataframe(df[display_cols], use_container_width=True)
    else:
        st.info("No jobs found in the system.")
        
    st.divider()
    
    # 2. Selection & Render Job 360
    if jobs:
        job_options = [j["job_no"] for j in jobs]
        selected_job_no = st.selectbox("Select Job for 360° View", options=["--- NEW JOB ---"] + job_options)
        
        if selected_job_no == "--- NEW JOB ---":
            render_new_job_form()
        else:
            job = get_shipment(selected_job_no)
            if job:
                render_job_360(job)
    else:
        render_new_job_form()

def render_new_job_form():
    st.markdown("### Create New Job")
    with st.form("new_job_form"):
        col1, col2 = st.columns(2)
        job_type = col1.selectbox("Type", ["EXPORT SEA FCL", "IMPORT SEA FCL", "EXPORT AIR", "IMPORT AIR", "CROSS BORDER"])
        mode = col2.selectbox("Mode", ["SEA", "AIR", "ROAD"])
        
        customer = st.text_input("Customer Name")
        sales = st.text_input("Salesperson")
        
        c3, c4 = st.columns(2)
        etd = c3.date_input("ETD")
        eta = c4.date_input("ETA")
        
        if st.form_submit_button("Create Job"):
            try:
                new_job = create_shipment({
                    "job_type": job_type,
                    "mode": mode,
                    "customer_name": customer,
                    "sales_person": sales,
                    "etd": str(etd),
                    "eta": str(eta)
                })
                st.success(f"Job Created! {new_job}")
                st.rerun()
            except Exception as e:
                st.error(f"Failed: {str(e)}")

def render_job_360(job):
    job_no = job["job_no"]
    
    # Header summary metrics card
    prof = get_profit_summary(job['id'])
    gp_val = prof.get("actual_net_profit", 0.0) if prof else 0.0
    margin_val = prof.get("actual_margin_pct", 0.0) if prof else 0.0
    
    st.markdown(f"""
    <div style="background-color: #0F172A; padding: 15px; border-radius: 10px; border: 1px solid #334155;">
        <h4 style="color:#38BDF8; margin-top:0;">{job.get('job_type', 'UNKNOWN')} | STATUS: {job.get('status', 'OPEN')}</h4>
        <b>Customer:</b> {job.get('customer_name')} | <b>Sales:</b> {job.get('sales_person')}<br>
        <b>Routing:</b> {job.get('pol')} ➡️ {job.get('pod')} | <b>Vessel/Voy:</b> {job.get('vessel')} / {job.get('voyage')}<br>
        <b>ETD:</b> {job.get('etd')} | <b>ETA:</b> {job.get('eta')} | <b>Est GP:</b> {gp_val:,.2f} ({margin_val}%)
    </div>
    <br>
    """, unsafe_allow_html=True)
    
    # Exactly 7 streamlined tabs
    tabs = st.tabs([
        "1. Overview", 
        "2. Operations", 
        "3. Cargo & Containers", 
        "4. Milestones", 
        "5. Documents", 
        "6. Financial",
        "7. History"
    ])
    
    # TAB 1: Overview
    with tabs[0]:
        st.subheader("Key Information")
        col1, col2 = st.columns(2)
        col1.write(f"**Job No:** {job_no}")
        col1.write(f"**Customer:** {job.get('customer_name')}")
        col1.write(f"**Salesperson:** {job.get('sales_person')}")
        col1.write(f"**Mode:** {job.get('mode')}")
        
        col2.write(f"**POL:** {job.get('pol')}")
        col2.write(f"**POD:** {job.get('pod')}")
        col2.write(f"**ETD:** {job.get('etd')}")
        col2.write(f"**ETA:** {job.get('eta')}")
        col2.write(f"**Status:** {job.get('status')}")
        
    # TAB 2: Operations
    with tabs[1]:
        st.subheader("Operations Control")
        with st.form("ops_control_form"):
            col1, col2 = st.columns(2)
            pol = col1.text_input("POL", value=job.get('pol', ''))
            pod = col2.text_input("POD", value=job.get('pod', ''))
            vessel = col1.text_input("Vessel", value=job.get('vessel', ''))
            voyage = col2.text_input("Voyage", value=job.get('voyage', ''))
            
            c1, c2 = st.columns(2)
            new_status = c1.selectbox("Status", STATUS_FLOW, index=STATUS_FLOW.index(job['status']) if job['status'] in STATUS_FLOW else 0)
            remarks = c2.text_input("Operational Remarks", value=job.get('remark', ''))
            
            if st.form_submit_button("Update Operations"):
                update_shipment(job_no, {
                    "pol": pol,
                    "pod": pod,
                    "vessel": vessel,
                    "voyage": voyage,
                    "status": new_status,
                    "remark": remarks
                })
                st.success("Operations Updated Successfully!")
                st.rerun()
                
    # TAB 3: Cargo & Containers
    with tabs[2]:
        st.subheader("Cargo & Container Assignments")
        
        # Form to add new container
        with st.form("add_container_form"):
            st.markdown("##### Add Container")
            c1, c2, c3 = st.columns(3)
            c_no = c1.text_input("Container No")
            c_size = c2.selectbox("Size", ["20GP", "40GP", "40HC", "45HC"])
            c_seal = c3.text_input("Seal No")
            if st.form_submit_button("Add Container"):
                try:
                    add_job_container({
                        "job_no": job_no,
                        "container_no": c_no,
                        "container_size": c_size,
                        "seal_no": c_seal,
                        "gross_weight": 0.0
                    })
                    st.success("Container assigned!")
                    st.rerun()
                except Exception as e:
                    st.error(str(e))
        
        containers = list_job_containers(job_no)
        if containers:
            st.dataframe(pd.DataFrame(containers)[["container_no", "container_size", "seal_no", "gross_weight"]], use_container_width=True)
        else:
            st.info("No containers attached.")
            
    # TAB 4: Milestones
    with tabs[3]:
        st.subheader("Operational Timeline")
        ms = list_milestones(job_no)
        if ms:
            st.dataframe(pd.DataFrame(ms)[["milestone_name", "planned_date", "actual_date", "status"]], use_container_width=True)
        else:
            st.info("No milestones tracked for this job.")
            
    # TAB 5: Documents
    with tabs[4]:
        st.subheader("Associated Documents")
        docs = list_documents("JOB", job['id'])
        if docs:
            st.dataframe(pd.DataFrame(docs)[["document_no", "document_type", "version_number", "created_at"]], use_container_width=True)
        else:
            st.info("No documents attached.")
            
        st.divider()
        st.subheader("Transport Orders & Custom Submissions")
        to = list_transport_orders_by_job(job_no)
        if to:
            st.dataframe(pd.DataFrame(to)[["transport_order_no", "order_type", "status", "driver_name"]], use_container_width=True)
        else:
            st.info("No transport orders assigned.")
            
    # TAB 6: Financial
    with tabs[5]:
        st.subheader("Job Profit & Loss (Actual vs Accrual)")
        if prof:
            col1, col2 = st.columns(2)
            col1.metric("Actual Revenue (AR)", f"{prof.get('ar_actual', 0.0):,.2f}")
            col2.metric("Actual Cost (AP + Accrued)", f"{(prof.get('ap_actual', 0.0) + prof.get('ap_accrued', 0.0)):,.2f}")
            
            c1, c2 = st.columns(2)
            c1.metric("ACTUAL GROSS PROFIT", f"{gp_val:,.2f}")
            c2.metric("Actual Margin %", f"{margin_val}%")
        else:
            st.info("No financial data found.")
            
    # TAB 7: History
    with tabs[6]:
        st.subheader("Audit Log History")
        logs = list_audit_logs(entity="booking", search=job_no)
        if logs:
            st.dataframe(pd.DataFrame(logs)[["username", "action", "details", "timestamp"]], use_container_width=True)
        else:
            st.info("No changes recorded in audit logs.")