"""Smart Freight NTT - Multi-module Freight Forwarding Operating System."""
import streamlit as st

st.set_page_config(
    page_title="Smart Freight NTT",
    page_icon="🚢",
    layout="wide",
    initial_sidebar_state="expanded",
)

from database.connection import init_database
from utils.nav import setup_sidebar
from managers.auth_manager import can_read, ROLE_LABELS
from managers.session_manager import get_user_by_token, delete_session

# ===== Initialization =====
@st.cache_resource
def _init_db():
    init_database()
    try:
        from managers.fx_manager import seed_default_rates
        seed_default_rates()
    except Exception:
        pass
    return True

_init_db()

# Auto-push DB to GitHub if dirty
try:
    from managers.db_persistence import push_if_dirty
    push_if_dirty()
except Exception:
    pass

# ===== Pages Configuration =====
PAGES = [
    ("dashboard", "📊 Dashboard", "dashboard"), ("crm", "👥 CRM", "crm"),
    ("quotation", "📄 Quotation", "quotation"), ("booking", "📑 Booking", "booking"),
    ("shipments", "📦 Shipment", "shipment"), ("tracking", "📍 Tracking", "shipment"),
    ("profit", "📊 Profit Sheet", "billing"), ("billing", "💰 Billing", "billing"),
    ("fx", "💱 FX Rates", "billing"), ("reports", "📈 Reports", "reports"),
    ("users", "👤 Users", "users"), ("settings", "⚙️ Settings", "users"),
    ("help", "📘 Help / Manual", "dashboard"),
]

# ===== Helpers for URL Params =====
def _get_query(key: str):
    try:
        qp = st.query_params
        val = qp.get(key)
        return val if val else None
    except Exception:
        return None

def _set_query(**kwargs):
    try:
        for k, v in kwargs.items():
            if v is None:
                if k in st.query_params: del st.query_params[k]
            else:
                st.query_params[k] = v
    except Exception:
        pass

# ===== AUTHENTICATION FLOW =====
user = st.session_state.get("user")

# ถ้าไม่มี user ใน session ให้ลองกู้คืนจาก URL Token
if not user:
    token = _get_query("token")
    if token:
        user = get_user_by_token(token)
        if user:
            st.session_state["user"] = user
            st.session_state["session_token"] = token
        else:
            # Token ไม่ถูกต้องหรือหมดอายุ
            st.error("Session expired. Please login again.")
            _set_query(token=None)

# ถ้ายังไม่มี user ให้แสดงหน้า Login
if not user:
    from views import login_view
    login_view.render()
    st.stop()

# หาก Login แล้ว เตรียมข้อมูลสำหรับแสดงผล
role = user.get("role", "")
session_token = st.session_state.get("session_token") or _get_query("token")

# ===== Sidebar & Navigation =====
setup_sidebar()
url_page = _get_query("page")
allowed_pages = [p[0] for p in PAGES if can_read(role, p[2])]
current_page = url_page if url_page in allowed_pages else (allowed_pages[0] if allowed_pages else "dashboard")

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
    
    # Navigation logic
    for page_id, label, module in PAGES:
        if not can_read(role, module): continue
        is_active = page_id == current_page
        href = f"?page={page_id}"
        if session_token: href += f"&token={session_token}"
        
        # ใช้ปุ่มแทน link เพื่อความเสถียรในบาง browser หรือใช้ a tag เดิม
        st.markdown(f'<a href="{href}" target="_self" class="{"nav-link active" if is_active else "nav-link"}">{label}</a>', unsafe_allow_html=True)

    st.markdown("---")
    if st.button("🚪 Sign Out", use_container_width=True):
        if session_token: delete_session(session_token)
        st.session_state.clear()
        _set_query(token=None, page=None)
        st.rerun()

# ===== Render Page Content =====
page_map = {
    "dashboard": "dashboard_view", "crm": "crm_view", "quotation": "quotation_view",
    "booking": "booking_view", "shipments": "shipments_view", "tracking": "tracking_view",
    "profit": "profit_view", "billing": "billing_view", "fx": "fx_manager", 
    "reports": "reports_view", "users": "users_view", "settings": "settings_view", "help": "help_view"
}

try:
    # นำเข้า view แบบไดนามิกตาม page_map
    module_name = page_map.get(current_page, "dashboard_view")
    view_module = __import__(f"views.{module_name}", fromlist=['render'])
    view_module.render()
except Exception as e:
    st.error(f"Error loading page: {e}")