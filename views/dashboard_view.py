import streamlit as st
import pandas as pd

# Safe integration layer to absorb relational schema changes smoothly
from managers.dashboard_manager import (
    get_kpi_summary,
    get_monthly_flow,
    get_finance_kpi,
    get_top_routes,
)

# =========================================================
# STRUCTURAL COMPATIBILITY VALUE HELPER (POSTGRESQL SAFE)
# =========================================================
def safe_numeric(val, default=0.0):
    if val is None:
        return default
    try:
        return float(val)
    except (ValueError, TypeError):
        return default

def safe_int(val, default=0):
    if val is None:
        return default
    try:
        return int(val)
    except (ValueError, TypeError):
        return default

# =========================================================
# 🚀 ULTIMATE SALES PERFORMANCE BOARD RENDER PIPELINE
# =========================================================
def render():
    st.markdown("<p style='color: #38BDF8; font-weight: 700; font-size: 13px; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 2px;'>Executive Analytics Matrix</p>", unsafe_allow_html=True)
    st.markdown("<h2 style='margin-top: 0px; font-weight: 800; color:#F8FAFC;'>🚀 Sales & Performance Dashboard</h2>", unsafe_allow_html=True)
    
    # ---------------------------------------------------------
    # DATA INGESTION
    # ---------------------------------------------------------
    with st.spinner("Aggregating Multi-tenant Data Logs..."):
        try:
            kpi_data = get_kpi_summary() or {}
        except Exception as e:
            kpi_data = {}
            print(f"[DB LOG OUT] Error fetching KPI Summary: {str(e)}")

        try:
            finance_data = get_finance_kpi() or {}
        except Exception as e:
            finance_data = {}
            print(f"[DB LOG OUT] Error fetching Financial metrics: {str(e)}")

        try:
            flow_data = get_monthly_flow() or {}
        except Exception as e:
            flow_data = {}
            print(f"[DB LOG OUT] Error fetching flow trends: {str(e)}")

        try:
            trade_lanes_raw = get_top_routes() or []
        except Exception as route_err:
            trade_lanes_raw = []
            print(f"[RECOVERABLE CRASH]: Route analytics bypassed: {str(route_err)}")


    # ---------------------------------------------------------
    # 💰 SECTION 1: FINANCIAL & TARGET TRACKER (THE MILLION BAHT ENGINE)
    # ---------------------------------------------------------
    st.markdown("<h3 style='font-size:18px; color:#F1F5F9; font-weight:700; margin-bottom:12px;'>🏆 Revenue & Profit Margins (Month-to-Date)</h3>", unsafe_allow_html=True)
    
    fin_cols = st.columns(3)
    
    gross_revenue = safe_numeric(finance_data.get("revenue"))
    total_cost = safe_numeric(finance_data.get("cost")) # Assuming you have or will add this to get_finance_kpi
    net_profit = gross_revenue - total_cost
    profit_margin = (net_profit / gross_revenue * 100) if gross_revenue > 0 else 0
    outstanding_ar = safe_numeric(finance_data.get("ar"))
    
    fin_cols[0].metric("Gross Revenue (AR)", f"฿{gross_revenue:,.2f}", "Total Billed")
    fin_cols[1].metric("Net Profit (Est.)", f"฿{net_profit:,.2f}", f"{profit_margin:.1f}% Margin")
    fin_cols[2].metric("Outstanding (AR)", f"฿{outstanding_ar:,.2f}", "- Follow up required", delta_color="inverse")

    # 🎯 TARGET TRACKER PROGRESS BAR (Set target to 1,000,000 THB)
    MONTHLY_TARGET = 1000000 
    progress_percent = min((gross_revenue / MONTHLY_TARGET) * 100, 100)
    
    st.markdown(f"""
    <div style='background-color: #0F172A; padding: 15px; border-radius: 10px; border: 1px solid #1E293B;'>
        <div style='display: flex; justify-content: space-between; font-size: 14px; font-weight: bold; color: #94A3B8; margin-bottom: 8px;'>
            <span>🎯 Monthly Revenue Target (1M THB)</span>
            <span style='color: #38BDF8;'>{progress_percent:.1f}% Achieved</span>
        </div>
        <div style='background-color: #334155; border-radius: 10px; height: 12px; width: 100%;'>
            <div style='background: linear-gradient(90deg, #38BDF8 0%, #10B981 100%); height: 12px; border-radius: 10px; width: {progress_percent}%;'></div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<div style='margin: 25px 0;'></div>", unsafe_allow_html=True)

    # ---------------------------------------------------------
    # 📈 SECTION 2: SALES CONVERSION & OPERATIONS (WIN RATE)
    # ---------------------------------------------------------
    st.markdown("<h3 style='font-size:18px; color:#F1F5F9; font-weight:700; margin-bottom:12px;'>📈 Sales Pipeline & Conversion</h3>", unsafe_allow_html=True)
    
    # Calculate Conversion/Win Rate
    total_quotes = safe_int(kpi_data.get("total_quotes", 1)) # Assuming total quotes requested
    active_jobs = safe_int(kpi_data.get("active_jobs"))
    finished_jobs = safe_int(kpi_data.get("finished_jobs"))
    closed_jobs = safe_int(kpi_data.get("closed_jobs"))
    
    total_won_jobs = active_jobs + finished_jobs + closed_jobs
    win_rate = (total_won_jobs / total_quotes * 100) if total_quotes > 0 else 0

    ops_cols = st.columns(4)
    ops_cols[0].metric("Total Won Jobs", total_won_jobs, f"Win Rate: {win_rate:.1f}%")
    ops_cols[1].metric("Active (In Transit)", active_jobs)
    ops_cols[2].metric("Finished (Awaiting Invoice)", finished_jobs, "Ready to Bill", delta_color="normal")
    ops_cols[3].metric("Closed (Fully Paid)", closed_jobs)

    st.markdown("<div style='margin: 25px 0;'></div>", unsafe_allow_html=True)
    st.markdown("<hr style='border-top: 1px solid #1E293B;'/>", unsafe_allow_html=True)

    # ---------------------------------------------------------
    # 🌍 SECTION 3: TOP TRADE LANES (FOCUS ON WHAT MAKES MONEY)
    # ---------------------------------------------------------
    st.markdown("<h3 style='font-size:18px; color:#F1F5F9; font-weight:700; margin-bottom:4px;'>🌍 High-Yield Trade Lanes Performance</h3>", unsafe_allow_html=True)
    st.markdown("<p style='font-size:12px; color:#64748B; margin-bottom:14px;'>Focus your sales efforts on these high-volume routes.</p>", unsafe_allow_html=True)

    if trade_lanes_raw:
        df_lanes = pd.DataFrame(trade_lanes_raw)
        if len(df_lanes.columns) >= 3:
            df_lanes = df_lanes.iloc[:, :3]
            df_lanes.columns = ["POL (Origin)", "POD (Destination)", "Volume (TEUs/Jobs)"]
        
        st.dataframe(df_lanes, use_container_width=True, hide_index=True)
    else:
        st.info("ℹ️ No operational trade route statistics available for the current query lifecycle.")