"""
Phase 18.5, 18.6, 18.7 - Executive Reports, Sales Performance, Commission
"""
import streamlit as st
import pandas as pd
from datetime import datetime

from managers.report_manager import get_company_monthly_performance, get_sales_performance_report, get_salesperson_job_drilldown
from managers.commission_manager import create_commission_draft

def render():
    st.title("📈 Management Reporting & Performance")
    
    tabs = st.tabs([
        "🏢 Company Monthly Report", 
        "📈 Sales Performance", 
        "💵 Sales Commission"
    ])
    
    now = datetime.now()
    default_month = f"{now.month:02d}"
    default_year = str(now.year)
    
    # ---------------------------------------------------------
    # TAB 1: COMPANY MONTHLY REPORT
    # ---------------------------------------------------------
    with tabs[0]:
        st.subheader("Company Monthly Performance")
        c1, c2 = st.columns(2)
        r_month = c1.selectbox("Reporting Month", [f"{i:02d}" for i in range(1, 13)], index=int(default_month)-1, key="cm_month")
        r_year = c2.selectbox("Reporting Year", ["2025", "2026", "2027", "2028"], index=1, key="cm_year")
        
        if st.button("Generate Executive Report", key="btn_cm"):
            perf = get_company_monthly_performance(r_month, r_year)
            
            st.markdown("### Operations Overview")
            op = perf["operations"]
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Total Jobs", op["total_jobs"])
            col2.metric("Export Jobs", op["export_jobs"])
            col3.metric("Import Jobs", op["import_jobs"])
            col4.metric("Won Jobs", op["won_jobs"])
            
            st.markdown("### Financial Overview (Strict GP Rule)")
            rev = perf["revenue"]
            cost = perf["cost"]
            prof = perf["profit"]
            
            col5, col6, col7, col8 = st.columns(4)
            col5.metric("Actual Revenue", f"{rev['actual_revenue']:,.2f}")
            col6.metric("Actual Cost", f"{cost['actual_cost']:,.2f}")
            col7.metric("Actual GP", f"{prof['actual_gp']:,.2f}")
            col8.metric("Gross Margin", f"{prof['gross_margin_pct']}%")
            
            st.markdown("### Salesperson Breakdown")
            if perf["sales"]:
                df_sp = pd.DataFrame(perf["sales"])
                st.dataframe(df_sp[["sales_person", "total_jobs", "export_jobs", "import_jobs", "actual_revenue", "actual_cost", "actual_gp", "gross_margin_pct"]], use_container_width=True)
            else:
                st.info("No sales data for this month.")
                
            st.info("💡 Note: Export jobs use ETD month. Import jobs use ETA month.")

    # ---------------------------------------------------------
    # TAB 2: SALES PERFORMANCE (DRILL DOWN)
    # ---------------------------------------------------------
    with tabs[1]:
        st.subheader("Salesperson Drill-down")
        c1, c2, c3 = st.columns(3)
        sp_month = c1.selectbox("Reporting Month", [f"{i:02d}" for i in range(1, 13)], index=int(default_month)-1, key="sp_month")
        sp_year = c2.selectbox("Reporting Year", ["2025", "2026", "2027", "2028"], index=1, key="sp_year")
        sp_name = c3.text_input("Salesperson Name", key="sp_name")
        
        if st.button("Search Jobs", key="btn_sp"):
            if not sp_name:
                st.warning("Please enter a salesperson name.")
            else:
                jobs = get_salesperson_job_drilldown(sp_month, sp_year, sp_name)
                if jobs:
                    st.dataframe(pd.DataFrame(jobs), use_container_width=True)
                else:
                    st.info("No jobs found.")

    # ---------------------------------------------------------
    # TAB 3: COMMISSION
    # ---------------------------------------------------------
    with tabs[2]:
        st.subheader("Commission Draft Generation")
        c1, c2, c3 = st.columns(3)
        com_month = c1.selectbox("Reporting Month", [f"{i:02d}" for i in range(1, 13)], index=int(default_month)-1, key="com_month")
        com_year = c2.selectbox("Reporting Year", ["2025", "2026", "2027", "2028"], index=1, key="com_year")
        com_name = c3.text_input("Salesperson", key="com_name")
        
        if st.button("Calculate Commission", key="btn_com"):
            if not com_name:
                st.warning("Please enter a salesperson name.")
            else:
                try:
                    c_id = create_commission_draft(com_month, com_year, com_name)
                    st.success(f"Commission Draft Generated! Draft ID: {c_id}")
                except Exception as e:
                    st.error(str(e))