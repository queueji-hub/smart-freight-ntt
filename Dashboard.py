"""Smart Freight NTT - Entry point with multi-page navigation."""
import streamlit as st

st.set_page_config(
    page_title="Smart Freight NTT",
    page_icon=":ship:",
    layout="wide",
)

# ===== Define all pages with Material Symbols icons =====
dashboard_page = st.Page(
    "pages_src/dashboard.py",
    title="Dashboard",
    icon=":material/dashboard:",
    default=True,
)
quotation_page = st.Page(
    "pages_src/quotation.py",
    title="Quotation",
    icon=":material/description:",
)
shipments_page = st.Page(
    "pages_src/shipments.py",
    title="Shipments",
    icon=":material/inventory_2:",
)

# Build navigation
pg = st.navigation([dashboard_page, quotation_page, shipments_page])
pg.run()
