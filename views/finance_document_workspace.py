"""Structured Finance Document Workspace.

Keeps invoice_manager and finance_v2_view as SSOT while providing a document-first
UI for Billing Note, Receipt / Tax Invoice, Credit Note, Debit Note and Statement of Account (SOA).
"""
from __future__ import annotations

import pandas as pd
import streamlit as st

from managers.auth_manager import can_write
from managers.invoice_manager import get_outstanding_summary, list_invoices
from ui.design_system import page_header, section
from views import finance_v2_view as finance

DOC_TYPES = finance.DOC_TYPES


def _filtered_rows(rows):
    doc_filter = st.selectbox(
        "Document Type",
        ["ALL"] + list(DOC_TYPES),
        format_func=lambda x: "All Documents" if x == "ALL" else DOC_TYPES[x],
        key="finance_workspace_doc_type",
    )
    customer = st.text_input(
        "Customer / Reference",
        placeholder="Search customer, document no., Job or B/L",
        key="finance_workspace_search",
    ).strip().lower()
    if doc_filter != "ALL":
        rows = [r for r in rows if r.get("doc_type") == doc_filter]
    if customer:
        rows = [r for r in rows if customer in str(r).lower()]
    return rows


def _summary(rows):
    billed = sum(float(r.get("total_amount") or r.get("grand_total") or 0) for r in rows if str(r.get("status", "")).upper() != "CANCELLED")
    outstanding = sum(float(r.get("outstanding") or 0) for r in rows if str(r.get("status", "")).upper() != "CANCELLED")
    paid = sum(float(r.get("paid_amount") or 0) for r in rows) if any(r.get("paid_amount") for r in rows) else max(billed - outstanding, 0.0)
    a, b, c = st.columns(3)
    a.metric("Total Billed", f"{billed:,.2f}")
    b.metric("Total Paid", f"{paid:,.2f}")
    c.metric("Outstanding", f"{outstanding:,.2f}")


def render():
    page_header("billing", status_text="Online")
    user = st.session_state.get("user", {})
    can_edit = can_write(str(user.get("role", "")).lower(), "billing")
    rows = list_invoices() or []
    _summary(rows)

    tabs = st.tabs(["Document Register", "Payments"] + (["Create Document"] if can_edit else []))

    with tabs[0]:
        section("Finance Document Register")
        rows = _filtered_rows(rows)
        display = [{
            "Document No.": r.get("doc_no"),
            "Type": DOC_TYPES.get(r.get("doc_type"), r.get("doc_type")),
            "Customer": r.get("customer_name"),
            "Issue Date": r.get("issue_date"),
            "Due Date": r.get("due_date"),
            "Reference": r.get("ref_doc_no") or r.get("job_no"),
            "Total": r.get("grand_total", r.get("total_amount")),
            "Outstanding": r.get("outstanding"),
            "Status": r.get("status"),
        } for r in rows]
        st.dataframe(pd.DataFrame(display), hide_index=True, width="stretch")

        choices = [r.get("doc_no") for r in rows if r.get("doc_no")]
        if choices:
            selected = st.selectbox("Selected Document", choices, key="finance_workspace_selected")
            rec = next(r for r in rows if r.get("doc_no") == selected)
            status = finance._status(selected, rec.get("status"))
            st.caption(f"{DOC_TYPES.get(rec.get('doc_type'), rec.get('doc_type'))} · {rec.get('customer_name', '—')} · {status}")
            a, b, c, d, e = st.columns(5)
            with a:
                finance._pdf(selected)
            with b:
                from views.receipt_view import render_receipt_action
                render_receipt_action(selected)
            with c:
                if can_edit and status == "Draft" and st.button("Edit", key=f"workspace_edit_{selected}", width="stretch"):
                    st.session_state["finance_edit"] = selected
                    st.rerun()
            with d:
                if can_edit and status == "Draft" and st.button("Submit", key=f"workspace_submit_{selected}", width="stretch"):
                    finance.submit_for_approval("invoice", selected, user)
                    st.rerun()
            with e:
                if can_edit and st.button("Duplicate", key=f"workspace_dup_{selected}", width="stretch"):
                    st.success(f"Created {finance.duplicate_invoice(selected, user)} as Draft.")
                    st.rerun()
            if can_edit and st.session_state.get("finance_edit") == selected:
                finance._edit(selected)
        else:
            st.info("No finance documents match the current filters.")

    with tabs[1]:
        finance._payments()

    if can_edit:
        with tabs[2]:
            finance._new(user)
