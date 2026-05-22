"""Smart Freight NTT - Multi-module Freight Forwarding Operating System.

Modules:
  • Dashboard — KPIs, active shipments, financial overview
  • CRM — Customer Database
  • Quotation — Generate / Edit / Copy
  • Booking — Booking confirmations
  • Shipment — Job Control + B/L
  • Billing — Invoice / BN / CN / DN / SOA
  • Reports — Analytics
"""
import streamlit as st

st.set_page_config(
    page_title="Smart Freight NTT",
    page_icon="🚢",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ===== Initialize database =====
from database.connection import init_database
from utils.nav import setup_sidebar
from managers.auth_manager import can_read, ROLE_LABELS


@st.cache_resource
def _init_db():
    init_database()
    return True


_init_db()


# ===== Pages config (each page → required module access) =====
PAGES = [
    ("dashboard", "📊 Dashboard", "dashboard"),
    ("crm", "👥 CRM", "crm"),
    ("quotation", "📄 Quotation", "quotation"),
    ("booking", "📑 Booking", "booking"),
    ("shipments", "📦 Shipment", "shipment"),
    ("billing", "💰 Billing", "billing"),
    ("reports", "📈 Reports", "reports"),
]


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


# ===== AUTHENTICATION GATE =====
user = st.session_state.get("user")

if not user:
    setup_sidebar()
    from views import login_view
    login_view.render()
    st.stop()

role = user.get("role", "")

# ===== Determine current page =====
url_page = _get_query_page()
allowed_pages = [p[0] for p in PAGES if can_read(role, p[2])]
current_page = url_page if url_page in allowed_pages else (
    allowed_pages[0] if allowed_pages else "dashboard"
)


# ===== Sidebar with HTML link navigation =====
setup_sidebar()

with st.sidebar:
    st.markdown(f"""
    <div style='padding:0.5rem 0'>
        <div style='font-size:1.1rem;font-weight:700'>🚢 Smart Freight NTT</div>
        <div style='font-size:0.75rem;color:#9CA0A8;margin-top:2px'>
            {user.get('full_name','User')} · {ROLE_LABELS.get(role, role)}
        </div>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("---")
    
    nav_html = """
    <style>
    .nav-link {
        display:block; padding:0.55rem 1rem; margin:0.25rem 0;
        border-radius:0.5rem; text-decoration:none !important;
        color:#FAFAFA !important; background:#262730;
        border:1px solid #464853; text-align:left;
        font-size:0.92rem; transition:all 0.15s ease;
    }
    .nav-link:hover {
        background:#3a3d4a; border-color:#5e6ad2;
        text-decoration:none !important;
    }
    .nav-link.active {
        background:#FF4B4B; border-color:#FF4B4B;
        color:white !important; font-weight:600;
    }
    .nav-link:visited, .nav-link:focus, .nav-link:active {
        text-decoration:none !important;
    }
    </style>
    """
    
    for page_id, label, module in PAGES:
        if not can_read(role, module):
            continue
        is_active = page_id == current_page
        cls = "nav-link active" if is_active else "nav-link"
        nav_html += f'<a href="?page={page_id}" target="_self" class="{cls}">'
        nav_html += f'{label}</a>'
    
    st.markdown(nav_html, unsafe_allow_html=True)
    
    st.markdown("---")
    if st.button("🚪 Sign Out", use_container_width=True):
        for k in list(st.session_state.keys()):
            del st.session_state[k]
        st.rerun()


# ===== Render selected page =====
if current_page == "dashboard":
    from views import dashboard_view
    dashboard_view.render()
elif current_page == "crm":
    from views import crm_view
    crm_view.render()
elif current_page == "quotation":
    from views import quotation_view
    quotation_view.render()
elif current_page == "booking":
    from views import booking_view
    booking_view.render()
elif current_page == "shipments":
    from views import shipments_view
    shipments_view.render()
elif current_page == "billing":
    from views import billing_view
    billing_view.render()
elif current_page == "reports":
    from views import reports_view
    reports_view.render()
else:
    st.error(f"Unknown page: {current_page}")
