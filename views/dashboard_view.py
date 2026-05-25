import streamlit as st
import pandas as pd

from managers.dashboard_manager import (
    get_kpi_summary,
    get_monthly_flow,
    get_finance_kpi,
    get_top_routes,
)

# =========================================================
# SAFE VALUE HELPER (POSTGRES SAFE)
# =========================================================
def safe(val, default=0):
    return val if val is not None else default


# =========================================================
# MAIN DASHBOARD
# =========================================================
def render():

    st.title("📊 Freight Intelligence Dashboard")
    st.caption("CargoWise-style ERP Analytics (PostgreSQL)")

    # =====================================================
    # LOAD DATA (SAFE)
    # =====================================================
    try:
        kpi = get_kpi_summary() or {}
    except Exception:
        kpi = {}

    try:
        fin = get_finance_kpi() or {}
    except Exception:
        fin = {}

    try:
        flow = get_monthly_flow() or {}
    except Exception:
        flow = {}

    # =====================================================
    # KPI ROW (CORE OPS)
    # =====================================================
    st.subheader("🚢 Operations Overview")

    c1, c2, c3, c4 = st.columns(4)

    c1.metric("Total Shipments", safe(kpi.get("total_shipments")))
    c2.metric("Active Jobs", safe(kpi.get("active_jobs")))
    c3.metric("Finished", safe(kpi.get("finished_jobs")))
    c4.metric("Closed", safe(kpi.get("closed_jobs")))

    st.divider()

    # =====================================================
    # REAL-TIME ETA / ETD
    # =====================================================
    st.subheader("⏱️ Today Schedule")

    c1, c2 = st.columns(2)

    c1.metric("ETD Today", safe(kpi.get("etd_today")))
    c2.metric("ETA Today", safe(kpi.get("eta_today")))

    st.divider()

    # =====================================================
    # FINANCIAL KPI (ERP CORE)
    # =====================================================
    st.subheader("💰 Finance Overview")

    c1, c2 = st.columns(2)

    revenue = float(fin.get("revenue") or 0)
    ar = float(fin.get("ar") or 0)

    c1.metric("Revenue (Invoice)", f"฿{revenue:,.2f}")
    c2.metric("Outstanding AR", f"฿{ar:,.2f}", delta_color="inverse")

    st.divider()

    # =====================================================
    # MONTHLY FLOW
    # =====================================================
    st.subheader("📅 Monthly Flow")

    c1, c2 = st.columns(2)

    c1.metric("ETD This Month", safe(flow.get("etd_this_month")))
    c2.metric("ETA This Month", safe(flow.get("eta_this_month")))

    st.divider()

    # =====================================================
    # TOP ROUTES ANALYTICS
    # =====================================================
    st.subheader("🌍 Top Trade Lanes (POL → POD)")

    try:
        routes = get_top_routes() or []
    except Exception:
        routes = []

    if routes:

        df = pd.DataFrame(routes)

        # PostgreSQL-safe column mapping
        if len(df.columns) >= 3:
            df = df.iloc[:, :3]
            df.columns = ["POL", "POD", "Volume"]

        st.dataframe(df, use_container_width=True)

    else:
        st.info("No route data available yet")


# =========================================================
# FUTURE EXTENSION HOOK (CARGOWISE STYLE)
# =========================================================
def _placeholder_ai_insight():
    """
    Future upgrade:
    - Delay prediction per port
    - Route profitability scoring
    - Customer ranking AI
    """
    pass