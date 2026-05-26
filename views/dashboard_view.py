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
    """Ensures numeric conversions from PostgreSQL Decimal types do not throw runtime exceptions."""
    if val is None:
        return default
    try:
        return float(val)
    except (ValueError, TypeError):
        return default

def safe_int(val, default=0):
    """Ensures precise integer metric representations."""
    if val is None:
        return default
    try:
        return int(val)
    except (ValueError, TypeError):
        return default


# =========================================================
# MAIN VIEWS RENDER PIPELINE
# =========================================================
def render():
    # Subtle subtitle contextualization for elite dashboard analytics UI
    st.markdown("<p style='color: #38BDF8; font-weight: 700; font-size: 13px; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 2px;'>Executive Analytics Matrix</p>", unsafe_allow_html=True)
    st.markdown("<h2 style='margin-top: 0px; font-weight: 800; color:#F8FAFC;'>📊 CargoWise Intelligence Dashboard</h2>", unsafe_allow_html=True)
    
    # =====================================================
    # DATA INGESTION SUBSYSTEM (ASYNCHRONOUS SAFE RECOVERY)
    # =====================================================
    with st.spinner("Aggregating multi-tenant data logs from PostgreSQL..."):
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

    # =====================================================
    # SECTION 1: CENTRAL CORE LOGISTICS OPERATIONS
    # =====================================================
    st.markdown("<h3 style='font-size:18px; color:#F1F5F9; font-weight:700; margin-bottom:12px;'>🚢 Global Freight Operations</h3>", unsafe_allow_html=True)
    
    ops_cols = st.columns(4)
    ops_cols[0].metric("Total Historical Shipments", safe_int(kpi_data.get("total_shipments")))
    ops_cols[1].metric("Active Transit Jobs", safe_int(kpi_data.get("active_jobs")))
    ops_cols[2].metric("Completed Transactions", safe_int(kpi_data.get("finished_jobs")))
    ops_cols[3].metric("Closed (Archived)", safe_int(kpi_data.get("closed_jobs")))

    st.markdown("<div style='margin: 20px 0;'></div>", unsafe_allow_html=True)

    # =====================================================
    # SECTION 2: SCHEDULE MANIFESTS (REAL-TIME ETA/ETD)
    # =====================================================
    st.markdown("<h3 style='font-size:18px; color:#F1F5F9; font-weight:700; margin-bottom:12px;'>⏱️ Real-time Harbor Schedules (Today)</h3>", unsafe_allow_html=True)
    
    schedule_cols = st.columns(2)
    schedule_cols[0].metric("Departures Scheduled (ETD)", safe_int(kpi_data.get("etd_today")))
    schedule_cols[1].metric("Arrivals Tracked (ETA)", safe_int(kpi_data.get("eta_today")))

    st.markdown("<div style='margin: 20px 0;'></div>", unsafe_allow_html=True)

    # =====================================================
    # SECTION 3: ERP CORNERSTONE - FINANCIAL LEDGERS
    # =====================================================
    st.markdown("<h3 style='font-size:18px; color:#F1F5F9; font-weight:700; margin-bottom:12px;'>💰 Commercial Finance Overview</h3>", unsafe_allow_html=True)
    
    fin_cols = st.columns(2)
    
    gross_revenue = safe_numeric(finance_data.get("revenue"))
    outstanding_ar = safe_numeric(finance_data.get("ar"))
    
    fin_cols[0].metric("Recognized Gross Revenue (Invoiced)", f"฿{gross_revenue:,.2f}")
    fin_cols[1].metric("Outstanding Accounts Receivable (AR)", f"฿{outstanding_ar:,.2f}", delta="- Risk Exposure", delta_color="inverse")

    st.markdown("<div style='margin: 20px 0;'></div>", unsafe_allow_html=True)

    # =====================================================
    # SECTION 4: PERIODIC VOLUMETRIC METRICS
    # =====================================================
    st.markdown("<h3 style='font-size:18px; color:#F1F5F9; font-weight:700; margin-bottom:12px;'>📅 Aggregated Monthly Volumetrics</h3>", unsafe_allow_html=True)
    
    monthly_cols = st.columns(2)
    monthly_cols[0].metric("Total Dispatched This Month", safe_int(flow_data.get("etd_this_month")))
    monthly_cols[1].metric("Total Discharged This Month", safe_int(flow_data.get("eta_this_month")))

    st.markdown("<div style='margin: 20px 0;'></div>", unsafe_allow_html=True)
    st.markdown("<hr style='border-top: 1px solid #1E293B;'/>", unsafe_allow_html=True)

    # =====================================================
    # SECTION 5: RELATIONAL DATA FRAME - TRADE LANE ANALYTICS
    # =====================================================
    st.markdown("<h3 style='font-size:18px; color:#F1F5F9; font-weight:700; margin-bottom:4px;'>🌍 High-Yield Trade Lanes Performance</h3>", unsafe_allow_html=True)
    st.markdown("<p style='font-size:12px; color:#64748B; margin-bottom:14px;'>Statistical analysis mapping Point of Loading (POL) to Point of Discharge (POD) metrics.</p>", unsafe_allow_html=True)

    try:
        trade_lanes_raw = get_top_routes() or []
    except Exception as route_err:
        trade_lanes_raw = []
        print(f"[RECOVERABLE CRASH]: Route analytics grid bypassed. Context: {str(route_err)}")

    if trade_lanes_raw:
        # Convert explicitly to Pandas frame structure safely ensuring schema standardizations
        df_lanes = pd.DataFrame(trade_lanes_raw)

        # Resilient structure alignment for strict PostgreSQL tuple return structures
        if len(df_lanes.columns) >= 3:
            df_lanes = df_lanes.iloc[:, :3]
            df_lanes.columns = ["Point of Loading (POL)", "Point of Discharge (POD)", "Teus/Volume Capacity"]
        
        # Output clean high-fidelity interactive dashboard grid
        st.dataframe(
            df_lanes,
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("ℹ️ No operational trade route statistics available for the current query lifecycle.")


# =========================================================
# FUTURE EXTENSION HOOK (CARGOWISE AI PREDICTIVE INFRASTRUCTURE)
# =========================================================
def _placeholder_ai_insight():
    """
    Architectural Specification Hook for Upcoming Modules:
    - Deep Learning Engine for Port Congestion & Delay Risk Indexing.
    - Automated Route Profit Optimization Matrices.
    - Smart Account Customer Lifecycle & Revenue Predictors.
    """
    pass