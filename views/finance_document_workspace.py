"""Professional finance document workspace.

Document-first UI aligned to the supplied NATTAYAARAT Billing Note and
Receipt/Tax Invoice references. Business calculations remain in finance_v2_view
and invoice_manager; this module owns presentation, selection and preview only.
"""
from __future__ import annotations

from typing import Any, Dict

import pandas as pd
import streamlit as st

from managers.auth_manager import can_write
from managers.customer_manager import list_customers
from managers.invoice_manager import list_invoices
from ui.design_system import page_header, section
from views import finance_v2_view as finance

DOC_TYPES = finance.DOC_TYPES


def _safe(value: Any, default: str = "—") -> str:
    text = str(value or "").strip()
    return default if not text or text.lower() in {"none", "nan", "nat"} else text


def _customer(customer_id: Any) -> Dict[str, Any]:
    try:
        target = int(customer_id)
    except (TypeError, ValueError):
        return {}
    for row in list_customers() or []:
        try:
            if int(row.get("id")) == target:
                return row
        except (TypeError, ValueError):
            continue
    return {}


def _fmt_money(value: Any, currency: str = "THB") -> str:
    try:
        return f"{float(value or 0):,.2f} {currency}"
    except (TypeError, ValueError):
        return f"0.00 {currency}"


def _document_preview(invoice: Dict[str, Any], items: list[dict]) -> None:
    doc_type = str(invoice.get("doc_type") or "INV").upper()
    title = DOC_TYPES.get(doc_type, doc_type)
    customer = _customer(invoice.get("customer_id"))
    selected_no = invoice.get("doc_no") or invoice.get("invoice_no")
    status = finance._status(selected_no, invoice.get("status"))
    copy_label = "ต้นฉบับ / Original + สำเนา / Copy" if doc_type == "INV" else "Original"

    section("Document Preview")
    st.caption(f"{title} · {copy_label} · Status: {status}")

    head_left, head_right = st.columns([2, 1])
    with head_left:
        st.markdown(
            f"**{_safe(customer.get('company_name') or invoice.get('customer_name'), 'Customer')}**\n\n"
            f"Tax ID: {_safe(customer.get('tax_id') or invoice.get('customer_tax_id'))}\n\n"
            f"Billing Address: {_safe(customer.get('address') or invoice.get('customer_address'))}"
        )
    with head_right:
        st.markdown(
            f"**{title}**\n\n"
            f"Document No.: `{_safe(selected_no)}`\n\n"
            f"Issue Date: {_safe(invoice.get('issue_date'))}\n\n"
            f"Due Date: {_safe(invoice.get('due_date'))}\n\n"
            f"Reference: {_safe(invoice.get('ref_doc_no') or invoice.get('job_no'))}"
        )

    shipping = invoice.get("shipping_address") or invoice.get("delivery_address")
    if shipping:
        st.info(f"Shipping / Delivery Address\n\n{shipping}")

    rows = []
    for idx, item in enumerate(items or [], 1):
        rows.append({
            "No.": idx,
            "Description": item.get("description") or item.get("charge_code") or "",
            "Qty": item.get("quantity") or 0,
            "Unit": item.get("unit") or item.get("package_unit") or "",
            "Unit Price": _fmt_money(item.get("unit_price"), invoice.get("currency", "THB")),
            "Discount": _fmt_money(item.get("discount", 0), invoice.get("currency", "THB")),
            "Amount": _fmt_money(item.get("amount"), invoice.get("currency", "THB")),
        })
    st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")

    summary = dict(invoice.get("summary") or {})
    total_before = summary.get("total_before_vat", invoice.get("subtotal", 0))
    vat = summary.get("total_vat_7", invoice.get("vat_amount", 0))
    wht = summary.get("wht_total", invoice.get("wht_amount", 0))
    total = summary.get("grand_total", invoice.get("total_amount", invoice.get("grand_total", 0)))
    currency = invoice.get("currency", "THB")

    left, right = st.columns([1.4, 1])
    with left:
        st.text_area("Remarks", value=str(invoice.get("remark") or ""), disabled=True, height=85)
        st.caption("Official document validation and tax rules are enforced by the finance/PDF layers.")
    with right:
        st.metric("Subtotal", _fmt_money(total_before, currency))
        st.metric("VAT", _fmt_money(vat, currency))
        if float(wht or 0) > 0:
            st.metric("WHT", _fmt_money(wht, currency))
        st.metric("Grand Total", _fmt_money(total, currency))
        st.metric("Outstanding", _fmt_money(invoice.get("outstanding"), currency))

    sig1, sig2, sig3 = st.columns(3)
    sig1.info("Payer / Receiver\n\n__________________\nDate: ____ / ____ / ______")
    sig2.info("Customer / Received by\n\n__________________\nDate: ____ / ____ / ______")
    sig3.info("Authorized Signature\n\n__________________\nNATTAYARAAT CO., LTD.")


def render() -> None:
    page_header("billing", status_text="Online")
    user = st.session_state.get("user", {})
    can_edit = can_write(str(user.get("role", "")).lower(), "billing")
    rows = list_invoices() or []

    section("Finance Control")
    total = sum(float(r.get("total_amount") or r.get("grand_total") or 0) for r in rows if str(r.get("status", "")).upper() != "CANCELLED")
    outstanding = sum(float(r.get("outstanding") or 0) for r in rows if str(r.get("status", "")).upper() != "CANCELLED")
    paid = max(total - outstanding, 0.0)
    a, b, c = st.columns(3)
    a.metric("Total Billed", f"{total:,.2f}")
    b.metric("Total Paid", f"{paid:,.2f}")
    c.metric("Outstanding", f"{outstanding:,.2f}")

    filters = st.columns([2, 3, 1])
    with filters[0]:
        dtype = st.selectbox("Document Type", ["ALL"] + list(DOC_TYPES), format_func=lambda x: "All Documents" if x == "ALL" else DOC_TYPES[x], key="finance_dtype")
    with filters[1]:
        query = st.text_input("Search", placeholder="Document, Customer, Job or Reference", key="finance_search").strip().lower()
    with filters[2]:
        new_doc = st.button("New Document", type="primary", width="stretch") if can_edit else False

    if dtype != "ALL":
        rows = [r for r in rows if r.get("doc_type") == dtype]
    if query:
        rows = [r for r in rows if query in str(r).lower()]

    if new_doc:
        st.session_state["finance_new"] = True

    if st.session_state.get("finance_new") and can_edit:
        finance._new(user)
        if st.button("Close New Document", key="finance_new_close"):
            st.session_state.pop("finance_new", None)
            st.rerun()
        return

    section("Document Register")
    display = [{
        "Document No.": r.get("doc_no") or r.get("invoice_no"),
        "Type": DOC_TYPES.get(r.get("doc_type"), r.get("doc_type")),
        "Customer": r.get("customer_name"),
        "Job": r.get("job_no"),
        "Issue Date": r.get("issue_date"),
        "Due Date": r.get("due_date"),
        "Total": _fmt_money(r.get("grand_total", r.get("total_amount")), r.get("currency", "THB")),
        "Outstanding": _fmt_money(r.get("outstanding"), r.get("currency", "THB")),
        "Status": finance._status(r.get("doc_no") or r.get("invoice_no"), r.get("status")),
    } for r in rows]
    st.dataframe(pd.DataFrame(display), hide_index=True, width="stretch")

    choices = [r.get("doc_no") or r.get("invoice_no") for r in rows if r.get("doc_no") or r.get("invoice_no")]
    if choices:
        selected = st.selectbox("Select Document", choices, key="finance_selected_document")
        invoice, items = finance.get_invoice_snapshot(selected)
        if not invoice:
            st.error("Selected document could not be loaded.")
            return
        status = finance._status(selected, invoice.get("status"))
        customer = _customer(invoice.get("customer_id"))

        section("Customer & Credit Control")
        c1, c2 = st.columns(2)
        c1.markdown(
            f"**{customer.get('company_name') or invoice.get('customer_name') or '—'}**\n\n"
            f"Tax ID: {customer.get('tax_id') or invoice.get('customer_tax_id') or '—'}\n\n"
            f"Payment Term: {customer.get('credit_days') or customer.get('payment_term') or '—'} days\n\n"
            f"Credit Limit: {_fmt_money(customer.get('credit_limit'), invoice.get('currency', 'THB'))}"
        )
        c2.markdown(
            f"**Current Document**\n\nStatus: **{status}**\n\n"
            f"Outstanding: **{_fmt_money(invoice.get('outstanding'), invoice.get('currency', 'THB'))}**\n\n"
            f"Due Date: **{invoice.get('due_date') or '—'}**"
        )

        section("Document Actions")
        a, b, c, d, e = st.columns([1, 1, 1, 1, 1])
        with a:
            finance._pdf(selected)
        with b:
            from views.receipt_view import render_receipt_action
            render_receipt_action(selected)
        with c:
            if can_edit and status == "Draft" and st.button("Edit", key=f"finance_edit_{selected}", width="stretch"):
                st.session_state["finance_edit_selected"] = selected
                st.rerun()
        with d:
            if can_edit and status == "Draft" and st.button("Submit", key=f"finance_submit_{selected}", width="stretch"):
                finance.submit_for_approval("invoice", selected, user)
                st.rerun()
            elif finance.can_approve("invoice", user) and status == "Pending Approval" and st.button("Approve", key=f"finance_approve_{selected}", type="primary", width="stretch"):
                finance.approve_document("invoice", selected, user)
                st.rerun()
        with e:
            if can_edit and st.button("Duplicate", key=f"finance_duplicate_{selected}", width="stretch"):
                new_no = finance.duplicate_invoice(selected, user)
                st.success(f"Created {new_no} as Draft.")
                st.rerun()

        if can_edit and status == "Draft" and st.session_state.get("finance_edit_selected") == selected:
            finance._edit(selected)

        _document_preview(invoice, items)

    else:
        st.info("No finance documents match the current filters.")

    with st.expander("Payments", expanded=False):
        finance._payments()
