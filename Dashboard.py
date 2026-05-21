"""Smart Freight NTT - Single-page entry with query-param navigation.

Single-file approach guarantees that switching pages renders ONLY
the selected page's content. No leakage between pages possible.
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


# ===== Determine current page from query param OR session state =====
PAGES = ["dashboard", "quotation", "shipments"]
PAGE_LABELS = {
    "dashboard": "📊 Dashboard",
    "quotation": "📄 Quotation",
    "shipments": "📦 Shipments",
}

# Read from query params (handles both old and new Streamlit APIs)
def _get_query_page():
    try:
        # New API (Streamlit >= 1.30)
        qp = st.query_params
        val = qp.get("page", None)
        if isinstance(val, list):
            val = val[0] if val else None
        return val
    except Exception:
        try:
            # Legacy API
            qp = st.experimental_get_query_params()
            val = qp.get("page", [None])
            return val[0] if val else None
        except Exception:
            return None


def _set_query_page(page_id):
    try:
        st.query_params["page"] = page_id
    except Exception:
        try:
            st.experimental_set_query_params(page=page_id)
        except Exception:
            pass


# Priority: session_state (button click) > query param > default
url_page = _get_query_page()
session_page = st.session_state.get("_active_page", None)

if session_page in PAGES:
    current_page = session_page
elif url_page in PAGES:
    current_page = url_page
else:
    current_page = "dashboard"

# Sync state and URL
st.session_state["_active_page"] = current_page
if url_page != current_page:
    _set_query_page(current_page)


# ===== Sidebar navigation (custom buttons) =====
setup_sidebar()

with st.sidebar:
    st.markdown("### 🚢 Smart Freight NTT")
    st.markdown("---")
    for page_id in PAGES:
        is_active = page_id == current_page
        if st.button(
            PAGE_LABELS[page_id],
            key=f"nav_{page_id}",
            use_container_width=True,
            type="primary" if is_active else "secondary",
        ):
            # Clear ALL session state except active page tracker
            keys_to_keep = {"_active_page"}
            for k in list(st.session_state.keys()):
                if k not in keys_to_keep:
                    try:
                        del st.session_state[k]
                    except KeyError:
                        pass
            st.session_state["_active_page"] = page_id
            _set_query_page(page_id)
            st.rerun()


# ===== Render ONLY the selected page =====
# This is a hard switch — no other page's code is executed
if current_page == "dashboard":
    from views import dashboard_view
    dashboard_view.render()
elif current_page == "quotation":
    from views import quotation_view
    quotation_view.render()
elif current_page == "shipments":
    from views import shipments_view
    shipments_view.render()
else:
    st.error(f"Unknown page: {current_page}")
