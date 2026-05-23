import streamlit as st
import pandas as pd

from managers.dashboard_manager import (
    get_kpi_summary,
    get_monthly_flow,
    get_finance_kpi,
    get_top_routes
)


def render():

    st.title("📊 Freight SaaS Dashboard (CargoWise Style)")

    # =========================
    # KPI ROW 1
    # =========================
    kpi = get_kpi_summary()
    fin = get_finance_kpi()
    flow = get_monthly_flow()

    c1, c2, c3, c4 = st.columns(4)

    c1.metric("Total Shipments", kpi["total_shipments"])
    c2.metric("Active Jobs", kpi["active_jobs"])
    c3.metric("Finished", kpi["finished_jobs"])
    c4.metric("Closed", kpi["closed_jobs"])

    st.divider()

    # =========================
    # ETD / ETA
    # =========================
    c1, c2 = st.columns(2)

    c1.metric("ETD Today", kpi["etd_today"])
    c2.metric("ETA Today", kpi["eta_today"])

    st.divider()

    # =========================
    # FINANCE
    # =========================
    c1, c2 = st.columns(2)

    c1.metric("Revenue (Invoice)", f"{fin['revenue']:,.2f}")
    c2.metric("Outstanding AR", f"{fin['ar']:,.2f}")

    st.divider()

    # =========================
    # MONTH FLOW
    # =========================
    c1, c2 = st.columns(2)

    c1.metric("ETD This Month", flow["etd_this_month"])
    c2.metric("ETA This Month", flow["eta_this_month"])

    st.divider()

    # =========================
    # TOP ROUTES
    # =========================
    st.subheader("🌍 Top Routes (POL → POD)")

    routes = get_top_routes()
    df = pd.DataFrame(routes)

    if not df.empty:
        df.columns = ["POL", "POD", "Volume"]
        st.dataframe(df, use_container_width=True)
    else:
        st.info("No data yet")