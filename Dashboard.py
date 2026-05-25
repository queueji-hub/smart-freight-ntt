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
<div style="
padding:16px 18px;
border-radius:16px;
background:#1C222F;
border:1px solid rgba(255,255,255,0.06);
margin-bottom:14px;
box-shadow:0 14px 40px rgba(0,0,0,0.65), inset 0 1px 0 rgba(255,255,255,0.03);
">
<div style="
font-size:22px;
font-weight:800;
color:#F8FAFC;
letter-spacing:-0.4px;
">
{current_page.replace('_',' ').title()}
</div>

<div style="
color:#94A3B8;
font-size:13px;
margin-top:6px;
letter-spacing:0.2px;
opacity:0.9;
">
Smart Freight ERP Platform
</div>
</div>
""", unsafe_allow_html=True)


# =========================================================
# SAFE MODULE LOADER (POSTGRES SAFE)
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