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
# CUSTOM PROFESSIONAL UI
# =========================================================
st.markdown("""
<style>

/* =====================================================
GLOBAL
===================================================== */

.block-container{
    padding-top: 1.2rem;
    padding-bottom: 1rem;
}

html, body, [class*="css"] {
    font-family: "Inter", sans-serif;
}

/* =====================================================
SIDEBAR
===================================================== */

section[data-testid="stSidebar"]{
    background: linear-gradient(
        180deg,
        #0F172A 0%,
        #111827 100%
    );
    border-right: 1px solid #1F2937;
}

section[data-testid="stSidebar"] *{
    color: white;
}

/* =====================================================
BUTTONS
===================================================== */

.stButton > button{
    border-radius: 12px;
    height: 48px;
    border: 1px solid #374151;
    background: #111827;
    color: white;
    font-weight: 600;
    transition: all 0.2s ease;
}

.stButton > button:hover{
    border: 1px solid #2563EB;
    background: #1E293B;
    color: white;
}

/* =====================================================
METRIC CARD
===================================================== */

.metric-card{
    background: white;
    padding: 1rem;
    border-radius: 18px;
    border: 1px solid #E5E7EB;
    box-shadow: 0 1px 2px rgba(0,0,0,0.04);
}

/* =====================================================
HIDE STREAMLIT
===================================================== */

#MainMenu{
    visibility:hidden;
}

footer{
    visibility:hidden;
}

header{
    visibility:hidden;
}

</style>
""", unsafe_allow_html=True)

# =========================================================
# SAFE IMPORTS
# =========================================================
from database.connection import init_database
from managers.auth_manager import ROLE_LABELS, can_read
from managers.session_manager import (
    delete_session,
    get_user_by_token
)

# =========================================================
# SAFE OPTIONAL IMPORT
# =========================================================
try:
    from utils.nav import setup_sidebar
except Exception:
    def setup_sidebar():
        pass


# =========================================================
# BOOTSTRAP DATABASE
# =========================================================
def bootstrap():

    try:
        init_database()
        print("✅ Database initialized")

    except Exception as e:
        st.error("❌ Database bootstrap failed")
        st.exception(e)
        st.stop()

    # =====================================================
    # OPTIONAL MODULES
    # =====================================================
    try:
        from managers.fx_manager import seed_default_rates
        seed_default_rates()

    except Exception as e:
        print("FX seed skipped:", e)

    try:
        from managers.db_persistence import push_if_dirty
        push_if_dirty()

    except Exception as e:
        print("DB persistence skipped:", e)


# =========================================================
# START SYSTEM
# =========================================================
bootstrap()


# =========================================================
# RESTORE SESSION
# =========================================================
def restore_session():

    try:

        # =============================================
        # EXISTING SESSION
        # =============================================
        if "user" in st.session_state:
            return st.session_state["user"]

        # =============================================
        # TOKEN FROM URL
        # =============================================
        token = st.query_params.get("token")

        if not token:
            return None

        user = get_user_by_token(token)

        if not user:
            return None

        st.session_state["user"] = user
        st.session_state["session_token"] = token

        return user

    except Exception as e:

        print("RESTORE SESSION ERROR:", e)
        return None


# =========================================================
# GET USER
# =========================================================
user = restore_session()


# =========================================================
# LOGIN SCREEN
# =========================================================
if not user:

    try:

        from views.login_view import render

        render()

    except Exception as e:

        st.error("❌ Login page failed")

        with st.expander("🐞 Debug Login Error"):
            st.code(traceback.format_exc())

        st.exception(e)

    st.stop()


# =========================================================
# PAGE CONFIGURATION
# =========================================================
PAGES = [

    ("dashboard", "📊 Dashboard", "dashboard"),

    ("crm", "👥 CRM", "crm"),

    ("quotation", "📄 Quotation", "quotation"),

    ("booking", "📑 Booking", "booking"),

    ("shipments", "📦 Shipments", "shipment"),

    ("tracking", "📍 Tracking", "tracking"),

    ("profit", "📊 Profit Sheet", "profit"),

    ("billing", "💰 Billing", "billing"),

    ("fx", "💱 FX Rates", "fx"),

    ("reports", "📈 Reports", "reports"),

    ("users", "👤 User Management", "users"),

    ("settings", "⚙️ Settings", "settings"),

    ("help", "📘 Help Center", "help"),
]


# =========================================================
# USER ROLE
# =========================================================
role = str(user.get("role", "")).lower()

allowed_pages = [
    p for p in PAGES
    if can_read(role, p[2])
]

if not allowed_pages:

    st.error("⚠️ No pages available for this account")
    st.stop()

allowed_page_ids = [p[0] for p in allowed_pages]


# =========================================================
# CURRENT PAGE
# =========================================================
current_page = st.query_params.get(
    "page",
    allowed_page_ids[0]
)

if current_page not in allowed_page_ids:
    current_page = allowed_page_ids[0]


# =========================================================
# SIDEBAR SETUP
# =========================================================
setup_sidebar()


# =========================================================
# SIDEBAR UI
# =========================================================
with st.sidebar:

    st.markdown(
        f"""
        <div style="
            padding:1.2rem;
            border-radius:18px;
            background:linear-gradient(
                135deg,
                #1E293B 0%,
                #0F172A 100%
            );
            border:1px solid #334155;
            margin-bottom:1rem;
            box-shadow:0 10px 25px rgba(0,0,0,0.25);
        ">

            <div style="
                font-size:1.35rem;
                font-weight:800;
                color:white;
                margin-bottom:8px;
            ">
                🚢 Smart Freight NTT
            </div>

            <div style="
                font-size:0.9rem;
                color:#CBD5E1;
                font-weight:600;
            ">
                {user.get('full_name', 'User')}
            </div>

            <div style="
                font-size:0.78rem;
                color:#94A3B8;
                margin-top:4px;
            ">
                {ROLE_LABELS.get(role, role.title())}
            </div>

        </div>
        """,
        unsafe_allow_html=True
    )

    st.markdown("### 📂 Navigation")

    # =====================================================
    # NAVIGATION BUTTONS
    # =====================================================
    for page_id, label, module_name in allowed_pages:

        is_active = current_page == page_id

        st.button(
            label,
            key=f"nav_{page_id}",
            use_container_width=True,
            type="primary" if is_active else "secondary",
            on_click=lambda p=page_id:
                st.query_params.__setitem__("page", p)
        )

    st.markdown("---")

    # =====================================================
    # SYSTEM INFO
    # =====================================================
    st.caption("Smart Freight ERP")
    st.caption("Version 1.0 Enterprise")

    st.markdown("---")

    # =====================================================
    # LOGOUT
    # =====================================================
    if st.button(
        "🚪 Sign Out",
        use_container_width=True,
        key="logout_btn"
    ):

        try:

            token = st.session_state.get("session_token")

            if token:
                delete_session(token)

        except Exception as e:

            print("DELETE SESSION ERROR:", e)

        st.session_state.clear()

        st.query_params.clear()

        st.rerun()


# =========================================================
# PAGE ROUTES
# =========================================================
PAGE_ROUTES = {
    p[0]: (
        f"views.{p[2]}_view",
        "render"
    )
    for p in PAGES
}


# =========================================================
# MAIN CONTENT HEADER
# =========================================================
page_title = current_page.replace("_", " ").title()

st.markdown(
    f"""
    <div style="
        background:white;
        border:1px solid #E5E7EB;
        border-radius:18px;
        padding:1.25rem 1.5rem;
        margin-bottom:1rem;
        box-shadow:0 1px 3px rgba(0,0,0,0.05);
    ">

        <div style="
            font-size:1.8rem;
            font-weight:800;
            color:#111827;
        ">
            {page_title}
        </div>

        <div style="
            color:#6B7280;
            margin-top:4px;
            font-size:0.95rem;
        ">
            Smart Freight Management Platform
        </div>

    </div>
    """,
    unsafe_allow_html=True
)


# =========================================================
# SAFE PAGE LOADER
# =========================================================
try:

    if current_page not in PAGE_ROUTES:

        st.warning("🚧 Page not found")
        st.stop()

    module_path, fn_name = PAGE_ROUTES[current_page]

    with st.spinner(f"Loading {page_title}..."):

        module = importlib.import_module(module_path)

        if not hasattr(module, fn_name):

            st.error(
                f"❌ Missing function `{fn_name}` "
                f"in `{module_path}`"
            )

            st.stop()

        render_fn = getattr(module, fn_name)

        render_fn()

except Exception as ex:

    st.error(
        f"❌ Error loading page `{current_page}`"
    )

    with st.expander("🐞 Full Debug Error"):

        st.code(
            traceback.format_exc(),
            language="python"
        )

    st.exception(ex)