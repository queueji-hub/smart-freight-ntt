"""Smart Freight NTT — Entry point with multi-page navigation."""
import streamlit as st

st.set_page_config(
    page_title="Smart Freight NTT",
    page_icon="🚢",
    layout="wide",
)

# ===== Define all pages with custom titles =====
dashboard_page = st.Page(
    "pages_src/dashboard.py",
    title="Dashboard",
    icon="📊",
    default=True,
)
quotation_page = st.Page(
    "pages_src/quotation.py",
    title="Quotation",
    icon="📄",
)
shipments_page = st.Page(
    "pages_src/shipments.py",
    title="Shipments",
    icon="�",
)

# Build navigation
pg = st.navigation([dashboard_page, quotation_page, shipments_page])
pg.run()
