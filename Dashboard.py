import traceback
import importlib
import streamlit as st

# =========================================================
# PAGE CONFIG
# =========================================================
st.set_page_config(
    page_title="Smart Freight NTT",
    page_icon="🚢",
    layout="wide",
    initial_sidebar_state="expanded",
)

# =========================================================
# IMPORTS SAFE (POSTGRES FRIENDLY)
# =========================================================
from managers.auth_manager import ROLE_LABELS, can_read
from managers.session_manager import delete_session, get_user_by_token

try:
    from database.connection import init_database
except Exception:
    init_database = None


# =========================================================
# SAFE DATABASE BOOTSTRAP (POSTGRES SAFE MODE)
# =========================================================
def bootstrap():

    if not init_database:
        st.warning("⚠️ Database module not loaded")
        return

    try:
        init_database()
    except Exception as e:
        # ❗ NEVER STOP APP FOR DB ERROR
        st.warning("⚠️ Database connection issue (app still running)")
        print("DB BOOT ERROR:", e)


bootstrap()


# =========================================================
# SESSION RESTORE
# =========================================================
def restore_session():

    if "user" in st.session_state:
        return st.session_state["user"]

    token = st.query_params.get("token")

    if not token:
        return None

    try:
        user = get_user_by_token(token)

        if not user:
            return None

        st.session_state["user"] = user
        st.session_state["session_token"] = token

        return user

    except Exception as e:
        print("SESSION ERROR:", e)
        return None


user = restore_session()

# =========================================================
# LOGIN GATE
# =========================================================
if not user:
    from views.login_view import render
    render()
    st.stop()


# =========================================================
# ERP MODULES (CLEAN ARCHITECTURE)
# =========================================================
PAGES = [
    ("dashboard", "📊 Dashboard", "dashboard"),

    ("crm", "👥 CRM", "crm"),

    ("quotation", "📄 Quotation", "quotation"),
    ("booking", "📑 Booking", "booking"),

    ("job", "📦 Shipments", "shipment"),

    ("tracking", "📍 Tracking", "tracking"),

    ("billing", "💰 Billing", "billing"),
    ("profit", "💹 Profit", "profit"),

    ("reports", "📈 Reports", "reports"),
    ("users", "👤 Users", "users"),
    ("settings", "⚙️ Settings", "settings"),
]


role = (user.get("role") or "admin").lower()

allowed_pages = [p for p in PAGES if can_read(role, p[2])]

if not allowed_pages:
    st.error("No pages available for this role")
    st.stop()

allowed_ids = [p[0] for p in allowed_pages]


# =========================================================
# SAFE PAGE PARAM (STREAMLIT FRIENDLY)
# =========================================================
query_params = st.query_params.to_dict()
current_page = query_params.get("page", allowed_ids[0])

if current_page not in allowed_ids:
    current_page = allowed_ids[0]


# =========================================================
# SIDEBAR UI (ENTERPRISE GRADE)
# =========================================================
with st.sidebar:

    st.markdown(f"""
    <div style="
        padding:18px;
        border-radius:16px;
        background:linear-gradient(135deg,#0F172A,#111827);
        border:1px solid #334155;
        margin-bottom:18px;
        color:white;
    ">
        <div style="font-size:18px;font-weight:800;">
            🚢 Smart Freight NTT
        </div>
        <div style="font-size:13px;color:#CBD5E1;margin-top:6px;">
            {user.get('full_name','User')}
        </div>
        <div style="font-size:11px;color:#94A3B8;">
            {ROLE_LABELS.get(role, role)}
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("### Navigation")

    for page_id, label, module in allowed_pages:

        active = (current_page == page_id)

        if st.button(
            label,
            key=f"nav_{page_id}",
            use_container_width=True,
            type="primary" if active else "secondary"
        ):
            st.query_params["page"] = page_id
            st.rerun()

    st.markdown("---")

    if st.button("🚪 Logout", use_container_width=True):

        try:
            token = st.session_state.get("session_token")
            if token:
                delete_session(token)
        except Exception as e:
            print("LOGOUT ERROR:", e)

        st.session_state.clear()
        st.query_params.clear()
        st.rerun()


# =========================================================
# PAGE ROUTER (SAFE IMPORT)
# =========================================================
PAGE_ROUTES = {
    p[0]: (f"views.{p[2]}_view", "render")
    for p in PAGES
}


# =========================================================
# HEADER UI (CLEAN ERP STYLE)
# =========================================================
st.markdown(f"""
<style>

/* =========================
   GLOBAL BACKGROUND (SaaS STYLE)
   ========================= */
.stApp {{
    background: radial-gradient(circle at 20% 20%, #f8fafc 0%, #f1f5f9 40%, #eef2ff 100%);
}}

/* subtle grid overlay */
.stApp::before {{
    content: "";
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background-image: linear-gradient(rgba(0,0,0,0.03) 1px, transparent 1px),
                      linear-gradient(90deg, rgba(0,0,0,0.03) 1px, transparent 1px);
    background-size: 40px 40px;
    pointer-events: none;
    z-index: 0;
}}

/* keep content above background */
.block-container {{
    position: relative;
    z-index: 1;
}}

/* =========================
   HEADER CARD (GLASS STYLE)
   ========================= */
.page-header {{
    padding: 18px 20px;
    border-radius: 16px;
    border: 1px solid rgba(255,255,255,0.6);
    background: rgba(255,255,255,0.75);
    backdrop-filter: blur(10px);
    box-shadow: 0 8px 24px rgba(0,0,0,0.06);
    margin-bottom: 16px;
}}

.page-title {{
    font-size: 24px;
    font-weight: 800;
    color: #111827;
    letter-spacing: -0.3px;
}}

.page-subtitle {{
    font-size: 13px;
    color: #6B7280;
    margin-top: 4px;
}}

</style>
""", unsafe_allow_html=True)


# =========================================================
# HEADER UI
# =========================================================
st.markdown(f"""
<div class="page-header">
    <div class="page-title">
        {current_page.replace('_',' ').title()}
    </div>
    <div class="page-subtitle">
        Smart Freight ERP Platform • PostgreSQL Edition
    </div>
</div>
""", unsafe_allow_html=True)


# =========================================================
# SAFE MODULE LOADER
# =========================================================
try:

    if current_page not in PAGE_ROUTES:
        st.warning("Page not found")
        st.stop()

    module_path, fn_name = PAGE_ROUTES[current_page]

    with st.spinner(f"Loading {current_page.title()}..."):

        module = importlib.import_module(module_path)

        if not hasattr(module, fn_name):
            st.error(f"Missing function: {fn_name} in {module_path}")
            st.stop()

        render_fn = getattr(module, fn_name)
        render_fn()

except Exception as e:

    st.error(f"Error loading page: {current_page}")

    with st.expander("Debug Error"):
        st.code(traceback.format_exc(), language="python")

    st.exception(e)