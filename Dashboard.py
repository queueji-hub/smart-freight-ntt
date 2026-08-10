import traceback
import importlib
import streamlit as st

# =========================================================
# PAGE CONFIG (ENTERPRISE STANDARD)
# =========================================================
st.set_page_config(
    page_title="Smart Freight NTT, | Enterprise Logistics ERP",
    page_icon="🚢",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS to global elements for professional look & feel
st.markdown("""
<style>
    /* Main Content Padding Optimization */
    .block-container {
        padding-top: 1.5rem !important;
        padding-bottom: 2rem !important;
    }
    /* Metric Card Polish */
    div[data-testid="stMetric"] {
        background-color: #0F172A;
        border: 1px solid #1E293B;
        padding: 1rem 1.25rem !important;
        border-radius: 12px !important;
        box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1);
    }
    div[data-testid="stMetric"] label {
        color: #94A3B8 !important;
        font-size: 0.85rem !important;
        font-weight: 600 !important;
        text-transform: uppercase !important;
        letter-spacing: 0.05em !important;
    }
    div[data-testid="stMetric"] div[data-testid="stMetricValue"] {
        color: #F8FAFC !important;
        font-size: 1.75rem !important;
        font-weight: 700 !important;
    }
</style>
""", unsafe_allow_html=True)

# =========================================================
# IMPORTS SAFE (POSTGRESQL & SERVICE LAYER)
# =========================================================
try:
    from managers.auth_manager import ROLE_LABELS, can_read
    from managers.session_manager import delete_session, get_user_by_token
except ImportError as ie:
    st.error(f"❌ Critical Component Missing: {str(ie)}")
    st.stop()

try:
    from database.connection import init_database
except ImportError:
    init_database = None


# =========================================================
# SAFE DATABASE BOOTSTRAP (POSTGRES RESILIENT MODE)
# =========================================================
def bootstrap():
    if not init_database:
        st.sidebar.error("⚠️ Database connection module could not be initialized.")
        return False
    try:
        init_database()
        return True
    except Exception as e:
        # Resilient implementation: Application keeps running with descriptive fallback warnings
        st.sidebar.warning("⚠️ PostgreSQL Connection Failure. Operating in offline/degraded mode.")
        print(f"[CRITICAL] DB BOOT ERROR (PostgreSQL): {str(e)}")
        return False


is_db_connected = bootstrap()


# =========================================================
# ROUTINE SESSION RESTORE
# =========================================================
def restore_session():
    if "user" in st.session_state:
        return st.session_state["user"]

    token = st.query_params.get("token")
    if not token:
        return None

    try:
        user_record = get_user_by_token(token)
        if not user_record:
            return None

        st.session_state["user"] = user_record
        st.session_state["session_token"] = token
        return user_record
    except Exception as e:
        print(f"[SESSION RESTORE ERROR]: {str(e)}")
        return None


user = restore_session()

# =========================================================
# SECURITY & AUTHENTICATION GATE
# =========================================================
if not user:
    try:
        from views.login_view import render as render_login
        render_login()
    except Exception as e:
        st.error("Authentication Service Unavailable.")
        st.code(str(e), language="python")
    st.stop()


# =========================================================
# ERP REPOSITORIES & ACCESS CONTROL
# =========================================================
PAGES = [
    ("dashboard", "📊 Dashboard", "dashboard"),
    ("crm", "👥 Customers", "crm"),
    ("quotation", "📄 Quotation", "quotation"),
    ("booking", "📑 Booking", "booking"),
    ("job", "📦 Shipments", "shipment"),
    ("bl", "📜 Bill of Lading", "bl"),
    ("tracking", "📍 Tracking", "tracking"),
    ("billing", "💰 Billing", "billing"),
    ("profit", "💹 Profit Analysis", "profit"),
    ("reports", "📈 Reports", "reports"),
    ("users", "👤 Users", "users"),
    ("settings", "⚙️ Settings", "settings"),
]

user_role = str(user.get("role", "guest")).lower()
allowed_pages = [p for p in PAGES if can_read(user_role, p[2])]

if not allowed_pages:
    st.error("🔒 Access Denied: Your account role does not have viewing permissions for this platform.")
    st.stop()

allowed_ids = [p[0] for p in allowed_pages]

# Extract routing metadata safely
query_params = st.query_params.to_dict()
current_page = query_params.get("page", allowed_ids[0])

if current_page not in allowed_ids:
    current_page = allowed_ids[0]


# =========================================================
# SIDEBAR UI (CARGOWISE METRO STYLE)
# =========================================================
with st.sidebar:
    # Corporate Identity Header Card
    st.markdown(f"""
    <div style="
        padding: 20px;
        border-radius: 14px;
        background: linear-gradient(135deg, #1E293B, #0F172A);
        border: 1px solid #334155;
        margin-bottom: 24px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    ">
        <div style="font-size: 20px; font-weight: 800; color: #F8FAFC; letter-spacing: -0.5px; display: flex; align-items: center; gap: 8px;">
            <span>🚢</span> Smart Freight NTT,
        </div>
        <div style="height: 1px; background: #334155; margin: 12px 0;"></div>
        <div style="font-size: 14px; font-weight: 600; color: #E2E8F0; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">
            {user.get('full_name', 'Operator Active')}
        </div>
        <div style="font-size: 11px; color: #38BDF8; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px; margin-top: 2px;">
            ⚙️ {ROLE_LABELS.get(user_role, user_role.upper())}
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<p style='color:#64748B; font-weight:700; font-size:11px; text-transform:uppercase; letter-spacing:1px; margin-bottom:8px;'>Navigation Matrix</p>", unsafe_allow_html=True)

    # Menu Router Action Buttons
    for page_id, label, module in allowed_pages:
        is_active = (current_page == page_id)
        
        if st.button(
            label,
            key=f"nav_btn_{page_id}",
            use_container_width=True,
            type="primary" if is_active else "secondary"
        ):
            st.query_params["page"] = page_id
            st.rerun()

    st.markdown("<div style='margin-top: 30px;'></div>", unsafe_allow_html=True)
    st.markdown("---")

    # Logout Engine Execution
    if st.button("🚪 System Terminate (Logout)", use_container_width=True):
        try:
            active_token = st.session_state.get("session_token")
            if active_token:
                delete_session(active_token)
        except Exception as e:
            print(f"[LOGOUT EXCEPTION]: {str(e)}")

        st.session_state.clear()
        st.query_params.clear()
        st.rerun()


# =========================================================
# CENTRAL PAGE HEADER COMPONENT
# =========================================================
page_title_text = current_page.replace('_', ' ').title()
st.markdown(f"""
<div style="
    padding: 20px 24px;
    border-radius: 14px;
    background: linear-gradient(90deg, #0F172A 0%, #1E293B 100%);
    border: 1px solid #1E293B;
    margin-bottom: 24px;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.2);
">
    <div style="display: flex; justify-content: space-between; align-items: center;">
        <div>
            <h1 style="font-size: 24px; font-weight: 800; color: #F8FAFC; margin: 0; letter-spacing: -0.5px;">
                {page_title_text}
            </h1>
            <p style="color: #94A3B8; font-size: 13px; margin: 4px 0 0 0; letter-spacing: 0.2px;">
                Enterprise Logistics ERP System
            </p>
        </div>
        <div style="background: rgba(56, 189, 248, 0.1); border: 1px solid rgba(56, 189, 248, 0.2); padding: 6px 12px; border-radius: 20px; color: #38BDF8; font-size: 11px; font-weight: 700; text-transform: uppercase;">
            🟢 System Online
        </div>
    </div>
</div>
""", unsafe_allow_html=True)


# =========================================================
# ASYNCHRONOUS SAFE VIEW MODULE DYNAMIC ROUTER
# =========================================================
PAGE_ROUTES = {p[0]: (f"views.{p[2]}_view", "render") for p in PAGES}

if current_page not in PAGE_ROUTES:
    st.error("🎯 Resource Execution Failure: Target context router location mismatch.")
    st.stop()

module_path, fn_name = PAGE_ROUTES[current_page]

try:
    view_module = importlib.import_module(module_path)
    
    if not hasattr(view_module, fn_name):
        st.error(f"❌ Compilation Error: View module missing expected entrypoint '{fn_name}'")
        st.stop()
        
    render_target = getattr(view_module, fn_name)
    render_target()

except Exception as view_exec_err:
    st.error("🚨 Critical Crash Intercepted inside Runtime Pipeline View")
    
    with st.expander("Diagnostic Traceback Logs", expanded=True):
        st.code(traceback.format_exc(), language="python")
    
    st.exception(view_exec_err)