import traceback
import importlib
import streamlit as st

from managers.auth_manager import ROLE_LABELS, can_read
from managers.session_manager import delete_session, get_user_by_token
from database.connection import init_database, get_connection
from database.local_schema_compat import ensure_phase30_local_schema
from database.party_finance_compat import ensure_party_finance_schema
from ui.design_system import apply_theme, page_header

BUILD_ID = "PHASE30-CONSOLIDATED-20260817"

st.set_page_config(page_title="Smart Freight NTT", page_icon="🚢", layout="wide", initial_sidebar_state="expanded")
apply_theme()

ERP_MODULES = {
    "EXECUTIVE": [("dashboard", "Home", "dashboard"), ("reports", "Reports", "reports")],
    "DATA": [("data", "Master Data", "settings")],
    "SALES": [("quotation", "Quotations", "quotation")],
    "OPERATIONS": [("booking", "Bookings", "booking"), ("job_control", "Jobs", "shipment"), ("bl", "Bills of Lading", "bl")],
    "DOCUMENTS": [("document", "Documents", "document")],
    "FINANCE": [
        ("billing", "Receipt & Billing (AR)", "billing"),
        ("ap", "Payment Voucher (AP)", "ap"),
        ("ar", "Financial Control & Tax", "billing"),
        ("profit", "Profitability", "profit"),
    ],
    "ADMIN": [("users", "Users", "users"), ("settings", "Settings", "settings"), ("health", "System Health", "system_health")],
}
PAGE_ROUTES = {page_id: (f"views.{module_name}_view", "render") for modules in ERP_MODULES.values() for page_id, _label, module_name in modules}
PAGE_ROUTES["booking"] = ("views.booking_v2_view", "render")
PAGE_ROUTES["quotation"] = ("views.quotation_v2_view", "render")
PAGE_ROUTES["bl"] = ("views.bl_v2_view", "render")
PAGE_ROUTES["billing"] = ("views.finance_document_workspace", "render")
PAGE_ROUTES["ap"] = ("views.ap_view", "render")
PAGE_ROUTES["ar"] = ("views.ar_ap_workspace", "render")
PAGE_ROUTES["document"] = ("views.document_v2_view", "render")
PAGE_ROUTES["health"] = ("views.system_health_view", "render")
PAGE_ROUTES["data"] = ("views.master_data_view", "render")
PAGE_ROUTES["crm"] = ("views.customer_master_view", "render")
PAGE_ROUTES["rates"] = ("views.rate_master_view", "render")
PAGE_ROUTES["handover"] = ("views.job_handover_view", "render")


def _restore_user():
    user = st.session_state.get("user")
    if user:
        return user
    token = st.query_params.get("token")
    if not token:
        return None
    try:
        user = get_user_by_token(token)
    except Exception:
        return None
    if user:
        st.session_state["user"] = user
        st.session_state["session_token"] = token
    return user


@st.cache_resource(show_spinner=False)
def _bootstrap_db_cached():
    try:
        init_database()
        ensure_phase30_local_schema()
        with get_connection() as conn:
            ensure_party_finance_schema(conn, sqlite=(type(conn).__name__ == "SQLiteConnAdapter"))
        return True
    except Exception as exc:
        print(f"[DB BOOT ERROR] {exc}")
        return False


def _bootstrap_db():
    return _bootstrap_db_cached()


def _allowed_pages(role: str):
    return [(g, [m for m in modules if can_read(role, m[2])]) for g, modules in ERP_MODULES.items() if any(can_read(role, m[2]) for m in modules)]


def _sync_navigation(allowed_ids):
    query_page = st.query_params.get("page")
    current = st.session_state.get("current_navigation")
    if query_page in allowed_ids:
        current = query_page
    if current not in allowed_ids:
        current = "dashboard" if "dashboard" in allowed_ids else allowed_ids[0]
    st.session_state["current_navigation"] = current
    st.query_params["page"] = current
    return current


def main():
    for k in list(st.session_state.keys()):
        if str(k).startswith("_rendered_hdr_"):
            del st.session_state[k]
    _bootstrap_db()
    user = _restore_user()
    if not user:
        try:
            from views.login_view import render as render_login
            render_login()
        except Exception as exc:
            st.error("Authentication service is unavailable.")
            st.code(str(exc), language="text")
        st.stop()
    role = str(user.get("role", "guest")).lower()
    groups = _allowed_pages(role)
    allowed_ids = [page_id for _group, modules in groups for page_id, _label, _module in modules]
    current_page = _sync_navigation(allowed_ids)
    with st.sidebar:
        st.markdown("**SMART FREIGHT NTT**")
        st.caption(f"{user.get('full_name', 'Operator')} · {ROLE_LABELS.get(role, role.upper())}")
        st.caption(BUILD_ID)
        st.divider()
        for group, modules in groups:
            st.caption(group.title())
            for page_id, label, _module in modules:
                if st.button(label, key=f"nav_{page_id}", width="stretch", type="primary" if page_id == current_page else "secondary"):
                    st.session_state["current_navigation"] = page_id
                    st.query_params["page"] = page_id
                    st.rerun()
        st.divider()
        if st.button("Log out", width="stretch", key="nav_logout"):
            try:
                token = st.session_state.get("session_token")
                if token:
                    delete_session(token)
            finally:
                st.session_state.clear()
                st.query_params.clear()
                st.rerun()
    page_header(current_page, status_text="Online")
    module_path, fn_name = PAGE_ROUTES.get(current_page, PAGE_ROUTES["dashboard"])
    try:
        module = importlib.import_module(module_path)
        getattr(module, fn_name)()
    except Exception as exc:
        st.error("Unable to load this workspace.")
        st.code(traceback.format_exc(), language="text")


if __name__ == "__main__":
    main()