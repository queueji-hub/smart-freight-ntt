"""Rate Master UI: create/edit reusable carrier-lane pricing."""
from __future__ import annotations

from datetime import date
import pandas as pd
import streamlit as st

from managers.auth_manager import can_write
from managers.charge_master_manager import list_charges
from managers.master_data_crud_manager import list_parties, list_ports
from managers.rate_master_manager import list_rate_cards, upsert_rate_card
from managers.tenant_context import get_current_tenant_id
from ui.design_system import page_header, section


MODE_OPTIONS = ["SEA", "AIR", "TRUCK", "MULTIMODAL"]


def _render_form(user):
    parties = list_parties(None, active_only=True)
    carriers = [p for p in parties if p.get("id") and "CARRIER" in str(p.get("role_types") or p.get("role_type") or "CARRIER")]
    ports = list_ports(active_only=True)
    charges = list_charges(active_only=True)
    carrier_map = {int(p["id"]): f"{p.get('party_code')} — {p.get('display_name') or p.get('legal_name')}" for p in carriers}
    port_map = {int(p["id"]): f"{p.get('port_code')} — {p.get('port_name')}, {p.get('country_name') or ''}" for p in ports}
    charge_map = {int(c["id"]): f"{c.get('charge_code')} — {c.get('description')}" for c in charges}

    with st.form("rate_master_new"):
        section("Rate Card")
        a, b, c, d = st.columns(4)
        rate_no = a.text_input("Rate No. *")
        mode = b.selectbox("Mode *", MODE_OPTIONS)
        currency = c.text_input("Currency", value="USD", max_chars=3).upper()
        status = d.selectbox("Status", ["ACTIVE", "INACTIVE"])
        e, f, g, h = st.columns(4)
        carrier_id = e.selectbox("Carrier", list(carrier_map), format_func=lambda x: carrier_map[x]) if carrier_map else None
        origin_id = f.selectbox("Origin", list(port_map), format_func=lambda x: port_map[x]) if port_map else None
        destination_id = g.selectbox("Destination", list(port_map), format_func=lambda x: port_map[x]) if port_map else None
        equipment = h.text_input("Equipment")
        i, j, k = st.columns(3)
        service = i.text_input("Service")
        valid_from = j.date_input("Valid From", date.today())
        valid_to = k.date_input("Valid To", date.today())

        section("Rate Lines")
        rows = [{"charge_id": list(charge_map)[0] if charge_map else None, "basis": "", "minimum": 0.0, "rate": 0.0, "currency": currency}] if charge_map else []
        df = pd.DataFrame(rows)
        if not df.empty:
            df["charge_id"] = df["charge_id"].astype("Int64")
        edited = st.data_editor(
            df,
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
            key="rate_master_lines",
        )
        save = st.form_submit_button("Save Rate Card", type="primary", width="stretch")

    if not save:
        return
    if valid_to < valid_from:
        st.error("Valid To cannot be earlier than Valid From.")
        return
    if not rate_no.strip() or not mode:
        st.error("Rate No. and Mode are required.")
        return
    lines = edited.to_dict("records") if not edited.empty else []
    upsert_rate_card({
        "rate_no": rate_no,
        "mode": mode,
        "currency": currency,
        "status": status,
        "carrier_id": carrier_id,
        "origin_port_id": origin_id,
        "destination_port_id": destination_id,
        "equipment_type": equipment,
        "service_type": service,
        "valid_from": valid_from.isoformat(),
        "valid_to": valid_to.isoformat(),
    }, lines, user)
    st.success("Rate card saved.")
    st.rerun()


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
        {"Rate No.": r.get("rate_no"), "Mode": r.get("mode"), "Currency": r.get("currency"), "Valid From": r.get("valid_from"), "Valid To": r.get("valid_to"), "Status": r.get("status"), "Lines": len(r.get("lines") or [])}
        for r in rows
    ]), hide_index=True, width="stretch")

    if st.button("New Rate Card", type="primary", width="stretch"):
        st.session_state["rate_master_new"] = True
    if st.session_state.get("rate_master_new"):
        _render_form(user)
        if st.button("Close", key="rate_master_close"):
            st.session_state.pop("rate_master_new", None)
            st.rerun()
