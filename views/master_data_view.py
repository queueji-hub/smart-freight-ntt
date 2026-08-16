"""Master Data Center: ports and reusable business parties with CRUD."""
from __future__ import annotations
import streamlit as st
import pandas as pd
from managers.auth_manager import can_write
from managers.master_data_crud_manager import list_parties, upsert_party, list_ports, upsert_port
from ui.design_system import page_header, section

ROLE_OPTIONS = ["CUSTOMER", "CARRIER", "VENDOR", "AGENT", "CO_LOADER", "SHIPPER", "CONSIGNEE"]


def _party_form(user):
    section("Business Party")
    roles = st.multiselect("Roles", ROLE_OPTIONS, default=["CUSTOMER"])
    c1, c2, c3 = st.columns(3)
    with c1:
        code = st.text_input("Code *", max_chars=5).upper()
        legal = st.text_input("Legal Name *")
        display = st.text_input("Display Name")
    with c2:
        tax_id = st.text_input("Tax ID")
        branch = st.text_input("Branch No.")
        phone = st.text_input("Phone")
    with c3:
        email = st.text_input("Email")
        country = st.text_input("Country Code", max_chars=2).upper()
        active = st.checkbox("Active", value=True)
    f1, f2, f3, f4 = st.columns(4)
    with f1:
        credit_limit = st.number_input("Credit Limit", min_value=0.0, step=1000.0)
    with f2:
        credit_currency = st.text_input("Credit Currency", value="THB", max_chars=3).upper()
    with f3:
        credit_days = st.number_input("Credit Days", min_value=0, step=1)
    with f4:
        payment_term = st.text_input("Payment Term Code")
    bank1, bank2, bank3, bank4 = st.columns(4)
    bank = [st.empty() for _ in range(4)]
    bank_name = bank1.text_input("Bank")
    account_name = bank2.text_input("Account Name")
    account_no = bank3.text_input("Account No.")
    swift = bank4.text_input("SWIFT")
    address = st.text_area("Billing Address")
    save = st.button("Save Party", type="primary", width="stretch")
    if save:
        if len(code) != 5 or not legal.strip():
            st.error("Code must be exactly 5 characters and Legal Name is required.")
            return
        upsert_party(
            {"party_code": code, "legal_name": legal, "display_name": display or legal, "tax_id": tax_id,
             "branch_no": branch, "country_code": country, "phone": phone, "email": email,
             "billing_address": address, "is_active": active},
            roles,
            {"credit_limit": credit_limit, "credit_currency": credit_currency, "credit_days": credit_days,
             "payment_term_code": payment_term, "bank_name": bank_name, "bank_account_name": account_name,
             "bank_account_no": account_no, "swift_code": swift},
            user,
        )
        st.success("Party saved.")
        st.rerun()


def _port_form(user):
    section("Port / Place")
    c1, c2, c3 = st.columns(3)
    code = c1.text_input("Port Code *", max_chars=5).upper()
    unlocode = c2.text_input("UN/LOCODE", max_chars=5).upper()
    name = c3.text_input("Port Name *")
    d1, d2, d3 = st.columns(3)
    city = d1.text_input("City")
    country_code = d2.text_input("Country Code", max_chars=2).upper()
    country_name = d3.text_input("Country Name")
    timezone = st.text_input("Timezone")
    active = st.checkbox("Active", value=True)
    save = st.button("Save Port", type="primary", width="stretch")
    if save:
        if len(code) != 5 or not name.strip():
            st.error("Port Code must be exactly 5 characters and Port Name is required.")
            return
        upsert_port({"port_code": code, "unlocode": unlocode or code, "port_name": name, "city": city,
                     "country_code": country_code, "country_name": country_name, "timezone": timezone, "is_active": active}, user)
        st.success("Port saved.")
        st.rerun()


def render():
    page_header("data", status_text="Online")
    user = st.session_state.get("user", {})
    role = str(user.get("role", "")).lower()
    if not can_write(role, "settings"):
        st.warning("Master Data access is restricted to authorized users.")
        return

    mode = st.radio("Master Data", ["Ports", "Business Parties"], horizontal=True, key="master_data_mode")
    if mode == "Ports":
        action = st.radio("Action", ["Browse", "New"], horizontal=True, key="port_action")
        if action == "New":
            _port_form(user)
        else:
            rows = list_ports()
            st.dataframe(pd.DataFrame([{k: r.get(k) for k in ["port_code","port_name","city","country_name","unlocode","is_active"]} for r in rows]), hide_index=True, use_container_width=True)
    else:
        role_type = st.selectbox("Party Role", ["ALL"] + ROLE_OPTIONS)
        action = st.radio("Action", ["Browse", "New"], horizontal=True, key="party_action")
        if action == "New":
            _party_form(user)
        else:
            rows = list_parties(None if role_type == "ALL" else role_type)
            st.dataframe(pd.DataFrame([{k: r.get(k) for k in ["party_code","legal_name","display_name","tax_id","phone","email","is_active"]} for r in rows]), hide_index=True, use_container_width=True)
