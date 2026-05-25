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
# SAFE IMPORTS
# =========================================================
from database.connection import init_database
from managers.auth_manager import ROLE_LABELS, can_read
from managers.session_manager import delete_session, get_user_by_token
from utils.nav import setup_sidebar


# =========================================================
# BOOTSTRAP DATABASE (SAFE FOR SUPABASE)
# =========================================================
def bootstrap():
    try:
        init_database()
    except TypeError:
        init_database([])  # fallback for old schema

    # optional seed (safe ignore errors)
    try:
        from managers.fx_manager import seed_default_rates
        seed_default_rates()
    except Exception:
        pass

    try:
        from managers.db_persistence import push_if_dirty
        push_if_dirty()
    except Exception:
        pass


bootstrap()


# =========================================================
# SESSION RESTORE (SAFE + CLEAN)
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

    except Exception:
        return None


user = restore_session()

if not user:
    from views.login_view import render
    render()
    st.stop()


# =========================================================
# NAVIGATION CONFIG
# =========================================================
PAGES = [
    ("dashboard", "📊 Dashboard", "dashboard"),
    ("crm", "👥 CRM", "crm"),
    ("quotation", "📄 Quotation", "quotation"),
    ("booking", "📑 Booking", "booking"),
    ("shipments", "📦 Shipment", "shipment"),
    ("tracking", "📍 Tracking", "milestone"),
    ("profit", "📊 Profit Sheet", "profit"),
    ("billing", "💰 Billing", "billing"),
    ("fx", "💱 FX Rates", "fx"),
    ("reports", "📈 Reports", "reports"),
    ("users", "👤 Users", "users"),
    ("settings", "⚙️ Settings", "template"),
    ("help", "📘 Help / Manual", "session"),
]

role = user.get("role", "")
allowed_pages = [p for p in PAGES if can_read(role, p[2])]

if not allowed_pages:
    st.error("No pages available for this role")
    st.stop()

allowed_page_ids = [p[0] for p in allowed_pages]

current_page = st.query_params.get("page", "dashboard")

if current_page not in allowed_page_ids:
    current_page = allowed_page_ids[0]


# =========================================================
# SIDEBAR
# =========================================================
setup_sidebar()

with st.sidebar:

    st.markdown(
        f"""
        <div style="padding:1rem;border-radius:12px;
                    background:#111827;border:1px solid #374151;
                    margin-bottom:1rem;">
            <div style="font-size:1.2rem;font-weight:700;color:white;">
                🚢 Smart Freight NTT
            </div>
            <div style="font-size:0.85rem;color:#9CA3AF;margin-top:6px;">
                {user.get('full_name', 'User')}
            </div>
            <div style="font-size:0.75rem;color:#6B7280;">
                {ROLE_LABELS.get(role, role)}
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    # ===========================
    # NAV BUTTONS (FIXED UNIQUE KEY)
    # ===========================
    for page_id, label, module in allowed_pages:

        st.button(
            label,
            key=f"nav_{page_id}",
            use_container_width=True,
            type="primary" if current_page == page_id else "secondary",
            on_click=lambda p=page_id: st.query_params.__setitem__("page", p)
        )

    st.markdown("---")

    # ===========================
    # LOGOUT
    # ===========================
    if st.button("🚪 Sign Out", use_container_width=True, key="logout_btn"):
        if st.session_state.get("session_token"):
            delete_session(st.session_state["session_token"])

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

try:
    if current_page not in PAGE_ROUTES:
        st.warning("🚧 Page not found")

    else:
        module_path, fn_name = PAGE_ROUTES[current_page]

        with st.spinner(f"Loading {current_page.title()}..."):
            module = importlib.import_module(module_path)

            if not hasattr(module, fn_name):
                st.error(f"Missing function: {fn_name} in {module_path}")
                st.stop()

            render_fn = getattr(module, fn_name)
            render_fn()

except Exception as ex:
    st.error(f"❌ Error loading page `{current_page}`")

    with st.expander("🐞 Debug Error"):
        st.code(traceback.format_exc(), language="python")

    st.exception(ex)