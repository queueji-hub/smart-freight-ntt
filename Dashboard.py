import traceback
import importlib
import streamlit as st

from managers.auth_manager import ROLE_LABELS, can_read
from managers.session_manager import delete_session, get_user_by_token
from database.connection import init_database
from ui.design_system import apply_theme, page_header

st.set_page_config(
    page_title="Smart Freight NTT",
    page_icon="🚢",
    layout="wide",
    initial_sidebar_state="expanded",
)
apply_theme()

ERP_MODULES = {
    "EXECUTIVE": [
        ("dashboard", "Home", "dashboard"),
        ("reports", "Reports", "reports"),
    ],
    "SALES": [
        ("crm", "Customers", "crm"),
        ("quotation", "Quotations", "quotation"),
        ("booking", "Bookings", "booking"),
    ],
    "OPERATIONS": [
        ("job_control", "Jobs", "shipment"),
        ("bl", "Bills of Lading", "bl"),
    ],
    "DOCUMENTS": [
        ("document", "Documents", "document"),
    ],
    "FINANCE": [
        ("billing", "Finance", "billing"),
        ("ap", "Payables", "ap"),
        ("profit", "Profitability", "profit"),
    ],
    "ADMIN": [
        ("users", "Users", "users"),
        ("settings", "Settings", "settings"),
    ],
}

PAGE_ROUTES = {
    page_id: (f"views.{module_name}_view", "render")
    for modules in ERP_MODULES.values()
    for page_id, _label, module_name in modules
}
# Phase 30: use the streamlined booking workspace while keeping the
# canonical page id/permission key unchanged.
PAGE_ROUTES["booking"] = ("views.booking_v2_view", "render")


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


def _bootstrap_db():
    try:
        init_database()
        return True
    except Exception as exc:
        st.sidebar.warning("Database connection is unavailable.")
        print(f"[DB BOOT ERROR] {exc}")
        return False


def _allowed_pages(role: str):
    pages = []
    for group, modules in ERP_MODULES.items():
        allowed = [m for m in modules if can_read(role, m[2])]
        if allowed:
            pages.append((group, allowed))
    return pages


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
        st.divider()
        for group, modules in groups:
            st.caption(group.title())
            for page_id, label, _module in modules:
                if st.button(
                    label,
                    key=f"nav_{page_id}",
                    width="stretch",
                    type="primary" if page_id == current_page else "secondary",
                ):
                    st.session_state["current_navigation"] = page_id
                    st.query_params["page"] = page_id
                    st.rerun()
        st.divider()
        if st.button("Log out", width="stretch"):
            try:
                token = st.session_state.get("session_token")
                if token:
                    delete_session(token)
            finally:
                st.session_state.clear()
                st.query_params.clear()
                st.rerun()

    page_header(current_page, status_text="Online")

    module_path, fn_name = PAGE_ROUTES[current_page]
    try:
        module = importlib.import_module(module_path)
        renderer = getattr(module, fn_name, None)
        if not renderer:
            st.error(f"View entrypoint '{fn_name}' is missing.")
            st.stop()
        renderer()
    except Exception as exc:
        st.error("Unable to load this module.")
        with st.expander("Technical details", expanded=False):
            st.code(traceback.format_exc(), language="python")
        st.exception(exc)


if __name__ == "__main__":
    main()
