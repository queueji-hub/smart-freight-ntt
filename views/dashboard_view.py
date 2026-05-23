import streamlit as st
import pandas as pd
from datetime import date

from managers.kpi_manager import (
    get_kpi_summary,
    get_finance_kpi,
    get_top_routes,
    get_port_monthly_volume
)


# =========================
# MAIN RENDER FUNCTION
# =========================
def render():
    st.title("📊 Freight Dashboard (CargoWise Style)")

    # ================= KPI =================
    kpi = get_kpi_summary()
    fin = get_finance_kpi()

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Total Jobs", kpi.get("total_shipments", 0))
    col2.metric("Active Jobs", kpi.get("active_jobs", 0))
    col3.metric("Finished", kpi.get("finished_jobs", 0))
    col4.metric("Closed", kpi.get("closed_jobs", 0))

    st.divider()

    # ================= FINANCE =================
    st.subheader("💰 Finance Overview")

    c1, c2 = st.columns(2)
    c1.metric("Revenue", fin.get("revenue", 0))
    c2.metric("AR (Outstanding)", fin.get("ar", 0))

    st.divider()

    # ================= TOP ROUTES =================
    st.subheader("📦 Top Trade Routes")

    routes = get_top_routes()
    if routes:
        df = pd.DataFrame(routes)
        st.dataframe(df, use_container_width=True)
    else:
        st.info("No route data")

    st.divider()

    # ================= PORT ANALYTICS =================
    st.subheader("🗺️ Port Intelligence")

    ports = get_port_monthly_volume()
    if ports:
        df2 = pd.DataFrame(ports)
        st.dataframe(df2, use_container_width=True)
    else:
        st.info("No port data")