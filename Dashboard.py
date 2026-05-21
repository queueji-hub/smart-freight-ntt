"""Smart Freight NTT - Single-page entry with query-param navigation.

This single-file approach guarantees that switching pages renders ONLY
the selected page's content. No leakage from other pages possible.
"""
import streamlit as st

st.set_page_config(
    page_title="Smart Freight NTT",
    page_icon="🚢",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ===== Initialize database (cached) =====
from database.connection import init_database
from utils.nav import setup_sidebar


@st.cache_resource
def _init_db():
    init_database()
    return True


_init_db()


# ===== Determine current page from query param =====
PAGES = {
    "dashboard": ("📊 Dashboard", "dashboard_view"),
    "quotation": ("📄 Quotation", "quotation_view"),
    "shipments": ("📦 Shipments", "shipments_view"),
}

# Read page from URL query param, default to "dashboard"
qp = st.query_params
current_page = qp.get("page", "dashboard")
if current_page not in PAGES:
    current_page = "dashboard"

# ===== Detect page change and clear stale state =====
last_page = st.session_state.get("_active_page")
if last_page != current_page:
    # Wipe all session state when switching pages
    for k in list(st.session_state.keys()):
        if k != "_active_page":
            try:
                del st.session_state[k]
            except KeyError:
                pass
    st.session_state["_active_page"] = current_page

# ===== Sidebar navigation (custom, replaces Streamlit's default) =====
setup_sidebar()

with st.sidebar:
    st.markdown("### 🚢 Smart Freight NTT")
    st.markdown("---")
    for page_id, (label, _) in PAGES.items():
        is_active = page_id == current_page
        # Use button styled as nav link
        if st.button(
            label,
            key=f"nav_{page_id}",
            use_container_width=True,
            type="primary" if is_active else "secondary",
        ):
            st.query_params["page"] = page_id
            st.rerun()


# ===== Render the selected page =====
_, module_name = PAGES[current_page]

if current_page == "dashboard":
    from views import dashboard_view
    dashboard_view.render()
elif current_page == "quotation":
    from views import quotation_view
    quotation_view.render()
elif current_page == "shipments":
    from views import shipments_view
    shipments_view.render()
