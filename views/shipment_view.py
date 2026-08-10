"""
Phase 18.4 - Job Sheet 360 & Job Control Center
"""
import streamlit as st
import pandas as pd
from datetime import datetime, date

from managers.auth_manager import can_write
from managers.shipment_manager import list_shipments, get_shipment, create_shipment, update_shipment, STATUS_FLOW, list_job_containers, list_milestones
from managers.profit_manager import get_profit_summary
from managers.document_manager import list_documents
from managers.transport_manager import list_transport_orders_by_job
from managers.regulatory_manager import list_submissions_by_job

def render():
    st.title("📦 Job Control Center")
    
    # 1. Selection & Global List
    st.subheader("Job Ledger")
    jobs = list_shipments()
    if jobs:
        df = pd.DataFrame(jobs)
        # minimal display
        st.dataframe(df[["job_no", "status", "job_type", "customer_name", "sales_person", "etd", "eta"]], use_container_width=True)
    else:
        st.info("No jobs found in the system.")
        
    st.divider()
    
    # Selection
    if jobs:
        job_options = [j["job_no"] for j in jobs]
        selected_job_no = st.selectbox("Select Job for 360° View", options=["--- NEW JOB ---"] + job_options)
        
        if selected_job_no == "--- NEW JOB ---":
            render_new_job_form()
        else:
            job = get_shipment(selected_job_no)
            if job:
                render_job_360(job)

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
    st.markdown(f"## Job Sheet 360: `{job_no}`")
    
    # Header card
    st.markdown(f"""
    <div style="background-color: #0F172A; padding: 15px; border-radius: 10px; border: 1px solid #334155;">
        <h4 style="color:#38BDF8; margin-top:0;">{job.get('job_type', 'UNKNOWN')} | STATUS: {job.get('status', 'OPEN')}</h4>
        <b>Customer:</b> {job.get('customer_name')} | <b>Sales:</b> {job.get('sales_person')}<br>
        <b>Routing:</b> {job.get('pol')} ➡️ {job.get('pod')} | <b>Vessel/Voy:</b> {job.get('vessel')} / {job.get('voyage')}<br>
        <b>ETD:</b> {job.get('etd')} | <b>ETA:</b> {job.get('eta')}
    </div>
    <br>
    """, unsafe_allow_html=True)
    
    tabs = st.tabs([
        "Overview & Details", 
        "Containers", 
        "Milestones", 
        "Documents & Checklists", 
        "Job Profit (Actual vs Est)",
        "Transport / Delivery",
        "Regulatory"
    ])
    
    # TAB 1: Overview
    with tabs[0]:
        st.subheader("Shipment Details")
        with st.form("update_job_form"):
            c1, c2 = st.columns(2)
            new_status = c1.selectbox("Status", STATUS_FLOW, index=STATUS_FLOW.index(job['status']) if job['status'] in STATUS_FLOW else 0)
            hbl = c2.text_input("HBL", value=job.get('hbl_no', ''))
            mbl = c1.text_input("MBL", value=job.get('mbl_no', ''))
            pol = c2.text_input("POL", value=job.get('pol', ''))
            pod = c1.text_input("POD", value=job.get('pod', ''))
            
            if st.form_submit_button("Update Job"):
                update_shipment(job_no, {
                    "status": new_status,
                    "hbl_no": hbl,
                    "mbl_no": mbl,
                    "pol": pol,
                    "pod": pod
                })
                st.success("Updated")
                st.rerun()
                
    # TAB 2: Containers
    with tabs[1]:
        st.subheader("Container Control")
        containers = list_job_containers(job_no)
        if containers:
            st.dataframe(pd.DataFrame(containers)[["container_no", "container_type", "seal_no", "gross_weight"]], use_container_width=True)
        else:
            st.info("No containers attached.")
            
    # TAB 3: Milestones
    with tabs[2]:
        st.subheader("Operational Timeline")
        ms = list_milestones(job_no)
        if ms:
            st.dataframe(pd.DataFrame(ms)[["milestone_name", "planned_date", "actual_date", "status"]], use_container_width=True)
        else:
            st.info("No milestones.")
            
    # TAB 4: Documents
    with tabs[3]:
        st.subheader("Document Center & Checklist")
        docs = list_documents("JOB", job['id'])
        if docs:
            st.dataframe(pd.DataFrame(docs)[["document_no", "document_type", "version_number", "created_at"]], use_container_width=True)
        else:
            st.info("No documents attached.")
            
    # TAB 5: Job Profit
    with tabs[4]:
        st.subheader("Financial Control (Accrual vs Actual)")
        prof = get_profit_summary(job['id'])
        
        if prof:
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Estimated Revenue", f"{prof.get('ar_estimated', 0):,.2f}")
                st.metric("Actual Revenue (AR)", f"{prof.get('ar_actual', 0):,.2f}")
            with col2:
                st.metric("Estimated Cost", f"{prof.get('ap_estimated', 0):,.2f}")
                st.metric("Accrued + Actual Cost (AP)", f"{prof.get('ap_actual', 0) + prof.get('ap_accrued', 0):,.2f}")
            with col3:
                gp = prof.get("actual_net_profit", 0)
                margin = prof.get("actual_margin_pct", 0)
                st.metric("ACTUAL GROSS PROFIT", f"{gp:,.2f}")
                st.metric("Actual Margin %", f"{margin}%")
                
            st.warning("⚠️ Never mix Estimated numbers into Actual GP reporting. Accrued AP is included in Actual Cost to prevent margin inflation.")
        else:
            st.info("No financial data.")
            
    # TAB 6: Transport
    with tabs[5]:
        st.subheader("Transport Orders")
        to = list_transport_orders_by_job(job_no)
        if to:
            st.dataframe(pd.DataFrame(to)[["transport_order_no", "order_type", "status", "driver_name", "vehicle_no"]], use_container_width=True)
        else:
            st.info("No transport orders.")
            
    # TAB 7: Regulatory
    with tabs[6]:
        st.subheader("Regulatory Submissions")
        regs = list_submissions_by_job(job_no)
        if regs:
            st.dataframe(pd.DataFrame(regs)[["submission_type", "country", "status", "submission_date", "reference_no"]], use_container_width=True)
        else:
            st.info("No regulatory submissions.")