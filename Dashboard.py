"""Smart Freight NTT - Multi-module Freight Forwarding Operating System."""
import streamlit as st
import traceback

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

try:
    from managers.db_persistence import push_if_dirty
    push_if_dirty()
except Exception:
    pass

# ===== AUTHENTICATION FLOW =====
# 1. เช็ค Session State เป็นหลัก
user = st.session_state.get("user")

# 2. ถ้าหลุด ให้ดึงจาก Token ใน URL
if not user:
    token = st.query_params.get("token")
    if token:
        user = get_user_by_token(token)
        if user:
            st.session_state["user"] = user
            st.session_state["session_token"] = token
        else:
            st.error("Session expired or invalid. Please login again.")
            if "token" in st.query_params:
                del st.query_params["token"]

# 3. ถ้ายังไม่มี user ให้ไปหน้า Login ทันที
if not user:
    from views import login_view
    login_view.render()
    st.stop()

# ===== App State (Logged In) =====
role = user.get("role", "")
session_token = st.session_state.get("session_token")

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

# กรองเฉพาะหน้าที่ user มีสิทธิ์เข้าถึง
allowed_pages = [p for p in PAGES if can_read(role, p[2])]
allowed_page_ids = [p[0] for p in allowed_pages]

current_page = st.query_params.get("page", "dashboard")
if current_page not in allowed_page_ids:
    current_page = allowed_page_ids[0] if allowed_page_ids else "dashboard"

# ===== Sidebar & Navigation =====
setup_sidebar()

with st.sidebar:
    st.markdown(f"""
    <div style='padding:0.5rem 0; margin-bottom:1rem;'>
        <div style='font-size:1.1rem;font-weight:700'>🚢 Smart Freight NTT</div>
        <div style='font-size:0.75rem;color:#9CA0A8;margin-top:2px'>
            {user.get('full_name','User')} · {ROLE_LABELS.get(role, role)}
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # ใช้ Native Button ของ Streamlit แทน HTML <a> tag ป้องกันการ Hard Reload
    for page_id, label, module in allowed_pages:
        # ทำให้ปุ่มหน้าที่กำลังเปิดอยู่เป็นสีเด่น (primary)
        btn_type = "primary" if current_page == page_id else "secondary"
        if st.button(label, key=f"nav_{page_id}", use_container_width=True, type=btn_type):
            st.query_params["page"] = page_id
            st.rerun()

    st.markdown("---")
    if st.button("🚪 Sign Out", use_container_width=True):
        if session_token:
            try:
                delete_session(session_token)
            except:
                pass
        st.session_state.clear()
        st.query_params.clear()
        st.rerun()

# ===== Render Page Content =====
try:
    if current_page == "dashboard":
        from views import dashboard_view
        dashboard_view.render