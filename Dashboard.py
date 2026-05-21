"""Smart Freight NTT - Single-page entry with HARD page reload navigation."""
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


# ===== Pages config =====
PAGES = ["dashboard", "quotation", "shipments"]
PAGE_LABELS = {
    "dashboard": "📊 Dashboard",
    "quotation": "📄 Quotation",
    "shipments": "📦 Shipments",
}


def _get_query_page():
    try:
        qp = st.query_params
        val = qp.get("page", None)
        if isinstance(val, list):
            val = val[0] if val else None
        return val
    except Exception:
        try:
            qp = st.experimental_get_query_params()
            val = qp.get("page", [None])
            return val[0] if val else None
        except Exception:
            return None


# Determine current page from URL query param ONLY
url_page = _get_query_page()
current_page = url_page if url_page in PAGES else "dashboard"


# ===== Sidebar with HTML <a href> links (full page reload on click) =====
setup_sidebar()

with st.sidebar:
    st.markdown("### 🚢 Smart Freight NTT")
    st.markdown("---")
    
    nav_html = """
    <style>
    .nav-link {
        display: block;
        padding: 0.55rem 1rem;
        margin: 0.3rem 0;
        border-radius: 0.5rem;
        text-decoration: none !important;
        color: #FAFAFA !important;
        background: #262730;
        border: 1px solid #464853;
        text-align: left;
        font-size: 0.95rem;
        transition: all 0.15s ease;
    }
    .nav-link:hover {
        background: #3a3d4a;
        border-color: #5e6ad2;
        text-decoration: none !important;
    }
    .nav-link.active {
        background: #FF4B4B;
        border-color: #FF4B4B;
        color: white !important;
        font-weight: 600;
    }
    .nav-link:visited, .nav-link:focus, .nav-link:active {
        text-decoration: none !important;
    }
    </style>
    """
    
    for page_id in PAGES:
        is_active = page_id == current_page
        cls = "nav-link active" if is_active else "nav-link"
        nav_html += f'<a href="?page={page_id}" target="_self" class="{cls}">'
        nav_html += f'{PAGE_LABELS[page_id]}</a>'
    
    st.markdown(nav_html, unsafe_allow_html=True)


# ===== Render selected page =====
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
