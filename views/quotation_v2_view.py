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
from managers.quotation_manager import (
    duplicate_quotation,
    get_quotation_by_no,
    list_quotations,
)
from managers.quotation_ssot_service import create_quotation_ssot
from ui.design_system import page_header, section

CURRENCY_OPTIONS = ["USD", "THB", "CNY", "EUR", "JPY"]


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
        st.download_button(
            "Download",
            data=payload,
            file_name=st.session_state.get(f"quotation_pdf_name_{qno}", f"{qno}.pdf"),
            mime="application/pdf",
            key=f"qv2_download_pdf_{qno}",
            width="stretch",
        )


def _master_data():
    customers = list_customers() or []
    sales = list_sales_users() or []
    customer_map = {int(r["id"]): r.get("company_name", str(r["id"])) for r in customers if r.get("id")}
    sales_map = {int(r["id"]): (r.get("full_name") or r.get("username") or str(r["id"])) for r in sales if r.get("id")}
    return customer_map, sales_map


def _item_editor(existing: list[dict] | None = None) -> list[dict]:
    rows = existing or [{"description": "", "basis": "", "quantity": 1.0, "unit": "SHPMT", "currency": "USD", "unit_rate": 0.0, "price": 0.0, "remark": ""}]
    df = pd.DataFrame(rows)
    if "price" not in df.columns:
        df["price"] = 0.0
    edited = st.data_editor(
        df,
        num_rows="dynamic",
        hide_index=True,
        use_container_width=True,
        column_config={
            "description": st.column_config.TextColumn("Charge *", required=True, width="large"),
            "basis": st.column_config.TextColumn("Basis", width="small"),
            "quantity": st.column_config.NumberColumn("Qty", min_value=0.0, step=1.0),
            "unit": st.column_config.TextColumn("Unit"),
            "currency": st.column_config.SelectboxColumn("Currency", options=CURRENCY_OPTIONS),
            "unit_rate": st.column_config.NumberColumn("Rate", min_value=0.0, step=0.01),
            "price": st.column_config.NumberColumn("Amount", disabled=True),
            "remark": st.column_config.TextColumn("Remarks"),
        },
        key="qv2_items",
    )
    edited["price"] = pd.to_numeric(edited["quantity"], errors="coerce").fillna(1) * pd.to_numeric(edited["unit_rate"], errors="coerce").fillna(0)
    return edited.to_dict("records")


def _create_form(user: Dict[str, Any]):
    customer_map, sales_map = _master_data()
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
            pol = st.text_input("POL")
        with r2:
            pod = st.text_input("POD")
        with r3:
            service_type = st.selectbox("Service", ["", "FCL", "LCL", "AIR", "FTL", "LTL"])
        commodity = st.text_input("Commodity")
        incoterm = st.selectbox("Incoterm", ["", "EXW", "FCA", "FOB", "CFR", "CIF", "DAP", "DDP", "DDU"])
        subject = st.text_input("Subject")

        section("Pricing")
        st.caption("Select standardized charges. Charge Master will be the canonical pricing source.")
        items_df = _item_editor()

        section("Terms")
        terms = st.text_area("Terms & Conditions", value=DEFAULT_TERMS, height=120)
        submitted = st.form_submit_button("Save Draft", type="primary", width="stretch")

    if submitted:
        errors = []
        if customer_id is None:
            errors.append("Customer is required.")
        if valid_until < issue_date:
            errors.append("Valid Until cannot be earlier than Issue Date.")
        clean_items = []
        for idx, row in enumerate(items_df, 1):
            if not _s(row.get("description")):
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
            "pol": pol.strip() or None,
            "pod": pod.strip() or None,
            "service_type": service_type,
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
        {
            "Quotation No.": _s(r.get("quotation_no")),
            "Customer": _s(r.get("customer_name"), "—"),
            "Issue Date": _s(r.get("quotation_date"), "—"),
            "Valid Until": _s(r.get("validity_date"), "—"),
            "Status": _s(r.get("status"), "—"),
        }
        for r in records
    ])
    st.dataframe(table, hide_index=True, use_container_width=True)
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
