"""Smart Freight NTT - Multi-module Freight Forwarding Operating System."""
import streamlit as st

st.set_page_config(
    page_title="Smart Freight NTT",
    page_icon="🚢",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- Imports ---
from database.connection import init_database
from utils.nav import setup_sidebar
from managers.auth_manager import can_read, ROLE_LABELS
from managers.session_manager import get_user_by_token, delete_session

# --- Init ---
@st.cache_resource
def _init_db():
    init_database()
    return True

_init_db()

# --- Auth Helper ---
def _get_query_param(key):
    return st.query_params.get(key)

# --- Authentication Logic ---
# 1. ตรวจสอบว่ามี user ใน session หรือไม่
if "user" not in st.session_state:
    token = _get_query_param("token")
    if token:
        user_data = get_user_by_token(token)
        if user_data:
            st.session_state["user"] = user_data
            st.session_state["session_token"] = token
        else:
            st.error("Session expired. Please login again.")
    else:
        # ถ้าไม่มี token และไม่มี session ให้ไปหน้า login
        from views import login_view
        login_view.render()
        st.stop()

# หากผ่านจุดนี้แสดงว่า Login แล้ว
user = st.session_state["user"]
role = user.get("role", "")
session_token = st.session_state.get("session_token")

# --- UI Setup ---
setup_sidebar()
current_page = _get_query_param("page") or "dashboard"

with st.sidebar:
    st.markdown(f"### 🚢 Smart Freight NTT\n**{user.get('full_name')}** ({ROLE_LABELS.get(role, role)})")
    st.markdown("---")
    
    # Navigation
    PAGES = [("dashboard", "📊 Dashboard"), ("crm", "👥 CRM"), ("booking", "📑 Booking"), ("users", "👤 Users")]
    for p_id, label in PAGES:
        if st.button(label, use_container_width=True):
            st.query_params["page"] = p_id
            st.rerun()

    if st.button("🚪 Sign Out"):
        delete_session(session_token)
        st.session_state.clear()
        st.query_params.clear()
        st.rerun()

# --- Page Rendering ---
try:
    if current_page == "dashboard":
        from views import dashboard_view
        dashboard_view.render()
    elif current_page == "users":
        from views import users_view
        users_view.render()
    # เพิ่ม page อื่นๆ ตามนี้
    else:
        st.write("Welcome to the Dashboard")
except Exception as e:
    st.error(f"Error loading page: {e}")