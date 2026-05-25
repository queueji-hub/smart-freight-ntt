import importlib
import traceback
import streamlit as st

# =========================================================
# PAGE HEADER (PROFESSIONAL UI BLOCK)
# =========================================================
def render_page_header(current_page: str):
    title = current_page.replace("_", " ").title()

    st.markdown(f"""
    <div style="
        padding:16px 18px;
        border-radius:14px;
        border:1px solid #E5E7EB;
        background: linear-gradient(135deg, #ffffff, #f9fafb);
        margin-bottom:14px;
        box-shadow:0 2px 6px rgba(0,0,0,0.06);
    ">
        <div style="font-size:24px;font-weight:800;color:#111827;">
            {title}
        </div>
        <div style="color:#6B7280;font-size:13px;margin-top:2px;">
            Smart Freight ERP Platform • PostgreSQL Edition
        </div>
    </div>
    """, unsafe_allow_html=True)


# =========================================================
# SAFE PAGE LOADER (POSTGRES READY ARCHITECTURE)
# =========================================================
def load_page(current_page: str, PAGE_ROUTES: dict):
    """
    Production-safe page loader:
    - PostgreSQL-ready architecture (stateless pages)
    - module isolation
    - safe error handling
    """

    render_page_header(current_page)

    try:
        # -------------------------
        # Validate route
        # -------------------------
        if current_page not in PAGE_ROUTES:
            st.error("❌ Page not found in routing table")
            st.stop()

        module_path, fn_name = PAGE_ROUTES[current_page]

        # -------------------------
        # Load module dynamically
        # -------------------------
        with st.spinner(f"Loading {current_page.replace('_',' ').title()}..."):

            module = importlib.import_module(module_path)

            if not hasattr(module, fn_name):
                st.error(f"❌ Missing function: {fn_name} in {module_path}")
                st.stop()

            render_fn = getattr(module, fn_name)

            # -------------------------
            # Execute page safely
            # -------------------------
            render_fn()

    except Exception as e:
        st.error("⚠️ System Error occurred while loading page")

        with st.expander("🔧 Debug Information", expanded=False):
            st.code(traceback.format_exc(), language="python")

        # show raw exception only in dev mode
        if st.secrets.get("ENV", "prod") == "dev":
            st.exception(e)


# =========================================================
# OPTIONAL: POSTGRES SAFE SESSION HOOK (RECOMMENDED)
# =========================================================
def get_app_context():
    """
    Central place for shared runtime context
    (PostgreSQL-safe architecture pattern)
    """

    if "app_context" not in st.session_state:
        st.session_state.app_context = {
            "db_type": "postgresql",
            "connection_pool": None,
            "user": st.session_state.get("user"),
        }

    return st.session_state.app_context