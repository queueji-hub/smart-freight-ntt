"""Smart Freight NTT - Single-page entry with HARD page reload navigation.

Uses HTML anchor links that trigger full browser reload to guarantee
no DOM leakage between pages on Streamlit Cloud.
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
    
    # Build HTML links - each click triggers full browser reload
    nav_html = '<style>'
    nav_html += '.nav-link { display:block; padding:0.5rem 1rem; margin:0.25rem 0; '
    nav_html += 'border-radius:0.5rem; text-decoration:none; color:#FAFAFA; '
    nav_html += 'background:#262730; border:1px solid #464853; text-align:left; '
    nav_html += 'font-size:0.95rem; transition:all 0.15s; }'
    nav_html += '.nav-link:hover { background:#3a3d4a; border-color:#5e6ad2; }'
    nav_html += '.nav-link.active { background:#FF4B4B; border-color:#FF4B4B; '
    nav_html += 'color:white; font-weight:600; }'
    nav_html += '</style>'
    
    for page_id in PAGES:
        is_active = page_id == current_page
        cls = "nav-link active" if is_active else "nav-link"
        # target="_self" forces same-tab full reload
        nav_html += f'<a href="?page={page_id}" target="_self" class="{cls}">'
        nav_html += f'{PAGE_LABELS[page_id]}</a>'
    
    st.markdown(nav_html, unsafe_allow_html=True)


# ===== Render selected page =====
st.caption(f"🔧 v5.0-htmllinks · current_page = `{current_page}`")

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
