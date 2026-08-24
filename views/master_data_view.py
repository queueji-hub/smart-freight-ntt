"""Master Data Center: canonical CRUD for ports, parties and charges."""
from __future__ import annotations

from typing import Any, Dict
import streamlit as st
import pandas as pd

from managers.auth_manager import can_write
from managers.master_data_crud_manager import list_parties, upsert_party, delete_party, list_ports, upsert_port, delete_port
from managers.charge_master_crud_manager import list_charges, upsert_charge, delete_charge
from ui.design_system import page_header, section

ROLE_OPTIONS = ["CUSTOMER", "CARRIER", "VENDOR", "AGENT", "CO_LOADER", "SHIPPER", "CONSIGNEE"]


def _party_form(user: Dict[str, Any], record: Dict[str, Any] | None = None) -> None:
    record = record or {}
    section("Business Party")
    existing_roles = [r for r in record.get("roles", []) if r in ROLE_OPTIONS]
    roles = st.multiselect("Roles", ROLE_OPTIONS, default=existing_roles or ["CUSTOMER"], key=f"party_roles_{record.get('id','new')}")
    c1, c2, c3 = st.columns(3)
    with c1:
        code = st.text_input("Code *", value=str(record.get("party_code") or ""), max_chars=5).upper()
        legal = st.text_input("Legal Name *", value=str(record.get("legal_name") or ""))
        display = st.text_input("Display Name", value=str(record.get("display_name") or ""))
    with c2:
        tax_id = st.text_input("Tax ID", value=str(record.get("tax_id") or ""))
        branch = st.text_input("Branch No.", value=str(record.get("branch_no") or ""))
        phone = st.text_input("Phone", value=str(record.get("phone") or ""))
    with c3:
        email = st.text_input("Email", value=str(record.get("email") or ""))
        country = st.text_input("Country Code", value=str(record.get("country_code") or ""), max_chars=2).upper()
        active = st.checkbox("Active", value=bool(record.get("is_active", True)), key=f"party_active_{record.get('id','new')}")

    f1, f2, f3, f4 = st.columns(4)
    with f1:
        credit_limit = st.number_input("Credit Limit", min_value=0.0, step=1000.0, value=float(record.get("credit_limit") or 0), key=f"party_credit_{record.get('id','new')}")
    with f2:
        credit_currency = st.text_input("Credit Currency", value=str(record.get("credit_currency") or "THB"), max_chars=3).upper()
    with f3:
        credit_days = st.number_input("Credit Days", min_value=0, step=1, value=int(record.get("credit_days") or 0), key=f"party_days_{record.get('id','new')}")
    with f4:
        payment_term = st.text_input("Payment Term Code", value=str(record.get("payment_term_code") or ""))

    bank1, bank2, bank3, bank4 = st.columns(4)
    bank_name = bank1.text_input("Bank", value=str(record.get("bank_name") or ""))
    account_name = bank2.text_input("Account Name", value=str(record.get("bank_account_name") or ""))
    account_no = bank3.text_input("Account No.", value=str(record.get("bank_account_no") or ""))
    swift = bank4.text_input("SWIFT", value=str(record.get("swift_code") or ""))
    address = st.text_area("Billing Address", value=str(record.get("billing_address") or ""))

    btn_cols = st.columns([3, 1] if record.get("id") else [1])
    save_label = "Update Party" if record.get("id") else "Save Party"
    with btn_cols[0]:
        save = st.button(save_label, type="primary", width="stretch", key=f"party_save_{record.get('id','new')}")
    if record.get("id") and len(btn_cols) > 1:
        with btn_cols[1]:
            if st.button("🗑️ Delete Party", type="secondary", width="stretch", key=f"party_del_{record.get('id')}"):
                delete_party(int(record["id"]), user)
                st.success("Party deleted successfully.")
                st.session_state.pop("master_data_edit_party", None)
                st.rerun()

    if save:
        if len(code) != 5 or not legal.strip():
            st.error("Code must be exactly 5 characters and Legal Name is required.")
            return
        upsert_party(
            {
                "id": record.get("id"),
                "party_code": code,
                "legal_name": legal,
                "display_name": display or legal,
                "tax_id": tax_id,
                "branch_no": branch,
                "country_code": country,
                "phone": phone,
                "email": email,
                "billing_address": address,
                "is_active": active,
            },
            roles,
            {
                "credit_limit": credit_limit,
                "credit_currency": credit_currency,
                "credit_days": credit_days,
                "payment_term_code": payment_term,
                "bank_name": bank_name,
                "bank_account_name": account_name,
                "bank_account_no": account_no,
                "swift_code": swift,
            },
            user,
        )
        st.success("Party updated." if record.get("id") else "Party saved.")
        st.session_state.pop("master_data_edit_party", None)
        st.rerun()


def _port_form(user: Dict[str, Any], record: Dict[str, Any] | None = None) -> None:
    record = record or {}
    section("Port / Place")
    c1, c2, c3 = st.columns(3)
    code = c1.text_input("Port Code *", value=str(record.get("port_code") or ""), max_chars=5).upper()
    unlocode = c2.text_input("UN/LOCODE", value=str(record.get("unlocode") or ""), max_chars=5).upper()
    name = c3.text_input("Port Name *", value=str(record.get("port_name") or ""))
    d1, d2, d3 = st.columns(3)
    city = d1.text_input("City", value=str(record.get("city") or ""))
    country_code = d2.text_input("Country Code", value=str(record.get("country_code") or ""), max_chars=2).upper()
    country_name = d3.text_input("Country Name", value=str(record.get("country_name") or ""))
    timezone = st.text_input("Timezone", value=str(record.get("timezone") or ""))
    active = st.checkbox("Active", value=bool(record.get("is_active", True)), key=f"port_active_{record.get('id','new')}")
    
    btn_cols = st.columns([3, 1] if record.get("id") else [1])
    save_label = "Update Port" if record.get("id") else "Save Port"
    with btn_cols[0]:
        save = st.button(save_label, type="primary", width="stretch", key=f"port_save_{record.get('id','new')}")
    if record.get("id") and len(btn_cols) > 1:
        with btn_cols[1]:
            if st.button("🗑️ Delete Port", type="secondary", width="stretch", key=f"port_del_{record.get('id')}"):
                delete_port(int(record["id"]), user)
                st.success("Port deleted successfully.")
                st.session_state.pop("master_data_edit_port", None)
                st.rerun()

    if save:
        if len(code) != 5 or not name.strip():
            st.error("Port Code must be exactly 5 characters and Port Name is required.")
            return
        upsert_port(
            {
                "id": record.get("id"),
                "port_code": code,
                "unlocode": unlocode or code,
                "port_name": name,
                "city": city,
                "country_code": country_code,
                "country_name": country_name,
                "timezone": timezone,
                "is_active": active,
            },
            user,
        )
        st.success("Port updated." if record.get("id") else "Port saved.")
        st.session_state.pop("master_data_edit_port", None)
        st.rerun()


def _charge_form(user: Dict[str, Any], record: Dict[str, Any] | None = None) -> None:
    record = record or {}
    section("Charge Master")
    c1, c2, c3 = st.columns(3)
    code = c1.text_input("Charge Code *", value=str(record.get("charge_code") or "")).strip().upper()
    description = c2.text_input("Description *", value=str(record.get("description") or ""))
    category = c3.text_input("Category", value=str(record.get("category") or ""))
    d1, d2, d3, d4 = st.columns(4)
    basis = d1.text_input("Default Basis", value=str(record.get("default_basis") or ""))
    unit = d2.text_input("Default Unit", value=str(record.get("default_unit") or ""))
    currency = d3.text_input("Default Currency", value=str(record.get("default_currency") or "USD"), max_chars=3).upper()
    active = d4.checkbox("Active", value=bool(record.get("is_active", True)), key=f"charge_active_{record.get('id','new')}")
    
    btn_cols = st.columns([3, 1] if record.get("id") else [1])
    save_label = "Update Charge" if record.get("id") else "Save Charge"
    with btn_cols[0]:
        save = st.button(save_label, type="primary", width="stretch", key=f"charge_save_{record.get('id','new')}")
    if record.get("id") and len(btn_cols) > 1:
        with btn_cols[1]:
            if st.button("🗑️ Delete Charge", type="secondary", width="stretch", key=f"charge_del_{record.get('id')}"):
                delete_charge(int(record["id"]), user)
                st.success("Charge deleted successfully.")
                st.session_state.pop("master_data_edit_charge", None)
                st.rerun()

    if save:
        if not code or not description.strip():
            st.error("Charge Code and Description are required.")
            return
        upsert_charge(
            {
                "id": record.get("id"),
                "charge_code": code,
                "description": description.strip(),
                "category": category.strip() or None,
                "default_basis": basis.strip() or None,
                "default_unit": unit.strip() or None,
                "default_currency": currency,
                "is_active": active,
            },
            user,
        )
        st.success("Charge updated." if record.get("id") else "Charge saved.")
        st.session_state.pop("master_data_edit_charge", None)
        st.rerun()


def render() -> None:
    page_header("data", status_text="Online")
    user = st.session_state.get("user", {})
    role = str(user.get("role", "")).lower()
    if not can_write(role, "settings"):
        st.warning("Master Data access is restricted to authorized users.")
        return

    mode = st.radio("Master Data", ["Ports", "Business Parties", "Charges"], horizontal=True, key="master_data_mode")
    if mode == "Ports":
        rows = list_ports(active_only=False)
        action = st.radio("Action", ["Browse", "New"], horizontal=True, key="port_action")
        if action == "New":
            _port_form(user)
        else:
            frame = pd.DataFrame([
                {"ID": r.get("id"), "Code": r.get("port_code"), "Port": r.get("port_name"), "City": r.get("city"), "Country": r.get("country_name"), "UN/LOCODE": r.get("unlocode"), "Active": r.get("is_active")}
                for r in rows
            ])
            st.dataframe(frame, hide_index=True, width="stretch")
            options = [r for r in rows if r.get("id")]
            if options:
                col_sel, col_btn = st.columns([3, 1])
                with col_sel:
                    selected = st.selectbox("Select Port to Edit/Delete", options, format_func=lambda r: f"{r.get('port_code')} — {r.get('port_name')}", key="port_edit_selector")
                with col_btn:
                    st.write("")
                    if st.button("Edit Port", key="port_edit_button", width="stretch"):
                        st.session_state["master_data_edit_port"] = int(selected["id"])
            edit_id = st.session_state.get("master_data_edit_port")
            if edit_id:
                record = next((r for r in rows if int(r.get("id")) == int(edit_id)), None)
                if record:
                    _port_form(user, record)
                    if st.button("Close Edit", key="port_cancel_edit"):
                        st.session_state.pop("master_data_edit_port", None)
                        st.rerun()
    elif mode == "Business Parties":
        role_type = st.selectbox("Party Role", ["ALL"] + ROLE_OPTIONS)
        rows = list_parties(None if role_type == "ALL" else role_type, active_only=False)
        action = st.radio("Action", ["Browse", "New"], horizontal=True, key="party_action")
        if action == "New":
            _party_form(user)
        else:
            frame = pd.DataFrame([
                {"ID": r.get("id"), "Code": r.get("party_code"), "Legal Name": r.get("legal_name"), "Display Name": r.get("display_name"), "Tax ID": r.get("tax_id"), "Phone": r.get("phone"), "Email": r.get("email"), "Active": r.get("is_active")}
                for r in rows
            ])
            st.dataframe(frame, hide_index=True, width="stretch")
            options = [r for r in rows if r.get("id")]
            if options:
                col_sel, col_btn = st.columns([3, 1])
                with col_sel:
                    selected = st.selectbox("Select Party to Edit/Delete", options, format_func=lambda r: f"{r.get('party_code')} — {r.get('legal_name')}", key="party_edit_selector")
                with col_btn:
                    st.write("")
                    if st.button("Edit Party", key="party_edit_button", width="stretch"):
                        st.session_state["master_data_edit_party"] = int(selected["id"])
            edit_id = st.session_state.get("master_data_edit_party")
            if edit_id:
                record = next((r for r in rows if int(r.get("id")) == int(edit_id)), None)
                if record:
                    _party_form(user, record)
                    if st.button("Close Edit", key="party_cancel_edit"):
                        st.session_state.pop("master_data_edit_party", None)
                        st.rerun()
    else:
        rows = list_charges(active_only=False, user=user)
        action = st.radio("Action", ["Browse", "New"], horizontal=True, key="charge_action")
        if action == "New":
            _charge_form(user)
        else:
            frame = pd.DataFrame([
                {"ID": r.get("id"), "Code": r.get("charge_code"), "Description": r.get("description"), "Category": r.get("category"), "Basis": r.get("default_basis"), "Unit": r.get("default_unit"), "Currency": r.get("default_currency"), "Active": r.get("is_active")}
                for r in rows
            ])
            st.dataframe(frame, hide_index=True, width="stretch")
            options = [r for r in rows if r.get("id")]
            if options:
                col_sel, col_btn = st.columns([3, 1])
                with col_sel:
                    selected = st.selectbox("Select Charge to Edit/Delete", options, format_func=lambda r: f"{r.get('charge_code')} — {r.get('description')}", key="charge_edit_selector")
                with col_btn:
                    st.write("")
                    if st.button("Edit Charge", key="charge_edit_button", width="stretch"):
                        st.session_state["master_data_edit_charge"] = int(selected["id"])
            edit_id = st.session_state.get("master_data_edit_charge")
            if edit_id:
                record = next((r for r in rows if int(r.get("id")) == int(edit_id)), None)
                if record:
                    _charge_form(user, record)
                    if st.button("Close Edit", key="charge_cancel_edit"):
                        st.session_state.pop("master_data_edit_charge", None)
                        st.rerun()

