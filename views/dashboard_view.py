"""
Phase 18.17 - Executive Dashboard
"""
import streamlit as st
import pandas as pd
from datetime import datetime
from managers.report_manager import get_company_monthly_performance
from managers.month_end_manager import get_month_end_summary

def render():
    st.markdown("<p style='color: #38BDF8; font-weight: 700; font-size: 13px; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 2px;'>Enterprise Executive Intelligence</p>", unsafe_allow_html=True)
    st.markdown("<h2 style='margin-top: 0px; font-weight: 800; color:#F8FAFC;'>🚢 FreightFlow Enterprise Control Tower</h2>", unsafe_allow_html=True)
    
    # Time context
    now = datetime.now()
    c1, c2 = st.columns([1, 4])
    r_month = c1.selectbox("Reporting Month", [f"{i:02d}" for i in range(1, 13)], index=now.month-1)
    r_year = c2.selectbox("Reporting Year", ["2025", "2026", "2027", "2028"], index=1)
    
    st.divider()

    # Load data
    with st.spinner("Aggregating Multi-tenant Financial Logs..."):
        try:
            perf = get_company_monthly_performance(r_month, r_year)
            month_end = get_month_end_summary(r_month, r_year)
        except Exception as e:
            st.error(f"Failed to load dashboard data: {str(e)}")
            return

    # 1. KPI Cards
    st.markdown("### 🏆 Financial Target & Margins")
    rev = perf["revenue"]
    cost = perf["cost"]
    prof = perf["profit"]
    ops = perf["operations"]
    
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total Jobs", ops["total_jobs"])
    m2.metric("Gross Revenue (Actual AR)", f"฿ {rev['actual_revenue']:,.2f}")
    m3.metric("Gross Profit (Actual)", f"฿ {prof['actual_gp']:,.2f}")
    m4.metric("GP Margin %", f"{prof['gross_margin_pct']}%")
    
    m5, m6, m7, m8 = st.columns(4)
    m5.metric("Cost (Accrued + Actual AP)", f"฿ {cost['actual_cost']:,.2f}")
    m6.metric("Outstanding AR", f"฿ {rev['outstanding_ar']:,.2f}")
    
    # Pull exceptions from month_end
    unbilled = month_end.get("total_jobs", 0) - month_end.get("closed_jobs", 0) 
    # Just mock unbilled/uncosted for display based on logic
    m7.metric("Open / Unbilled Jobs", month_end.get("open_jobs", 0), delta_color="inverse")
    m8.metric("Export vs Import", f"{ops['export_jobs']} Exp / {ops['import_jobs']} Imp")

    st.divider()
    
    # 2. Charts
    st.markdown("### 📈 Operational Trends")
    c_left, c_right = st.columns(2)
    
    with c_left:
        st.markdown("**Salesperson Performance (GP)**")
        if perf["sales"]:
            df_sp = pd.DataFrame(perf["sales"])
            df_sp["sales_person"] = df_sp["sales_person"].fillna("Unassigned").astype(str)
            df_sp["actual_gp"] = pd.to_numeric(df_sp["actual_gp"], errors="coerce").fillna(0.0)
            st.bar_chart(df_sp, x="sales_person", y="actual_gp", color="#38bdf8")
        else:
            st.info("No data")
            
    with c_right:
        st.markdown("**Mode Distribution**")
        if ops["total_jobs"] > 0:
            df_mode = pd.DataFrame([
                {"Mode": "SEA", "Count": ops["sea_jobs"]},
                {"Mode": "AIR", "Count": ops["air_jobs"]},
                {"Mode": "ROAD", "Count": ops["cross_border_jobs"]}
            ])
            st.bar_chart(df_mode, x="Mode", y="Count", color="#f87171")
        else:
            st.info("No data")