"""Production Finance workspace for Phase 30.

Reuses the existing financial engine for calculations, AR and payments while
providing a compact SSOT/approval/PDF workflow aligned to the supplied NTT
Billing Note / Receipt-Tax Invoice / Delivery Invoice references.
"""
from __future__ import annotations

import os
from datetime import date, timedelta
from typing import Any, Dict, List, Optional
import pandas as pd
import streamlit as st

from managers.auth_manager import can_write
from managers.charge_master_manager import list_charges
from managers.customer_manager import list_customers
from managers.document_approval_manager import approve_document, can_approve, get_approval_status, submit_for_approval
from managers.document_duplicate_service import duplicate_invoice, get_invoice_snapshot, update_invoice_draft
from managers.invoice_manager import TAX_TYPES, WHT_TYPES, create_invoice, list_invoices, record_payment, calculate_summary
from managers.shipment_manager import list_shipments
from ui.design_system import page_header, section

CURRENCIES = ["THB", "USD", "EUR", "CNY"]
PAYMENT_METHODS = ["Bank Transfer", "Cash", "Cheque", "Credit Card"]
DOC_TYPES = {
    "INV": "ใบเสร็จรับเงิน / ใบกำกับภาษี — Receipt / Tax Invoice",
    "BN": "ใบวางบิล — Billing Note",
    "CN": "ใบลดหนี้ — Credit Note",
    "DN": "ใบเพิ่มหนี้ — Debit Note",
    "SOA": "ใบแจ้งยอดบัญชี — Statement of Account",
}


def _invoice_status(doc_no: str, fallback: str = "Draft") -> str:
    try:
        return get_approval_status("invoice", doc_no)
    except Exception:
        return fallback or "Draft"


def _customer_master(customer_id: Any) -> Dict[str, Any]:
    if customer_id is None:
        return {}
    for row in list_customers() or []:
        try:
            if int(row.get("id")) == int(customer_id):
                return row
        except (TypeError, ValueError):
            continue
    return {}


def _charge_master() -> Dict[str, Dict[str, Any]]:
    charges = list_charges() or []
    return {c.get("charge_code") or c.get("code") or "": c for c in charges if c.get("charge_code") or c.get("code")}


def _customer_label(customer: Dict[str, Any]) -> str:
    return str(customer.get("company_name") or customer.get("display_name") or customer.get("legal_name") or "")


def _credit_summary(customer: Dict[str, Any]) -> str:
    credit_limit = customer.get("credit_limit")
    credit_days = customer.get("credit_days") or customer.get("payment_term")
    tax_id = customer.get("tax_id")
    chunks = []
    if tax_id:
        chunks.append(f"Tax ID: {tax_id}")
    if credit_limit not in (None, ""):
        chunks.append(f"Credit Limit: {float(credit_limit):,.2f}")
    if credit_days not in (None, ""):
        chunks.append(f"Terms: {credit_days}")
    return " · ".join(chunks)


def _pdf(doc_no: str) -> None:
    bytes_key = f"finance_pdf_bytes_{doc_no}"
    name_key = f"finance_pdf_name_{doc_no}"
    if st.button("PDF", key=f"finance_pdf_{doc_no}", type="primary", width="stretch"):
        try:
            from pdf.invoice_pdf import generate_invoice_pdf
            invoice, items = get_invoice_snapshot(doc_no)
            status = _invoice_status(doc_no, invoice.get("status"))
            customer = _customer_master(invoice.get("customer_id"))
            payload = {**invoice, "items": items, "approval_status": status, "status": status}
            output = generate_invoice_pdf(payload, customer=customer)
            if not output or not os.path.exists(output):
                raise FileNotFoundError("Invoice PDF generator did not return a valid file.")
            with open(output, "rb") as fh:
                st.session_state[bytes_key] = fh.read()
            st.session_state[name_key] = os.path.basename(output)
        except Exception as exc:
            st.error(f"Unable to create PDF: {exc}")
    if st.session_state.get(bytes_key):
        st.download_button(
            "Download",
            st.session_state[bytes_key],
            file_name=st.session_state.get(name_key, f"{doc_no}.pdf"),
            mime="application/pdf",
            key=f"finance_download_{doc_no}",
            width="stretch",
        )


def _customer_card(customer: Optional[Dict[str, Any]]) -> None:
    if not customer:
        return
    section("Customer Snapshot")
    a, b = st.columns(2)
    a.markdown(f"**{customer.get('company_name', '—')}**\n\nTax ID: {customer.get('tax_id') or '—'}\n\nContact: {customer.get('contact_person') or '—'}")
    b.markdown(f"**Billing Address**\n\n{customer.get('address') or customer.get('billing_address') or '—'}\n\nTel: {customer.get('tel') or '—'} · Email: {customer.get('email') or '—'}")


def _new(user: Dict[str, Any]) -> None:
    customers = list_customers() or []
    cmap = {int(c["id"]): c for c in customers if c.get("id")}
    jobs = list_shipments(limit=200) or []
    jmap = {j.get("job_no"): j for j in jobs if j.get("job_no")}
    charge_map = _charge_master()

    section("New Financial Document")
    with st.form("finance_v2_new"):
        a, b, c = st.columns(3)
        typ = a.selectbox("Document", list(DOC_TYPES), format_func=lambda x: DOC_TYPES[x])
        cid = b.selectbox("Customer", list(cmap), format_func=lambda x: cmap[x].get("company_name", str(x)) if cmap else "—")
        job = c.selectbox("Linked Job", [""] + list(jmap))
        customer = cmap.get(cid) if cid else None
        if customer:
            st.caption(f"Customer Tax ID: {customer.get('tax_id') or '—'} · Billing Address loaded from Customer Master")
        a, b, c = st.columns(3)
        issue = a.date_input("Issue Date", date.today())
        due = b.date_input("Due Date", date.today() + timedelta(days=30))
        currency = c.selectbox("Currency", CURRENCIES)
        ref = st.text_input("Reference / Job Ref.", value=job or "")

        section("Charge Lines")
        if "finance_v2_items" not in st.session_state:
            st.session_state["finance_v2_items"] = [{"charge_code": "", "quantity": 1.0, "unit_price": 0.0, "tax": TAX_TYPES[0], "wht": WHT_TYPES[0] if WHT_TYPES else "None"}]
        items = []
        for i, row in enumerate(st.session_state["finance_v2_items"]):
            a, b, c, d, e = st.columns([4, 1, 1.5, 1.2, 1.2])
            codes = [""] + list(charge_map)
            code = a.selectbox("Charge", codes, index=codes.index(row.get("charge_code", "")) if row.get("charge_code", "") in codes else 0, format_func=lambda x: f"{x} — {charge_map[x].get('description', '')}" if x else "Select charge", key=f"fin_code_{i}")
            qty = b.number_input("Qty", min_value=0.01, value=float(row.get("quantity", 1)), key=f"fin_qty_{i}")
            rate = c.number_input("Unit Price", min_value=0.0, value=float(row.get("unit_price", 0)), step=100.0, key=f"fin_rate_{i}")
            tax = d.selectbox("VAT", TAX_TYPES, index=TAX_TYPES.index(row.get("tax")) if row.get("tax") in TAX_TYPES else 0, key=f"fin_tax_{i}")
            wht = e.selectbox("WHT", WHT_TYPES, index=WHT_TYPES.index(row.get("wht")) if row.get("wht") in WHT_TYPES else 0, key=f"fin_wht_{i}")
            desc = charge_map.get(code, {}).get("description", "") if code else ""
            items.append({"charge_code": code, "description": desc or code, "quantity": qty, "unit_price": rate, "tax_type": tax, "wht_type": wht})
        remark = st.text_area("Remarks / Payment Terms", placeholder="Example: Payment within 30 days from invoice date.")
        save = st.form_submit_button("Create Draft", type="primary", width="stretch")

    summary = calculate_summary(items)
    st.markdown(f"**Preview Total:** {float(summary['grand_total']):,.2f} {currency} · VAT {float(summary['total_vat_7']):,.2f} · WHT {float(summary['wht_total']):,.2f}")
    if save:
        if not cid:
            st.error("Customer is required.")
            return
        if not any(x["description"] and x["unit_price"] > 0 for x in items):
            st.error("Select at least one charge and enter a positive rate.")
            return
        try:
            doc = create_invoice(
                {
                    "doc_type": typ,
                    "job_no": job or None,
                    "customer_id": cid,
                    "customer_name": customer.get("company_name") if customer else None,
                    "issue_date": issue.isoformat(),
                    "due_date": due.isoformat(),
                    "currency": currency,
                    "ref_doc_no": ref.strip(),
                    "remark": remark.strip(),
                    "created_by": user.get("username", "system"),
                    "status": "DRAFT",
                },
                items,
            )
            st.session_state["finance_v2_items"] = [{"charge_code": "", "quantity": 1.0, "unit_price": 0.0, "tax": TAX_TYPES[0], "wht": WHT_TYPES[0] if WHT_TYPES else "None"}]
            st.success(f"Created {doc} as Draft.")
            st.rerun()
        except Exception as exc:
            st.error(f"Unable to create document: {exc}")


def _edit(doc_no: str) -> None:
    inv, items = get_invoice_snapshot(doc_no)
    if not inv:
        st.error("Invoice not found.")
        return
    charge_map = _charge_master()
    section(f"Edit {doc_no} Draft")
    with st.form(f"finance_edit_{doc_no}"):
        a, b = st.columns(2)
        ref = a.text_input("Reference / Job Ref.", inv.get("ref_doc_no") or "")
        due = b.date_input("Due Date", date.fromisoformat(str(inv.get("due_date"))[:10]) if inv.get("due_date") else date.today())
        remark = st.text_area("Remarks", inv.get("remark") or "")

        section("Line Items")
        edited_items = []
        for i, item in enumerate(items):
            a, b, c = st.columns([3, 1, 1.5])
            desc = a.text_input("Description", item.get("description") or "", key=f"edit_desc_{doc_no}_{i}")
            qty = b.number_input("Qty", min_value=0.01, value=float(item.get("quantity") or 1), key=f"edit_qty_{doc_no}_{i}")
            price = c.number_input("Unit Price", min_value=0.0, value=float(item.get("unit_price") or 0), key=f"edit_price_{doc_no}_{i}")
            edited_items.append({**item, "description": desc, "quantity": qty, "unit_price": price})
        saved = st.form_submit_button("Save Changes", type="primary", width="stretch")
    if saved:
        try:
            update_invoice_draft(doc_no, {"ref_doc_no": ref.strip(), "due_date": due.isoformat(), "remark": remark.strip()}, edited_items)
            st.success("Draft updated.")
            st.rerun()
        except Exception as exc:
            st.error(f"Unable to update draft: {exc}")


def render() -> None:
    page_header("billing", status_text="Online")
    user = st.session_state.get("user", {})
    can_edit = can_write(str(user.get("role", "")).lower(), "billing")
    invoices = list_invoices() or []

    a, b = st.columns([4, 1])
    query = a.text_input("Search Invoices", placeholder="Invoice No., Customer, Job No.", key="fin_v2_search")
    new = b.button("New Document", type="primary", width="stretch") if can_edit else False

    if query.strip():
        invoices = [inv for inv in invoices if query.strip().lower() in str(inv).lower()]

    section("Invoice Ledger")
    st.dataframe(
        pd.DataFrame([
            {
                "Doc No.": inv.get("doc_no") or inv.get("invoice_no"),
                "Type": DOC_TYPES.get(inv.get("doc_type"), inv.get("doc_type")),
                "Customer": inv.get("customer_name"),
                "Job": inv.get("job_no"),
                "Amount": f"{float(inv.get('grand_total') or 0):,.2f} {inv.get('currency', 'THB')}",
                "Status": _invoice_status(inv.get("doc_no") or inv.get("invoice_no"), inv.get("status")),
            }
            for inv in invoices
        ]),
        hide_index=True,
        width="stretch",
    )

    if new:
        _new(user)

    if not invoices:
        st.info("No invoice records found.")
        return

    doc_ids = [inv.get("doc_no") or inv.get("invoice_no") for inv in invoices if (inv.get("doc_no") or inv.get("invoice_no"))]
    selected_doc = st.selectbox("Select Document", doc_ids, key="fin_selected_doc")
    if not selected_doc:
        return

    invoice, items = get_invoice_snapshot(selected_doc)
    status = _invoice_status(selected_doc, invoice.get("status"))
    customer = _customer_master(invoice.get("customer_id"))

    _customer_card(customer)

    section("Actions")
    a, b, c, d = st.columns([2, 1, 1, 1])
    with a:
        _pdf(selected_doc)
    with b:
        if can_edit and status == "Draft" and st.button("Submit", key=f"fin_submit_{selected_doc}", width="stretch"):
            try:
                submit_for_approval("invoice", selected_doc, user)
                st.rerun()
            except Exception as exc:
                st.error(str(exc))
    with c:
        if can_approve("invoice", user) and status == "Pending Approval" and st.button("Approve", key=f"fin_approve_{selected_doc}", type="primary", width="stretch"):
            try:
                approve_document("invoice", selected_doc, user)
                st.rerun()
            except Exception as exc:
                st.error(str(exc))
    with d:
        if can_edit and st.button("Duplicate", key=f"fin_dup_{selected_doc}", width="stretch"):
            try:
                new_no = duplicate_invoice(selected_doc, user)
                st.success(f"Duplicated as {new_no}")
                st.rerun()
            except Exception as exc:
                st.error(str(exc))

    if can_edit and status == "Draft":
        _edit(selected_doc)
