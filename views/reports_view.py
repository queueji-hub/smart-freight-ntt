"""
Phase 30 Consolidated Management Reporting & Performance View
"""
import streamlit as st
import pandas as pd
from datetime import datetime

from managers.report_manager import (
    get_company_monthly_performance, 
    get_sales_performance_report, 
    get_salesperson_job_drilldown
)
from managers.commission_manager import create_commission_draft

def render():
    st.subheader("Executive Management Reports")
    
    # 1. Scope & Period Selectors
    scope = st.radio("Report Scope", options=["🏢 Company Monthly Report", "📈 Salesperson Performance"], horizontal=True)
    
    now = datetime.now()
    default_month = f"{now.month:02d}"
    
    c1, c2 = st.columns(2)
    r_month = c1.selectbox("Reporting Month", [f"{i:02d}" for i in range(1, 13)], index=int(default_month)-1)
    r_year = c2.selectbox("Reporting Year", ["2025", "2026", "2027", "2028"], index=1)
    
    st.divider()
    
    # 2. Company Report View
    if scope == "🏢 Company Monthly Report":
        st.markdown("#### Company Financial & Operations Summary")
        if st.button("Generate Company Report"):
            perf = get_company_monthly_performance(r_month, r_year)
            
            # Metrics Row 1: Operations
            st.markdown("##### Operations Overview")
            op = perf["operations"]
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Total Jobs", op.get("total_jobs", 0))
            col2.metric("Export Jobs", op.get("export_jobs", 0))
            col3.metric("Import Jobs", op.get("import_jobs", 0))
            col4.metric("Won Jobs", op.get("won_jobs", 0))
            
            # Metrics Row 2: Finance
            st.markdown("##### Financial Overview (Strict GP Rule)")
            rev = perf["revenue"]
            cost = perf["cost"]
            prof = perf["profit"]
            
            col5, col6, col7, col8 = st.columns(4)
            col5.metric("Actual Revenue", f"{rev.get('actual_revenue', 0.0):,.2f}")
            col6.metric("Actual Cost", f"{cost.get('actual_cost', 0.0):,.2f}")
            col7.metric("Actual GP", f"{prof.get('actual_gp', 0.0):,.2f}")
            col8.metric("Gross Margin", f"{prof.get('gross_margin_pct', 0.0)}%")
            
            # Salesperson performance breakdown
            st.markdown("##### Salesperson Performance Breakdown")
            if perf.get("sales"):
                df_sp = pd.DataFrame(perf["sales"])
                if "sales_person" in df_sp.columns:
                    df_sp["sales_person"] = df_sp["sales_person"].fillna("Unassigned").astype(str)
                for col in ["actual_revenue", "actual_cost", "actual_gp", "gross_margin_pct"]:
                    if col in df_sp.columns:
                        df_sp[col] = pd.to_numeric(df_sp[col], errors="coerce").fillna(0.0)
                disp_cols = [c for c in ["sales_person", "total_jobs", "export_jobs", "import_jobs", "actual_revenue", "actual_cost", "actual_gp", "gross_margin_pct"] if c in df_sp.columns]
                st.dataframe(df_sp[disp_cols], width="stretch")
            else:
                st.info("No sales performance data recorded for this month.")
                
            st.info("💡 Note: Export jobs use ETD month. Import jobs use ETA month.")

    # 3. Salesperson Performance & Commission View
    else:
        st.markdown("#### Salesperson Performance & Commission")
        salesperson = st.text_input("Enter Salesperson Name")
        
        c1, c2 = st.columns(2)
        btn_search = c1.button("Search & Drill Down Jobs")
        btn_com = c2.button("Calculate & Draft Commission")
        
        if btn_search:
            if not salesperson:
                st.warning("Please enter a salesperson name.")
            else:
                jobs = get_salesperson_job_drilldown(r_month, r_year, salesperson)
                if jobs:
                    st.markdown(f"##### Job List for {salesperson} ({r_month}/{r_year})")
                    st.dataframe(pd.DataFrame(jobs)[["job_no", "customer_name", "job_type", "mode", "status", "actual_revenue", "actual_cost", "gross_profit", "gross_margin_pct"]], use_container_width=True)
                else:
                    st.info(f"No jobs found for salesperson: {salesperson}")
                    
        if btn_com:
            if not salesperson:
                st.warning("Please enter a salesperson name.")
            else:
                try:
                    c_id = create_commission_draft(r_month, r_year, salesperson)
                    st.success(f"Commission Draft Generated! Draft ID: {c_id}")
                except Exception as e:
                    st.error(str(e))