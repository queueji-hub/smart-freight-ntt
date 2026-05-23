import streamlit as st
import pandas as pd
from managers.kpi_manager import (
    get_kpi_summary,
    get_monthly_flow,
    get_finance_kpi,
    get_top_routes
)

def render():
    st.title("🚢 Smart Freight Dashboard")

    kpi = get_kpi_summary()
    finance = get_finance_kpi()

    col1, col2, col3 = st.columns(3)

    col1.metric("Total Jobs", kpi["total_shipments"])
    col2.metric("Active Jobs", kpi["active_jobs"])
    col3.metric("Finished", kpi["finished_jobs"])

    st.divider()

    col4, col5 = st.columns(2)
    col4.metric("ETD Today", kpi["etd_today"])
    col5.metric("ETA Today", kpi["eta_today"])

    st.divider()

    st.subheader("💰 Finance KPI")
    st.metric("Revenue", finance["revenue"])
    st.metric("AR Outstanding", finance["ar"])

    st.divider()

    st.subheader("🚢 Top Routes")

    routes = get_top_routes()
    df = pd.DataFrame(routes)

    if not df.empty:
        st.dataframe(df, use_container_width=True)