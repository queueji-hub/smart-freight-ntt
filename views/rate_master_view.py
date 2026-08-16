"""Rate Master UI: create/edit reusable carrier-lane pricing."""
from __future__ import annotations

from datetime import date
import pandas as pd
import streamlit as st

from managers.auth_manager import can_write
from managers.charge_master_manager import list_charges
from managers.master_data_crud_manager import list_parties, list_ports
from managers.rate_master_manager import list_rate_cards, upsert_rate_card
from ui.design_system import page_header, section

MODE_OPTIONS = ["SEA", "AIR", "TRUCK", "MULTIMODAL"]


def _render_form(user, record=None):
    record = record or {}
    parties = list_parties("CARRIER", active_only=True)
    ports = list_ports(active_only=True)
    charges = list_charges(active_only=True)
    carrier_map = {int(p["id"]): f"{p.get('party_code')} — {p.get('display_name') or p.get('legal_name')}" for p in parties if p.get("id")}
    port_map = {int(p["id"]): f"{p.get('port_code')} — {p.get('port_name')}, {p.get('country_name') or ''}" for p in ports if p.get("id")}
    charge_map = {int(c["id"]): f"{c.get('charge_code')} — {c.get('description')}" for c in charges if c.get("id")}

    def _date(v, fallback):
        try:
            return date.fromisoformat(str(v)[:10])
        except (TypeError, ValueError):
            return fallback

    current_carrier = int(record.get("carrier_id")) if record.get("carrier_id") else None
    current_origin = int(record.get("origin_port_id")) if record.get("origin_port_id") else None
    current_dest = int(record.get("destination_port_id")) if record.get("destination_port_id") else None
    carrier_options = list(carrier_map)
    origin_options = list(port_map)
    dest_options = list(port_map)

    with st.form(f"rate_master_{record.get('id','new')}"):
        section("Rate Card")
        a, b, c, d = st.columns(4)
        rate_no = a.text_input("Rate No. *", value=str(record.get("rate_no") or ""))
        mode = b.selectbox("Mode *", MODE_OPTIONS, index=MODE_OPTIONS.index(str(record.get("mode") or "SEA").upper()) if str(record.get("mode") or "SEA").upper() in MODE_OPTIONS else 0)
        currency = c.text_input("Currency", value=str(record.get("currency") or "USD"), max_chars=3).upper()
        status = d.selectbox("Status", ["ACTIVE", "INACTIVE"], index=0 if str(record.get("status") or "ACTIVE").upper() == "ACTIVE" else 1)
        e, f, g, h = st.columns(4)
        carrier_id = e.selectbox("Carrier", carrier_options, index=carrier_options.index(current_carrier) if current_carrier in carrier_options else 0, format_func=lambda x: carrier_map[x]) if carrier_options else None
        origin_id = f.selectbox("Origin", origin_options, index=origin_options.index(current_origin) if current_origin in origin_options else 0, format_func=lambda x: port_map[x]) if origin_options else None
        destination_id = g.selectbox("Destination", dest_options, index=dest_options.index(current_dest) if current_dest in dest_options else 0, format_func=lambda x: port_map[x]) if dest_options else None
        equipment = h.text_input("Equipment", value=str(record.get("equipment_type") or ""))
        i, j, k = st.columns(3)
        service = i.text_input("Service", value=str(record.get("service_type") or ""))
        valid_from = j.date_input("Valid From", _date(record.get("valid_from"), date.today()))
        valid_to = k.date_input("Valid To", _date(record.get("valid_to"), date.today()))

        section("Rate Lines")
        existing_lines = record.get("lines") or []
        rows = [{
            "charge_id": int(x.get("charge_id")) if x.get("charge_id") else (list(charge_map)[0] if charge_map else None),
            "basis": x.get("basis") or "",
            "minimum": float(x.get("minimum") or 0),
            "rate": float(x.get("rate") or 0),
            "currency": x.get("currency") or currency,
        } for x in existing_lines]
        if not rows and charge_map:
            rows = [{"charge_id": list(charge_map)[0], "basis": "", "minimum": 0.0, "rate": 0.0, "currency": currency}]
        edited = st.data_editor(
            pd.DataFrame(rows),
            num_rows="dynamic",
            hide_index=True,
            width="stretch",
            column_config={
                "charge_id": st.column_config.SelectboxColumn("Charge", options=list(charge_map.keys()), format_func=lambda x: charge_map.get(x, str(x)), required=True),
                "basis": st.column_config.TextColumn("Basis"),
                "minimum": st.column_config.NumberColumn("Minimum", min_value=0.0, step=0.01),
                "rate": st.column_config.NumberColumn("Rate", min_value=0.0, step=0.01),
                "currency": st.column_config.TextColumn("Currency", max_chars=3),
            },
            key=f"rate_master_lines_{record.get('id','new')}",
        )
        save = st.form_submit_button("Update Rate Card" if record.get("id") else "Save Rate Card", type="primary", width="stretch")

    if not save:
        return False
    if valid_to < valid_from:
        st.error("Valid To cannot be earlier than Valid From.")
        return False
    if not rate_no.strip() or not mode:
        st.error("Rate No. and Mode are required.")
        return False
    lines = edited.to_dict("records") if not edited.empty else []
    upsert_rate_card({
        "id": record.get("id"), "rate_no": rate_no, "mode": mode, "currency": currency, "status": status,
        "carrier_id": carrier_id, "origin_port_id": origin_id, "destination_port_id": destination_id,
        "equipment_type": equipment, "service_type": service,
        "valid_from": valid_from.isoformat(), "valid_to": valid_to.isoformat(),
    }, lines, user)
    st.success("Rate card updated." if record.get("id") else "Rate card saved.")
    return True


def render():
    page_header("rates", status_text="Online")
    user = st.session_state.get("user", {})
    role = str(user.get("role", "")).lower()
    if not can_write(role, "settings"):
        st.warning("Rate Master access is restricted to authorized users.")
        return

    section("Rate Card Ledger")
    rows = list_rate_cards(active_only=False, user=user)
    st.dataframe(pd.DataFrame([
        {"Rate No.": r.get("rate_no"), "Mode": r.get("mode"), "Carrier": r.get("carrier_id"), "Currency": r.get("currency"), "Valid From": r.get("valid_from"), "Valid To": r.get("valid_to"), "Status": r.get("status"), "Lines": len(r.get("lines") or [])}
        for r in rows
    ]), hide_index=True, width="stretch")

    options = [r for r in rows if r.get("id")]
    if options:
        selected = st.selectbox("Select Rate Card", options, format_func=lambda r: f"{r.get('rate_no')} — {r.get('mode')} — {r.get('currency')}", key="rate_master_edit_selector")
        actions = st.columns(2)
        with actions[0]:
            edit = st.button("Edit Selected", width="stretch")
        with actions[1]:
            new_rate = st.button("New Rate Card", type="primary", width="stretch")
        if edit:
            st.session_state["rate_master_edit_id"] = int(selected["id"])
            st.session_state.pop("rate_master_new", None)
        if new_rate:
            st.session_state["rate_master_new"] = True
            st.session_state.pop("rate_master_edit_id", None)
    else:
        new_rate = st.button("New Rate Card", type="primary", width="stretch")
        if new_rate:
            st.session_state["rate_master_new"] = True

    edit_id = st.session_state.get("rate_master_edit_id")
    if edit_id:
        record = next((r for r in rows if int(r.get("id")) == int(edit_id)), None)
        if record:
            if _render_form(user, record):
                st.session_state.pop("rate_master_edit_id", None)
                st.rerun()
            if st.button("Cancel Edit", key="rate_master_cancel_edit"):
                st.session_state.pop("rate_master_edit_id", None)
                st.rerun()

    if st.session_state.get("rate_master_new"):
        if _render_form(user):
            st.session_state.pop("rate_master_new", None)
            st.rerun()
        if st.button("Close", key="rate_master_close"):
            st.session_state.pop("rate_master_new", None)
            st.rerun()
