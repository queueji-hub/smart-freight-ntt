"""Master Data Center: Business Parties, Salespersons, Ports & Locations, and Charge Codes."""
from __future__ import annotations

from typing import Any, Dict, List, Optional
import streamlit as st
import pandas as pd

from managers.auth_manager import can_write
from managers.master_data_crud_manager import list_parties, upsert_party, delete_party, list_ports, upsert_port, delete_port
from managers.salesperson_manager import list_salespersons, save_salesperson, delete_salesperson, get_salesperson
from managers.charge_master_manager import list_charges, upsert_charge, delete_charge
from ui.design_system import page_header, section

ROLE_OPTIONS = ["CUSTOMER", "CARRIER", "VENDOR", "AGENT", "CO_LOADER", "SHIPPER", "CONSIGNEE"]


def _party_form(user: Dict[str, Any], record: Dict[str, Any] | None = None) -> None:
    record = record or {}
    section("Business Party / Customer Profile")
    existing_roles = [r for r in record.get("roles", []) if r in ROLE_OPTIONS]
    roles = st.multiselect(
        "Roles (ประเภทคู่ค้า / ลูกค้า) *",
        ROLE_OPTIONS,
        default=existing_roles or ["CUSTOMER"],
        key=f"party_roles_{record.get('id','new')}",
        help="เลือกว่าเป็น CUSTOMER (ลูกค้า), CARRIER (สายเรือ/สายการบิน), VENDOR (ผู้ให้บริการ), AGENT หรืออื่นๆ"
    )
    
    c1, c2, c3 = st.columns(3)
    with c1:
        code = st.text_input("Party Code (รหัสคู่ค้า/ลูกค้า)", value=str(record.get("party_code") or ""), placeholder="Auto (ระบบ gen ให้อัตโนมัติ)", max_chars=10, key=f"party_code_{record.get('id','new')}").upper()
        legal = st.text_input("Legal / Company Name (ชื่อบริษัท/นิติบุคคล) *", value=str(record.get("legal_name") or record.get("company_name") or ""), key=f"party_legal_{record.get('id','new')}")
        display = st.text_input("Display Name (ชื่อทางการค้า/ชื่อย่อ)", value=str(record.get("display_name") or record.get("company_name") or ""), key=f"party_disp_{record.get('id','new')}")
    with c2:
        tax_id = st.text_input("Tax ID (เลขประจำตัวผู้เสียภาษี)", value=str(record.get("tax_id") or ""), key=f"party_tax_{record.get('id','new')}")
        branch = st.text_input("Branch No. (สาขา)", value=str(record.get("branch_no") or "00000"), key=f"party_branch_{record.get('id','new')}")
        phone = st.text_input("Phone (เบอร์โทร)", value=str(record.get("phone") or record.get("tel") or ""), key=f"party_phone_{record.get('id','new')}")
    with c3:
        email = st.text_input("Email (อีเมล)", value=str(record.get("email") or ""), key=f"party_email_{record.get('id','new')}")
        country = st.text_input("Country Code (รหัสประเทศ เช่น TH, US, CN)", value=str(record.get("country_code") or "TH"), max_chars=2, key=f"party_country_{record.get('id','new')}").upper()
        active = st.checkbox("Active (เปิดใช้งาน)", value=bool(record.get("is_active", True)), key=f"party_active_{record.get('id','new')}")

    section("Billing & Credit Terms (เงื่อนไขเครดิตและการเรียกเก็บเงิน)")
    f1, f2, f3, f4 = st.columns(4)
    with f1:
        credit_limit = st.number_input("Credit Limit (วงเงินเครดิต)", min_value=0.0, step=1000.0, value=float(record.get("credit_limit") or 0), key=f"party_credit_{record.get('id','new')}")
    with f2:
        credit_currency = st.text_input("Credit Currency (สกุลเงิน)", value=str(record.get("credit_currency") or "THB"), max_chars=3, key=f"party_ccurr_{record.get('id','new')}").upper()
    with f3:
        credit_days = st.number_input("Credit Days (จำนวนวันเครดิต)", min_value=0, step=1, value=int(record.get("credit_days") or 0), key=f"party_days_{record.get('id','new')}")
    with f4:
        payment_term = st.text_input("Payment Term (เงื่อนไขชำระเงิน)", value=str(record.get("payment_term_code") or "Net 30"), key=f"party_payterm_{record.get('id','new')}")

    bank1, bank2, bank3, bank4 = st.columns(4)
    bank_name = bank1.text_input("Bank (ธนาคาร)", value=str(record.get("bank_name") or ""), key=f"party_bank_{record.get('id','new')}")
    account_name = bank2.text_input("Account Name (ชื่อบัญชี)", value=str(record.get("bank_account_name") or ""), key=f"party_accname_{record.get('id','new')}")
    account_no = bank3.text_input("Account No. (เลขที่บัญชี)", value=str(record.get("bank_account_no") or ""), key=f"party_accno_{record.get('id','new')}")
    swift = bank4.text_input("SWIFT Code", value=str(record.get("swift_code") or ""), key=f"party_swift_{record.get('id','new')}")
    address = st.text_area("Billing / Tax Address (ที่อยู่ออกใบกำกับภาษี / ใบแจ้งหนี้)", value=str(record.get("billing_address") or record.get("address") or ""), key=f"party_addr_{record.get('id','new')}")

    btn_cols = st.columns([3, 1] if record.get("id") else [1])
    save_label = "Update Party / Customer" if record.get("id") else "Save Party / Customer"
    with btn_cols[0]:
        save = st.button(save_label, type="primary", width="stretch", key=f"party_save_{record.get('id','new')}")
    if record.get("id") and len(btn_cols) > 1:
        with btn_cols[1]:
            if st.button("🗑️ Delete Party", type="secondary", width="stretch", key=f"party_del_{record.get('id')}"):
                delete_party(int(record["id"]), user)
                st.success("Party deleted successfully.")
                st.session_state["party_action"] = "Browse"
                st.session_state.pop("master_data_edit_party", None)
                st.rerun()

    if save:
        if not legal.strip():
            st.error("Legal / Company Name is required (กรุณากรอกชื่อบริษัท/นิติบุคคล).")
            return
        if not roles:
            roles = ["CUSTOMER"]
        upsert_party(
            {
                "id": record.get("id"),
                "party_code": code,
                "legal_name": legal.strip(),
                "display_name": (display.strip() or legal.strip()),
                "tax_id": tax_id.strip(),
                "branch_no": branch.strip(),
                "country_code": country.strip(),
                "phone": phone.strip(),
                "email": email.strip(),
                "billing_address": address.strip(),
                "is_active": active,
            },
            roles,
            {
                "credit_limit": credit_limit,
                "credit_currency": credit_currency,
                "credit_days": credit_days,
                "payment_term_code": payment_term.strip(),
                "bank_name": bank_name.strip(),
                "bank_account_name": account_name.strip(),
                "bank_account_no": account_no.strip(),
                "swift_code": swift.strip(),
            },
            user,
        )
        st.session_state["party_action"] = "Browse"
        st.session_state.pop("master_data_edit_party", None)
        st.success("Party / Customer updated." if record.get("id") else "Party / Customer saved.")
        st.rerun()


def _salesperson_form(user: Dict[str, Any], record: Dict[str, Any] | None = None) -> None:
    record = record or {}
    section("Sales Person Profile")
    c1, c2, c3 = st.columns(3)
    with c1:
        code = st.text_input("Sales Code (รหัสพนักงานขาย)", value=str(record.get("sales_code") or ""), placeholder="Auto (ระบบ gen ให้อัตโนมัติ)", max_chars=10, key=f"sp_code_{record.get('id','new')}").upper()
        name = st.text_input("Salesperson Name (ชื่อ-นามสกุล) *", value=str(record.get("name") or ""), key=f"sp_name_{record.get('id','new')}")
    with c2:
        email = st.text_input("Email (อีเมล)", value=str(record.get("email") or ""), key=f"sp_email_{record.get('id','new')}")
        phone = st.text_input("Phone (เบอร์โทร)", value=str(record.get("phone") or ""), key=f"sp_phone_{record.get('id','new')}")
    with c3:
        comm = st.number_input("Commission Rate (%)", min_value=0.0, max_value=100.0, step=0.5, value=float(record.get("commission_rate") or 0.0), key=f"sp_comm_{record.get('id','new')}")
        active = st.checkbox("Active (เปิดใช้งาน)", value=bool(record.get("is_active", True)), key=f"sp_active_{record.get('id','new')}")

    remarks = st.text_area("Remarks / Notes (หมายเหตุ)", value=str(record.get("remarks") or ""), key=f"sp_remarks_{record.get('id','new')}")

    btn_cols = st.columns([3, 1] if record.get("id") else [1])
    save_label = "Update Sales Person" if record.get("id") else "Save Sales Person"
    with btn_cols[0]:
        save = st.button(save_label, type="primary", width="stretch", key=f"sp_save_{record.get('id','new')}")
    if record.get("id") and len(btn_cols) > 1:
        with btn_cols[1]:
            if st.button("🗑️ Delete Sales Person", type="secondary", width="stretch", key=f"sp_del_{record.get('id')}"):
                delete_salesperson(record["id"], user)
                st.success("Sales Person deleted successfully.")
                st.session_state["sp_action"] = "Browse"
                st.session_state.pop("master_data_edit_sp", None)
                st.rerun()

    if save:
        if not name.strip():
            st.error("Salesperson Name is required (กรุณากรอกชื่อพนักงานขาย).")
            return
        save_salesperson({
            "id": record.get("id"),
            "sales_code": code.strip(),
            "name": name.strip(),
            "email": email.strip(),
            "phone": phone.strip(),
            "commission_rate": comm,
            "remarks": remarks.strip(),
            "is_active": active,
        }, user)
        st.session_state["sp_action"] = "Browse"
        st.session_state.pop("master_data_edit_sp", None)
        st.success("Sales Person updated." if record.get("id") else "Sales Person saved.")
        st.rerun()


def _port_form(user: Dict[str, Any], record: Dict[str, Any] | None = None) -> None:
    record = record or {}
    section("Port / Location Profile")
    c1, c2, c3 = st.columns(3)
    with c1:
        code = st.text_input("Port Code (รหัสท่าเรือ/สนามบิน) *", value=str(record.get("port_code") or ""), max_chars=10, key=f"port_code_{record.get('id','new')}").upper()
        name = st.text_input("Port / Terminal Name (ชื่อท่าเรือ/สนามบิน) *", value=str(record.get("port_name") or ""), key=f"port_name_{record.get('id','new')}")
    with c2:
        unlocode = st.text_input("UN/LOCODE", value=str(record.get("unlocode") or ""), max_chars=10, key=f"port_unlocode_{record.get('id','new')}").upper()
        country_code = st.text_input("Country Code (รหัสประเทศ)", value=str(record.get("country_code") or "TH"), max_chars=2, key=f"port_country_{record.get('id','new')}").upper()
    with c3:
        port_type = st.selectbox("Type", ["PORT", "AIRPORT", "ICD", "BORDER", "OTHER"], index=["PORT", "AIRPORT", "ICD", "BORDER", "OTHER"].index(str(record.get("port_type") or "PORT")) if str(record.get("port_type") or "PORT") in ["PORT", "AIRPORT", "ICD", "BORDER", "OTHER"] else 0, key=f"port_type_{record.get('id','new')}")
        active = st.checkbox("Active (เปิดใช้งาน)", value=bool(record.get("is_active", True)), key=f"port_active_{record.get('id','new')}")

    city = st.text_input("City / Province (เมือง/จังหวัด)", value=str(record.get("city") or ""), key=f"port_city_{record.get('id','new')}")
    remarks = st.text_area("Remarks (หมายเหตุ)", value=str(record.get("remarks") or ""), key=f"port_remarks_{record.get('id','new')}")

    btn_cols = st.columns([3, 1] if record.get("id") else [1])
    save_label = "Update Port" if record.get("id") else "Save Port"
    with btn_cols[0]:
        save = st.button(save_label, type="primary", width="stretch", key=f"port_save_{record.get('id','new')}")
    if record.get("id") and len(btn_cols) > 1:
        with btn_cols[1]:
            if st.button("🗑️ Delete Port", type="secondary", width="stretch", key=f"port_del_{record.get('id')}"):
                delete_port(int(record["id"]), user)
                st.success("Port deleted successfully.")
                st.session_state["port_action"] = "Browse"
                st.session_state.pop("master_data_edit_port", None)
                st.rerun()

    if save:
        if not code.strip() or not name.strip():
            st.error("Port Code and Name are required (กรุณากรอกรหัสและชื่อท่าเรือ).")
            return
        upsert_port({
            "id": record.get("id"),
            "port_code": code.strip(),
            "port_name": name.strip(),
            "unlocode": unlocode.strip(),
            "country_code": country_code.strip(),
            "port_type": port_type,
            "city": city.strip(),
            "remarks": remarks.strip(),
            "is_active": active,
        }, user)
        st.session_state["port_action"] = "Browse"
        st.session_state.pop("master_data_edit_port", None)
        st.success("Port updated." if record.get("id") else "Port saved.")
        st.rerun()


def _charge_form(user: Dict[str, Any], record: Dict[str, Any] | None = None) -> None:
    record = record or {}
    section("Charge Code Profile")
    c1, c2, c3 = st.columns(3)
    with c1:
        code = st.text_input("Charge Code (รหัสค่าบริการ) *", value=str(record.get("charge_code") or ""), max_chars=10, key=f"chg_code_{record.get('id','new')}").upper()
        desc = st.text_input("Description (คำอธิบายค่าบริการ) *", value=str(record.get("description") or ""), key=f"chg_desc_{record.get('id','new')}")
    with c2:
        cat = st.selectbox("Category (หมวดหมู่)", ["FREIGHT", "ORIGIN", "DESTINATION", "DOCUMENT", "CUSTOMS", "STORAGE", "TRUCKING", "OTHER"], index=["FREIGHT", "ORIGIN", "DESTINATION", "DOCUMENT", "CUSTOMS", "STORAGE", "TRUCKING", "OTHER"].index(str(record.get("category") or "FREIGHT")) if str(record.get("category") or "FREIGHT") in ["FREIGHT", "ORIGIN", "DESTINATION", "DOCUMENT", "CUSTOMS", "STORAGE", "TRUCKING", "OTHER"] else 0, key=f"chg_cat_{record.get('id','new')}")
        basis = st.selectbox("Default Basis", ["PER_CONTAINER", "PER_BL", "PER_SHIPMENT", "PER_KG", "PER_CBM", "PER_TRIP", "LUMPSUM"], key=f"chg_basis_{record.get('id','new')}")
    with c3:
        curr = st.text_input("Default Currency", value=str(record.get("default_currency") or "USD"), max_chars=3, key=f"chg_curr_{record.get('id','new')}").upper()
        active = st.checkbox("Active (เปิดใช้งาน)", value=bool(record.get("is_active", True)), key=f"chg_active_{record.get('id','new')}")

    btn_cols = st.columns([3, 1] if record.get("id") else [1])
    save_label = "Update Charge Code" if record.get("id") else "Save Charge Code"
    with btn_cols[0]:
        save = st.button(save_label, type="primary", width="stretch", key=f"chg_save_{record.get('id','new')}")
    if record.get("id") and len(btn_cols) > 1:
        with btn_cols[1]:
            if st.button("🗑️ Delete Charge Code", type="secondary", width="stretch", key=f"chg_del_{record.get('id')}"):
                delete_charge(int(record["id"]), user)
                st.success("Charge code deleted successfully.")
                st.session_state["chg_action"] = "Browse"
                st.session_state.pop("master_data_edit_chg", None)
                st.rerun()

    if save:
        if not code.strip() or not desc.strip():
            st.error("Charge Code and Description are required (กรุณากรอกรหัสและคำอธิบายค่าบริการ).")
            return
        upsert_charge({
            "id": record.get("id"),
            "charge_code": code.strip(),
            "description": desc.strip(),
            "category": cat,
            "default_basis": basis,
            "default_unit": basis.replace("PER_", ""),
            "default_currency": curr.strip(),
            "is_active": active,
        }, user)
        st.session_state["chg_action"] = "Browse"
        st.session_state.pop("master_data_edit_chg", None)
        st.success("Charge Code updated." if record.get("id") else "Charge Code saved.")
        st.rerun()


def render() -> None:
    page_header("data", status_text="Online")
    user = st.session_state.get("user", {})
    role = str(user.get("role", "")).lower()
    if not can_write(role, "settings"):
        st.warning("Master Data access is restricted to authorized users.")
        return

    mode = st.radio(
        "Master Data Section",
        [
            "🤝 Business Parties (คู่ค้า / ลูกค้า / สายเรือ / ซัพพลายเออร์)",
            "👤 Sales Persons (พนักงานขาย)",
            "⚓ Ports & Locations (ท่าเรือ / สนามบิน / สถานี)",
            "🏷️ Charge Codes (รหัสค่าใช้จ่าย / บริการ)",
        ],
        horizontal=True,
        key="master_data_mode"
    )

    if "Business Parties" in mode:
        section("Business Parties Ledger (ฐานข้อมูลคู่ค้าและลูกค้า)")
        
        filter_col, action_col = st.columns([2, 2])
        with filter_col:
            role_type = st.selectbox(
                "Filter by Role (กรองตามประเภท)",
                ["ALL (ทั้งหมด)", "CUSTOMER (ลูกค้า)", "CARRIER (สายเรือ / สายการบิน)", "VENDOR (ผู้ให้บริการ)", "AGENT (ตัวแทน)", "SHIPPER (ผู้ส่งสินค้า)", "CONSIGNEE (ผู้รับสินค้า)"],
                key="party_role_filter"
            )
        with action_col:
            st.write("")
            action = st.radio("Action", ["Browse", "➕ New Party / Customer"], horizontal=True, key="party_action")

        selected_role = None
        if "CUSTOMER" in role_type:
            selected_role = "CUSTOMER"
        elif "CARRIER" in role_type:
            selected_role = "CARRIER"
        elif "VENDOR" in role_type:
            selected_role = "VENDOR"
        elif "AGENT" in role_type:
            selected_role = "AGENT"
        elif "SHIPPER" in role_type:
            selected_role = "SHIPPER"
        elif "CONSIGNEE" in role_type:
            selected_role = "CONSIGNEE"

        if action == "➕ New Party / Customer":
            default_rec = {"roles": [selected_role]} if selected_role else {"roles": ["CUSTOMER"]}
            _party_form(user, default_rec)
            return

        rows = list_parties(selected_role, active_only=False)
        
        search_query = st.text_input("🔍 Search Parties & Customers", placeholder="Search by Code, Legal Name, Display Name, Tax ID, Phone, Email...", key="md_party_search")
        if search_query.strip():
            sq = search_query.strip().lower()
            rows = [
                r for r in rows
                if sq in f"{r.get('party_code','')} {r.get('legal_name','')} {r.get('display_name','')} {r.get('tax_id','')} {r.get('phone','')} {r.get('email','')}".lower()
            ]

        frame = pd.DataFrame([
            {
                "ID": r.get("id"),
                "Code": r.get("party_code"),
                "Legal Name": r.get("legal_name"),
                "Display Name": r.get("display_name"),
                "Roles": ", ".join(r.get("roles", [])) if isinstance(r.get("roles"), list) else _s(r.get("roles")),
                "Tax ID": r.get("tax_id") or "—",
                "Phone": r.get("phone") or "—",
                "Email": r.get("email") or "—",
                "Credit Limit": f"{float(r.get('credit_limit') or 0):,.2f} {r.get('credit_currency','THB')}",
                "Credit Days": r.get("credit_days") or 0,
                "Active": "✅ Active" if r.get("is_active") else "Inactive",
            }
            for r in rows
        ])
        st.dataframe(frame, hide_index=True, width="stretch")

        options = [r for r in rows if r.get("id")]
        if options:
            col_sel, col_btn = st.columns([3, 1])
            with col_sel:
                selected = st.selectbox(
                    "Select Party / Customer to Edit",
                    options,
                    format_func=lambda r: f"{r.get('party_code')} — {r.get('display_name') or r.get('legal_name')} ({', '.join(r.get('roles', [])) if isinstance(r.get('roles'), list) else r.get('roles', '')})",
                    key="party_edit_selector"
                )
            with col_btn:
                st.write("")
                if st.button("✏️ Edit Party / Customer", key="party_edit_button", width="stretch"):
                    st.session_state["master_data_edit_party"] = int(selected["id"])

        edit_id = st.session_state.get("master_data_edit_party")
        if edit_id:
            record = next((r for r in rows if int(r.get("id")) == int(edit_id)), None)
            if record:
                _party_form(user, record)
                if st.button("✖️ Close Edit", key="party_cancel_edit"):
                    st.session_state.pop("master_data_edit_party", None)
                    st.rerun()

    elif "Sales Persons" in mode:
        section("Sales Persons Ledger (ข้อมูลพนักงานขาย)")
        action = st.radio("Action", ["Browse", "➕ New Sales Person"], horizontal=True, key="sp_action")
        if action == "➕ New Sales Person":
            _salesperson_form(user)
            return

        rows = list_salespersons(active_only=False, user=user)
        search_query = st.text_input("🔍 Search Sales Persons", placeholder="Search by Code, Name, Email, Phone...", key="md_sp_search")
        if search_query.strip():
            sq = search_query.strip().lower()
            rows = [
                r for r in rows
                if sq in f"{r.get('sales_code','')} {r.get('name','')} {r.get('email','')} {r.get('phone','')}".lower()
            ]

        frame = pd.DataFrame([
            {
                "ID": r.get("id"),
                "Sales Code": r.get("sales_code"),
                "Name": r.get("name"),
                "Email": r.get("email") or "—",
                "Phone": r.get("phone") or "—",
                "Commission %": f"{float(r.get('commission_rate') or 0):.2f}%",
                "Remarks": r.get("remarks") or "—",
                "Active": "✅ Active" if r.get("is_active") else "Inactive",
            }
            for r in rows
        ])
        st.dataframe(frame, hide_index=True, width="stretch")
        
        options = [r for r in rows if r.get("id")]
        if options:
            col_sel, col_btn = st.columns([3, 1])
            with col_sel:
                selected = st.selectbox(
                    "Select Sales Person to Edit",
                    options,
                    format_func=lambda r: f"{r.get('sales_code')} — {r.get('name')}",
                    key="sp_edit_selector"
                )
            with col_btn:
                st.write("")
                if st.button("✏️ Edit Sales Person", key="sp_edit_button", width="stretch"):
                    st.session_state["master_data_edit_sp"] = selected["id"]

        edit_id = st.session_state.get("master_data_edit_sp")
        if edit_id is not None:
            record = next((r for r in rows if str(r.get("id")) == str(edit_id)), None)
            if record:
                _salesperson_form(user, record)
                if st.button("✖️ Close Edit", key="sp_cancel_edit"):
                    st.session_state.pop("master_data_edit_sp", None)
                    st.rerun()

    elif "Ports & Locations" in mode:
        section("Ports & Locations Ledger (ท่าเรือ / สนามบิน / สถานี)")
        action = st.radio("Action", ["Browse", "➕ New Port / Location"], horizontal=True, key="port_action")
        if action == "➕ New Port / Location":
            _port_form(user)
            return

        rows = list_ports(active_only=False)
        search_query = st.text_input("🔍 Search Ports & Locations", placeholder="Search by Code, Name, UN/LOCODE, Country...", key="md_port_search")
        if search_query.strip():
            sq = search_query.strip().lower()
            rows = [
                r for r in rows
                if sq in f"{r.get('port_code','')} {r.get('port_name','')} {r.get('unlocode','')} {r.get('country_code','')} {r.get('city','')}".lower()
            ]

        frame = pd.DataFrame([
            {
                "ID": r.get("id"),
                "Port Code": r.get("port_code"),
                "Name": r.get("port_name"),
                "UN/LOCODE": r.get("unlocode") or "—",
                "Type": r.get("port_type") or "PORT",
                "Country": r.get("country_code") or "TH",
                "City": r.get("city") or "—",
                "Active": "✅ Active" if r.get("is_active") else "Inactive",
            }
            for r in rows
        ])
        st.dataframe(frame, hide_index=True, width="stretch")

        options = [r for r in rows if r.get("id")]
        if options:
            col_sel, col_btn = st.columns([3, 1])
            with col_sel:
                selected = st.selectbox(
                    "Select Port to Edit",
                    options,
                    format_func=lambda r: f"{r.get('port_code')} — {r.get('port_name')} ({r.get('country_code')})",
                    key="port_edit_selector"
                )
            with col_btn:
                st.write("")
                if st.button("✏️ Edit Port", key="port_edit_button", width="stretch"):
                    st.session_state["master_data_edit_port"] = int(selected["id"])

        edit_id = st.session_state.get("master_data_edit_port")
        if edit_id:
            record = next((r for r in rows if int(r.get("id")) == int(edit_id)), None)
            if record:
                _port_form(user, record)
                if st.button("✖️ Close Edit", key="port_cancel_edit"):
                    st.session_state.pop("master_data_edit_port", None)
                    st.rerun()

    elif "Charge Codes" in mode:
        section("Charge Codes Ledger (รหัสค่าใช้จ่าย / ค่าบริการ)")
        action = st.radio("Action", ["Browse", "➕ New Charge Code"], horizontal=True, key="chg_action")
        if action == "➕ New Charge Code":
            _charge_form(user)
            return

        rows = list_charges(active_only=False)
        search_query = st.text_input("🔍 Search Charge Codes", placeholder="Search by Code, Description, Category...", key="md_chg_search")
        if search_query.strip():
            sq = search_query.strip().lower()
            rows = [
                r for r in rows
                if sq in f"{r.get('charge_code','')} {r.get('description','')} {r.get('category','')}".lower()
            ]

        frame = pd.DataFrame([
            {
                "ID": r.get("id"),
                "Charge Code": r.get("charge_code"),
                "Description": r.get("description"),
                "Category": r.get("category") or "FREIGHT",
                "Default Basis": r.get("default_basis") or "PER_CONTAINER",
                "Currency": r.get("default_currency") or "USD",
                "Active": "✅ Active" if r.get("is_active") else "Inactive",
            }
            for r in rows
        ])
        st.dataframe(frame, hide_index=True, width="stretch")

        options = [r for r in rows if r.get("id")]
        if options:
            col_sel, col_btn = st.columns([3, 1])
            with col_sel:
                selected = st.selectbox(
                    "Select Charge to Edit",
                    options,
                    format_func=lambda r: f"{r.get('charge_code')} — {r.get('description')} ({r.get('category')})",
                    key="chg_edit_selector"
                )
            with col_btn:
                st.write("")
                if st.button("✏️ Edit Charge", key="chg_edit_button", width="stretch"):
                    st.session_state["master_data_edit_chg"] = int(selected["id"])

        edit_id = st.session_state.get("master_data_edit_chg")
        if edit_id:
            record = next((r for r in rows if int(r.get("id")) == int(edit_id)), None)
            if record:
                _charge_form(user, record)
                if st.button("✖️ Close Edit", key="chg_cancel_edit"):
                    st.session_state.pop("master_data_edit_chg", None)
                    st.rerun()


def _s(val: Any) -> str:
    return str(val or "").strip()
