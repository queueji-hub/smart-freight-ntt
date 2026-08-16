"""Streamlined Quotation workspace for Phase 30."""
from __future__ import annotations

import os
from datetime import date, timedelta
from typing import Any, Dict

import pandas as pd
import streamlit as st

from config import DEFAULT_TERMS, JOB_TYPES
from managers.auth_manager import can_write
from managers.customer_manager import list_customers
from managers.master_data_manager import list_sales_users
from managers.charge_master_manager import list_charges
from managers.master_data_crud_manager import list_parties, list_ports
from managers.quotation_manager import duplicate_quotation, get_quotation_by_no, list_quotations
from managers.quotation_ssot_service import create_quotation_ssot
from managers.rate_lookup_service import find_applicable_rates
from ui.design_system import page_header, section

CURRENCY_OPTIONS = ["USD", "THB", "CNY", "EUR", "JPY"]
MODE_OPTIONS = ["SEA", "AIR", "TRUCK", "MULTIMODAL"]


def _s(value: Any, default: str = "") -> str:
    if value is None:
        return default
    value = str(value).strip()
    return default if value.lower() in {"", "none", "nan", "nat"} else value


def _date(value: Any, fallback: date) -> date:
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value)[:10])
    except (ValueError, TypeError):
        return fallback


def _prepare_pdf(record: Dict[str, Any], items: list[dict]) -> None:
    qno = _s(record.get("quotation_no"), "quotation")
    try:
        from pdf.quotation_pdf import generate_quotation_pdf
        path = generate_quotation_pdf(record, items)
        if path and os.path.exists(path):
            with open(path, "rb") as fh:
                st.session_state[f"quotation_pdf_{qno}"] = fh.read()
                st.session_state[f"quotation_pdf_name_{qno}"] = os.path.basename(path)
    except Exception as exc:
        st.error(f"Unable to create PDF: {exc}")


def _render_pdf(record: Dict[str, Any], items: list[dict]) -> None:
    qno = _s(record.get("quotation_no"), "quotation")
    if st.button("PDF", key=f"qv2_prepare_pdf_{qno}", type="primary", width="stretch"):
        _prepare_pdf(record, items)
    payload = st.session_state.get(f"quotation_pdf_{qno}")
    if payload:
        st.download_button("Download", data=payload, file_name=st.session_state.get(f"quotation_pdf_name_{qno}", f"{qno}.pdf"), mime="application/pdf", key=f"qv2_download_pdf_{qno}", width="stretch")


def _master_data():
    customers = list_customers() or []
    sales = list_sales_users() or []
    carriers = list_parties("CARRIER", active_only=True) or []
    ports = list_ports(active_only=True) or []
    charges = list_charges(active_only=True) or []
    customer_map = {int(r["id"]): r.get("company_name", str(r["id"])) for r in customers if r.get("id")}
    sales_map = {int(r["id"]): (r.get("full_name") or r.get("username") or str(r["id"])) for r in sales if r.get("id")}
    carrier_map = {int(r["id"]): f"{r.get('party_code')} — {r.get('display_name') or r.get('legal_name')}" for r in carriers if r.get("id")}
    port_map = {int(r["id"]): f"{r.get('port_code')} — {r.get('port_name')}, {r.get('country_name') or ''}" for r in ports if r.get("id")}
    charge_map = {str(r.get("charge_code")).upper(): r for r in charges if r.get("charge_code")}
    return customer_map, sales_map, carrier_map, port_map, charge_map


def _item_editor(charge_map: dict[str, dict[str, Any]], existing: list[dict] | None = None) -> list[dict]:
    rows = []
    for raw in existing or []:
        item = dict(raw or {})
        code = _s(item.get("charge_code")).upper()
        if not code:
            desc = _s(item.get("description")).lower()
            match = next((c for c in charge_map.values() if _s(c.get("description")).lower() == desc), None)
            code = _s(match.get("charge_code")).upper() if match else ""
        rows.append({"charge_code": code, "quantity": float(item.get("quantity") or 1), "unit_rate": float(item.get("unit_rate") or 0), "price": float(item.get("price") or 0), "remark": _s(item.get("remark"))})
    if not rows:
        default_code = next(iter(charge_map), "")
        rows = [{"charge_code": default_code, "quantity": 1.0, "unit_rate": 0.0, "price": 0.0, "remark": ""}]

    codes = list(charge_map.keys())
    df = pd.DataFrame(rows)
    edited = st.data_editor(
        df,
        num_rows="dynamic",
        hide_index=True,
        width="stretch",
        column_config={
            "charge_code": st.column_config.SelectboxColumn("Charge *", options=codes, required=True, width="large"),
            "quantity": st.column_config.NumberColumn("Qty", min_value=0.0, step=1.0),
            "unit_rate": st.column_config.NumberColumn("Rate", min_value=0.0, step=0.01),
            "price": st.column_config.NumberColumn("Amount", disabled=True),
            "remark": st.column_config.TextColumn("Remarks"),
        },
        key="qv2_items",
    )
    edited["charge_code"] = edited["charge_code"].fillna("").astype(str).str.upper().str.strip()
    edited["price"] = pd.to_numeric(edited["quantity"], errors="coerce").fillna(1) * pd.to_numeric(edited["unit_rate"], errors="coerce").fillna(0)
    output = []
    for row in edited.to_dict("records"):
        code = _s(row.get("charge_code")).upper()
        master = charge_map.get(code)
        if not master:
            output.append(row)
            continue
        output.append({
            "charge_code": code,
            "description": master.get("description"),
            "basis": master.get("default_basis"),
            "quantity": float(row.get("quantity") or 0),
            "unit": master.get("default_unit"),
            "currency": master.get("default_currency") or "USD",
            "unit_rate": float(row.get("unit_rate") or 0),
            "price": float(row.get("price") or 0),
            "remark": _s(row.get("remark")),
        })
    return output


def _create_form(user: Dict[str, Any]):
    customer_map, sales_map, carrier_map, port_map, charge_map = _master_data()
    today = date.today()
    with st.form("quotation_v2_create"):
        section("Quotation Details")
        c1, c2 = st.columns(2)
        with c1:
            customer_id = st.selectbox("Customer *", list(customer_map), format_func=lambda x: customer_map[x]) if customer_map else None
            job_type = st.selectbox("Job Type *", list(JOB_TYPES.keys()), format_func=lambda x: JOB_TYPES.get(x, x))
            issue_date = st.date_input("Issue Date", today)
        with c2:
            sales_id = st.selectbox("Sales", list(sales_map), format_func=lambda x: sales_map[x]) if sales_map else None
            valid_until = st.date_input("Valid Until", today + timedelta(days=30))
            payment_term = st.text_input("Payment Terms", value="Net 30")

        section("Shipment")
        r1, r2, r3 = st.columns(3)
        with r1:
            carrier_id = st.selectbox("Carrier", list(carrier_map), format_func=lambda x: carrier_map[x]) if carrier_map else None
        with r2:
            pol_id = st.selectbox("POL", list(port_map), format_func=lambda x: port_map[x]) if port_map else None
        with r3:
            pod_id = st.selectbox("POD", list(port_map), format_func=lambda x: port_map[x]) if port_map else None
        r4, r5, r6 = st.columns(3)
        with r4:
            mode = st.selectbox("Transport Mode", MODE_OPTIONS)
        with r5:
            service_type = st.selectbox("Service", ["", "FCL", "LCL", "AIR", "FTL", "LTL"])
        with r6:
            equipment_type = st.text_input("Equipment")
        commodity = st.text_input("Commodity")
        incoterm = st.selectbox("Incoterm", ["", "EXW", "FCA", "FOB", "CFR", "CIF", "DAP", "DDP", "DDU"])
        subject = st.text_input("Subject")

        section("Rate Lookup")
        applicable = find_applicable_rates(carrier_id=carrier_id, origin_port_id=pol_id, destination_port_id=pod_id, mode=mode, equipment_type=equipment_type.strip() or None) if carrier_id and pol_id and pod_id else []
        st.caption(f"Rate Master matches: {len(applicable)}")
        rate_options = [r for r in applicable if r.get("line_id")]
        if rate_options:
            rate_index = st.selectbox("Rate Card", list(range(len(rate_options))), format_func=lambda i: f"{rate_options[i].get('rate_no')} — {rate_options[i].get('currency')} {rate_options[i].get('rate')}")
            selected_rate = rate_options[rate_index]
        else:
            selected_rate = None

        section("Pricing")
        items_df = _item_editor(charge_map)
        if selected_rate and items_df:
            for row in items_df:
                if _s(row.get("charge_code")).upper() == _s(selected_rate.get("charge_code")).upper():
                    row["unit_rate"] = float(selected_rate.get("rate") or 0)
                    row["currency"] = selected_rate.get("line_currency") or selected_rate.get("currency") or "USD"
                    row["price"] = float(row.get("quantity") or 1) * row["unit_rate"]

        section("Terms")
        terms = st.text_area("Terms & Conditions", value=DEFAULT_TERMS, height=120)
        submitted = st.form_submit_button("Save Draft", type="primary", width="stretch")

    if submitted:
        errors = []
        if customer_id is None:
            errors.append("Customer is required.")
        if valid_until < issue_date:
            errors.append("Valid Until cannot be earlier than Issue Date.")
        if pol_id is None or pod_id is None:
            errors.append("POL and POD are required.")
        if not charge_map:
            errors.append("Charge Master has no active charges.")
        clean_items = []
        for idx, row in enumerate(items_df, 1):
            if not _s(row.get("charge_code")):
                errors.append(f"Line {idx}: Charge is required.")
                continue
            if float(row.get("unit_rate") or 0) < 0:
                errors.append(f"Line {idx}: Rate cannot be negative.")
            clean_items.append(row)
        if errors:
            for error in errors:
                st.error(error)
            return

        payload = {
            "job_type": job_type,
            "customer_id": customer_id,
            "customer_name": customer_map[customer_id],
            "sales_id": sales_id,
            "salesperson": sales_map.get(sales_id, "") if sales_id else "",
            "quotation_date": issue_date.isoformat(),
            "validity_date": valid_until.isoformat(),
            "payment_term": payment_term.strip(),
            "carrier_id": carrier_id,
            "pol_id": pol_id,
            "pod_id": pod_id,
            "pol": port_map[pol_id] if pol_id else None,
            "pod": port_map[pod_id] if pod_id else None,
            "mode": mode,
            "service_type": service_type,
            "equipment_type": equipment_type.strip() or None,
            "commodity": commodity.strip() or None,
            "incoterm": incoterm,
            "subject": subject.strip() or None,
            "terms_conditions": terms.strip(),
            "status": "Draft",
        }
        try:
            qno = create_quotation_ssot(payload, clean_items)
            st.success(f"Quotation {qno} saved as Draft.")
            st.rerun()
        except Exception as exc:
            st.error(f"Unable to save quotation: {exc}")


def render():
    page_header("quotation", status_text="Online")
    user = st.session_state.get("user", {})
    can_edit = can_write(str(user.get("role", "")).lower(), "quotation")

    records = list_quotations() or []
    search, new_col = st.columns([4, 1])
    with search:
        query = st.text_input("Search quotations", placeholder="Quotation, customer or subject", key="qv2_search")
    with new_col:
        st.write("")
        new_quote = st.button("New Quotation", type="primary", width="stretch") if can_edit else False

    if query.strip():
        q = query.strip().lower()
        records = [r for r in records if q in str(r).lower()]

    if new_quote:
        st.session_state["qv2_create"] = True
    if st.session_state.get("qv2_create") and can_edit:
        _create_form(user)
        if st.button("Close", key="qv2_close"):
            st.session_state.pop("qv2_create", None)
            st.rerun()
        return

    section("Quotation Ledger")
    table = pd.DataFrame([
        {"Quotation No.": _s(r.get("quotation_no")), "Customer": _s(r.get("customer_name"), "—"), "Issue Date": _s(r.get("quotation_date"), "—"), "Valid Until": _s(r.get("validity_date"), "—"), "Status": _s(r.get("status"), "—")}
        for r in records
    ])
    st.dataframe(table, hide_index=True, width="stretch")
    if not records:
        st.info("No quotations found.")
        return

    qnos = [r["quotation_no"] for r in records if r.get("quotation_no")]
    selected_no = st.selectbox("Select Quotation", qnos, key="qv2_selected")
    selected = get_quotation_by_no(selected_no)
    if not selected:
        st.warning("Quotation not found.")
        return

    section("Quotation Actions")
    a1, a2, a3 = st.columns(3)
    with a1:
        _render_pdf(selected, selected.get("items", []))
    with a2:
        if can_edit and st.button("Duplicate", key=f"qv2_dup_{selected_no}", width="stretch"):
            try:
                duplicate_quotation(selected_no)
                st.success("Quotation duplicated.")
                st.rerun()
            except Exception as exc:
                st.error(str(exc))
    with a3:
        st.metric("Status", _s(selected.get("status"), "Draft"))
