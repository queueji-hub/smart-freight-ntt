"""AR/AP operational workspace built on the existing Finance SSOT."""
from __future__ import annotations

from datetime import date
import pandas as pd
import streamlit as st

from managers.invoice_manager import list_invoices, record_payment
from managers.auth_manager import can_write
from ui.design_system import page_header, section


def _safe_num(value):
    try:
        return float(value or 0)
    except Exception:
        return 0.0


def render() -> None:
    page_header("billing", status_text="Online")
    user = st.session_state.get("user", {})
    can_edit = can_write(str(user.get("role", "")).lower(), "billing")
    rows = list_invoices() or []

    ar = [r for r in rows if str(r.get("doc_type", "")).upper() in {"INV", "BN", "CN", "DN"}]
    outstanding = [r for r in ar if _safe_num(r.get("outstanding")) > 0]
    overdue = [r for r in outstanding if r.get("due_date") and str(r.get("due_date")) < date.today().isoformat()]

    section("AR / Outstanding Control")
    a, b, c, d = st.columns(4)
    a.metric("Open Documents", len(outstanding))
    b.metric("Outstanding", f"{sum(_safe_num(r.get('outstanding')) for r in outstanding):,.2f}")
    c.metric("Overdue Documents", len(overdue))
    d.metric("Overdue", f"{sum(_safe_num(r.get('outstanding')) for r in overdue):,.2f}")

    tab_ar, tab_overdue, tab_payment = st.tabs(["AR Ledger", "Overdue", "Record Payment"])
    with tab_ar:
        q = st.text_input("Search Customer / Document / Job / B/L", key="arap_search")
        view = outstanding
        if q.strip():
            view = [r for r in view if q.strip().lower() in str(r).lower()]
        st.dataframe(pd.DataFrame([{
            "Document": r.get("doc_no"),
            "Customer": r.get("customer_name"),
            "Type": r.get("doc_type"),
            "Issue": r.get("issue_date"),
            "Due": r.get("due_date"),
            "Total": _safe_num(r.get("grand_total")),
            "Outstanding": _safe_num(r.get("outstanding")),
            "Status": r.get("status"),
        } for r in view]), hide_index=True, width="stretch")

    with tab_overdue:
        st.dataframe(pd.DataFrame([{
            "Document": r.get("doc_no"), "Customer": r.get("customer_name"),
            "Due Date": r.get("due_date"), "Outstanding": _safe_num(r.get("outstanding")),
            "Status": r.get("status"),
        } for r in overdue]), hide_index=True, width="stretch")

    with tab_payment:
        if not can_edit:
            st.info("You do not have permission to record payments.")
            return
        if not outstanding:
            st.info("No outstanding documents available.")
            return
        options = [r.get("doc_no") for r in outstanding]
        selected = st.selectbox("Document", options, key="arap_payment_doc")
        rec = next(r for r in outstanding if r.get("doc_no") == selected)
        amount = st.number_input("Payment Amount", min_value=0.01, value=_safe_num(rec.get("outstanding")), key="arap_payment_amount")
        method = st.selectbox("Payment Method", ["Bank Transfer", "Cash", "Cheque", "Credit Card"], key="arap_payment_method")
        reference = st.text_input("Transaction Reference", key="arap_payment_reference")
        payment_date = st.date_input("Payment Date", date.today(), key="arap_payment_date")
        if st.button("Record Payment", type="primary", width="stretch", key="arap_record_payment"):
            try:
                record_payment({"doc_no": selected, "amount": amount, "method": method, "reference": reference.strip(), "date": payment_date.isoformat()})
                st.success(f"Payment recorded for {selected}.")
                st.rerun()
            except Exception as exc:
                st.error(f"Payment failed: {exc}")
