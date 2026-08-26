"""Customer Master: code-based SSOT with tax, billing and credit controls."""
from __future__ import annotations
from typing import Any, Dict
import pandas as pd
import streamlit as st
from managers.auth_manager import can_write
from managers.customer_master_manager import list_customers, save_customer, get_credit_snapshot
from ui.design_system import page_header, section


def _form(user: Dict[str, Any], record: Dict[str, Any] | None = None) -> None:
    record = record or {}
    section("Customer Profile")
    a, b, c, d = st.columns(4)
    code = a.text_input("Customer Code", value=str(record.get("customer_code") or ""), placeholder="Auto (ระบบ gen ให้อัตโนมัติ)", max_chars=10).upper()
    company = b.text_input("Company Name *", value=str(record.get("company_name") or ""))
    display = c.text_input("Display Name", value=str(record.get("display_name") or ""))
    tax_id = d.text_input("Tax ID", value=str(record.get("tax_id") or ""))
    a, b, c, d = st.columns(4)
    contact = a.text_input("Contact Person", value=str(record.get("contact_person") or ""))
    tel = b.text_input("Tel", value=str(record.get("tel") or ""))
    email = c.text_input("Email", value=str(record.get("email") or ""))
    branch = d.text_input("Branch No.", value=str(record.get("branch_no") or ""))

    section("Billing & Credit")
    a, b, c, d = st.columns(4)
    credit_limit = a.number_input("Credit Limit", min_value=0.0, value=float(record.get("credit_limit") or 0), step=1000.0)
    credit_currency = b.text_input("Currency", value=str(record.get("credit_currency") or "THB"), max_chars=3).upper()
    credit_days = c.number_input("Credit Days", min_value=0, value=int(record.get("credit_days") or 0), step=1)
    payment_term = d.text_input("Payment Term", value=str(record.get("payment_term_code") or ""))
    billing_name = st.text_input("Tax Invoice / Billing Name", value=str(record.get("billing_name") or company))
    billing_address = st.text_area("Billing Address", value=str(record.get("billing_address") or record.get("address") or ""))
    a, b = st.columns(2)
    status = a.selectbox("Credit Status", ["NORMAL", "OVERDUE", "OVER LIMIT", "CREDIT HOLD"], index=["NORMAL","OVERDUE","OVER LIMIT","CREDIT HOLD"].index(str(record.get("credit_status") or "NORMAL")) if str(record.get("credit_status") or "NORMAL") in {"NORMAL","OVERDUE","OVER LIMIT","CREDIT HOLD"} else 0)
    credit_hold = b.checkbox("Credit Hold", value=bool(record.get("credit_hold")))
    active = st.checkbox("Active", value=bool(record.get("is_active", True)))

    save = st.button("Update Customer" if record.get("id") else "Save Customer", type="primary", width="stretch", key=f"customer_save_{record.get('id','new')}")
    if save:
        if not company.strip():
            st.error("Company Name is required.")
            return
        save_customer({
            "id": record.get("id"), "customer_code": code, "company_name": company, "display_name": display,
            "billing_name": billing_name, "contact_person": contact, "tel": tel, "email": email,
            "address": record.get("address"), "billing_address": billing_address, "branch_no": branch,
            "tax_id": tax_id, "credit_limit": credit_limit, "credit_currency": credit_currency,
            "credit_days": credit_days, "payment_term_code": payment_term, "credit_status": status,
            "credit_hold": credit_hold, "is_active": active,
        }, user)
        st.session_state["customer_master_action"] = "Browse"
        st.session_state.pop("customer_edit_id", None)
        st.success("Customer updated." if record.get("id") else "Customer saved.")
        st.rerun()



def render() -> None:
    page_header("crm", status_text="Online")
    user = st.session_state.get("user", {})
    role = str(user.get("role", "")).lower()
    if not can_write(role, "crm"):
        st.warning("Customer Master access is restricted.")
        return

    action = st.radio("Customers", ["Browse", "New"], horizontal=True, key="customer_master_action")
    rows = list_customers(active_only=False, user=user)
    if action == "New":
        _form(user)
        return

    frame = pd.DataFrame([
        {"ID": r.get("id"), "Code": r.get("customer_code"), "Company": r.get("display_name") or r.get("company_name"), "Tax ID": r.get("tax_id"), "Credit Limit": r.get("credit_limit"), "Credit Days": r.get("credit_days"), "Hold": r.get("credit_hold"), "Active": r.get("is_active")}
        for r in rows
    ])
    st.dataframe(frame, hide_index=True, width="stretch")

    options = [r for r in rows if r.get("id")]
    if options:
        selected = st.selectbox("Edit Customer", options, format_func=lambda r: f"{r.get('customer_code')} — {r.get('display_name') or r.get('company_name')}", key="customer_edit_selector")
        x, y = st.columns(2)
        with x:
            if st.button("Edit Selected", key="customer_edit_button", width="stretch"):
                st.session_state["customer_edit_id"] = int(selected["id"])
        with y:
            if st.button("Check Credit", key="customer_credit_button", width="stretch"):
                try:
                    snap = get_credit_snapshot(int(selected["id"]), user)
                    st.session_state["customer_credit_snapshot"] = snap
                except Exception as exc:
                    st.error(str(exc))

    snapshot = st.session_state.get("customer_credit_snapshot")
    if snapshot:
        section("Credit Control")
        a, b, c, d = st.columns(4)
        a.metric("Credit Limit", f"{float(snapshot['credit_limit'] or 0):,.2f} {snapshot.get('credit_currency','THB')}")
        b.metric("Outstanding", f"{snapshot['outstanding']:,.2f}")
        c.metric("Available", "Unlimited" if snapshot["available_credit"] is None else f"{snapshot['available_credit']:,.2f}")
        d.metric("Overdue", f"{snapshot['overdue']:,.2f}")
        if snapshot["control_status"] != "NORMAL":
            st.warning(snapshot["control_status"])

    edit_id = st.session_state.get("customer_edit_id")
    if edit_id:
        record = next((r for r in rows if int(r.get("id")) == int(edit_id)), None)
        if record:
            _form(user, record)
            if st.button("Cancel Edit", key="customer_cancel_edit"):
                st.session_state.pop("customer_edit_id", None)
                st.rerun()
