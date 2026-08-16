"""AR / outstanding control workspace built on the existing Finance SSOT."""
from __future__ import annotations
from datetime import date
import pandas as pd
import streamlit as st
from managers.invoice_manager import list_invoices, record_payment
from managers.auth_manager import can_write
from ui.design_system import page_header, section

PAYMENT_METHODS = ["Bank Transfer", "Cash", "Cheque", "Credit Card"]


def _num(value):
    try:
        return float(value or 0)
    except Exception:
        return 0.0


def _money(value):
    return f"{_num(value):,.2f}"


def _is_open(row):
    return str(row.get("status", "")).upper() not in {"CANCELLED", "PAID"} and _num(row.get("outstanding")) > 0


def _is_overdue(row):
    due = str(row.get("due_date") or "")
    return _is_open(row) and bool(due) and due < date.today().isoformat()


def render():
    page_header("billing", status_text="Online")
    user = st.session_state.get("user", {})
    writable = can_write(str(user.get("role", "")).lower(), "billing")
    rows = list_invoices() or []
    open_rows = [r for r in rows if _is_open(r)]
    overdue_rows = [r for r in open_rows if _is_overdue(r)]

    section("AR / Outstanding Control")
    billed = sum(_num(r.get("grand_total")) for r in rows if str(r.get("status", "")).upper() != "CANCELLED")
    outstanding = sum(_num(r.get("outstanding")) for r in open_rows)
    paid = max(billed - outstanding, 0)
    overdue = sum(_num(r.get("outstanding")) for r in overdue_rows)
    a, b, c, d = st.columns(4)
    a.metric("AR Billed", _money(billed))
    b.metric("AR Paid", _money(paid))
    c.metric("AR Outstanding", _money(outstanding))
    d.metric("Overdue", _money(overdue))

    tabs = st.tabs(["AR Aging", "SOA View", "Payment Register"])
    with tabs[0]:
        section("Accounts Receivable Aging")
        q = st.text_input("Customer / Document / Job / B/L", key="ar_search")
        view = open_rows
        if q.strip():
            view = [r for r in view if q.strip().lower() in str(r).lower()]
        st.dataframe(pd.DataFrame([{
            "Document": r.get("doc_no"),
            "Customer": r.get("customer_name"),
            "Issue": r.get("issue_date"),
            "Due": r.get("due_date"),
            "Total": _num(r.get("grand_total")),
            "Outstanding": _num(r.get("outstanding")),
            "Status": "OVERDUE" if _is_overdue(r) else r.get("status"),
        } for r in view]), hide_index=True, width="stretch")

    with tabs[1]:
        section("Statement of Account (SOA)")
        customers = sorted({str(r.get("customer_name")) for r in rows if r.get("customer_name")})
        customer = st.selectbox("Customer", customers, key="soa_customer") if customers else None
        if customer:
            view = [r for r in rows if r.get("customer_name") == customer and str(r.get("status", "")).upper() != "CANCELLED"]
            balance = sum(_num(r.get("outstanding")) for r in view)
            st.metric("Customer Outstanding", _money(balance))
            st.dataframe(pd.DataFrame([{
                "Document": r.get("doc_no"),
                "Date": r.get("issue_date"),
                "Due": r.get("due_date"),
                "Debit": _num(r.get("grand_total")),
                "Credit": max(_num(r.get("grand_total")) - _num(r.get("outstanding")), 0),
                "Balance": _num(r.get("outstanding")),
            } for r in view]), hide_index=True, width="stretch")
        else:
            st.info("No customer transactions available for SOA.")

    with tabs[2]:
        section("Payment Register")
        if not writable:
            st.info("Payment entry requires billing write permission.")
        elif not open_rows:
            st.success("No outstanding AR documents.")
        else:
            options = [r.get("doc_no") for r in open_rows]
            selected = st.selectbox("Outstanding Document", options, key="ar_payment_doc")
            rec = next(r for r in open_rows if r.get("doc_no") == selected)
            st.caption(f"Customer: {rec.get('customer_name', '—')} · Outstanding: {_money(rec.get('outstanding'))} {rec.get('currency', 'THB')}")
            amount = st.number_input("Payment Amount", min_value=0.01, max_value=max(_num(rec.get("outstanding")), 0.01), value=max(_num(rec.get("outstanding")), 0.01), key="ar_payment_amount")
            method = st.selectbox("Payment Method", PAYMENT_METHODS, key="ar_payment_method")
            reference = st.text_input("Transaction Reference", key="ar_payment_ref")
            payment_date = st.date_input("Payment Date", date.today(), key="ar_payment_date")
            if st.button("Record Payment", type="primary", width="stretch", key="ar_record_payment"):
                try:
                    record_payment({"doc_no": selected, "amount": amount, "method": method, "reference": reference.strip(), "date": payment_date.isoformat()})
                    st.success(f"Payment recorded for {selected}.")
                    st.rerun()
                except Exception as exc:
                    st.error(f"Payment failed: {exc}")
