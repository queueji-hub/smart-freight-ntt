"""Production Finance workspace for Phase 30.

Reuses the existing financial engine for calculations, AR and payments while
providing a compact SSOT/approval/PDF workflow aligned to the supplied NTT
Billing Note / Receipt-Tax Invoice / Delivery Invoice references.
"""
from __future__ import annotations

import os
from datetime import date, timedelta
from typing import Any, Dict, List

import pandas as pd
import streamlit as st

from managers.auth_manager import can_write
from managers.charge_master_manager import list_charges
from managers.customer_manager import list_customers
from managers.document_approval_manager import approve_document, can_approve, get_approval_status, submit_for_approval
from managers.document_duplicate_service import duplicate_invoice, get_invoice_snapshot, update_invoice_draft
from managers.invoice_manager import TAX_TYPES, WHT_TYPES, create_invoice, list_invoices, record_payment
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


def _pdf_action(doc_no: str) -> None:
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


def _charge_master() -> Dict[str, Dict[str, Any]]:
    charges = list_charges(active_only=True) or []
    return {
        str(c.get("charge_code") or c.get("code") or "").strip().upper(): c
        for c in charges
        if str(c.get("charge_code") or c.get("code") or "").strip()
    }


def _new_document(user: Dict[str, Any]) -> None:
    customers = list_customers() or []
    customer_map = {int(c["id"]): _customer_label(c) for c in customers if c.get("id")}
    jobs = list_shipments(limit=200) or []
    job_map = {j.get("job_no"): j.get("job_no") for j in jobs if j.get("job_no")}
    charge_map = _charge_master()

    section("New Financial Document")
    with st.form("finance_v2_new"):
        c1, c2, c3 = st.columns(3)
        doc_type = c1.selectbox("Document Type", list(DOC_TYPES), format_func=lambda x: DOC_TYPES[x])
        customer_id = c2.selectbox("Customer *", list(customer_map), format_func=lambda x: customer_map[x]) if customer_map else None
        job_no = c3.selectbox("Linked Job", [""] + list(job_map))

        if customer_id:
            master_customer = _customer_master(customer_id)
            st.caption(_credit_summary(master_customer) or "Customer master data loaded")

        section("Document Details")
        d1, d2, d3, d4 = st.columns(4)
        issue_date = d1.date_input("Issue Date", date.today())
        due_date = d2.date_input("Due Date", date.today() + timedelta(days=30))
        currency = d3.selectbox("Currency", CURRENCIES)
        reference = d4.text_input("Reference / Job Ref.", value=job_no or "")

        section("Bill To / Tax Information")
        if customer_id:
            customer = _customer_master(customer_id)
            b1, b2 = st.columns(2)
            with b1:
                st.text_input("Customer", value=_customer_label(customer), disabled=True)
                st.text_area("Billing Address", value=str(customer.get("address") or customer.get("billing_address") or ""), disabled=True, height=70)
            with b2:
                st.text_input("Tax ID", value=str(customer.get("tax_id") or ""), disabled=True)
                st.text_input("Branch", value=str(customer.get("branch_name") or customer.get("branch_no") or ""), disabled=True)
        else:
            st.info("Select a Customer Master record to load billing identity.")

        section("Charges")
        st.caption("Charges are selected from Charge Master. Description, basis, unit and default currency are canonical master data.")
        if "finance_v2_items" not in st.session_state:
            st.session_state["finance_v2_items"] = [{"charge_code": "", "quantity": 1.0, "unit_price": 0.0, "tax_type": TAX_TYPES[0], "wht_type": WHT_TYPES[0] if WHT_TYPES else "None"}]

        item_rows: List[Dict[str, Any]] = []
        for idx, item in enumerate(st.session_state["finance_v2_items"]):
            q1, q2, q3, q4 = st.columns([4, 1, 1.5, 1.5])
            codes = [""] + list(charge_map)
            code = q1.selectbox(
                "Charge *",
                codes,
                index=codes.index(item.get("charge_code", "")) if item.get("charge_code", "") in codes else 0,
                format_func=lambda x: f"{x} — {charge_map[x].get('description', '')}" if x else "Select charge",
                key=f"fin_charge_{idx}",
            )
            qty = q2.number_input("Qty", min_value=0.01, value=float(item.get("quantity", 1)), key=f"fin_qty_{idx}")
            unit_price = q3.number_input("Unit Rate", min_value=0.0, value=float(item.get("unit_price", 0)), step=100.0, key=f"fin_rate_{idx}")
            tax = q4.selectbox("Tax", TAX_TYPES, index=TAX_TYPES.index(item.get("tax_type")) if item.get("tax_type") in TAX_TYPES else 0, key=f"fin_tax_{idx}")
            master = charge_map.get(code, {}) if code else {}
            description = master.get("description", "")
            item_rows.append({
                "charge_code": code or None,
                "description": description,
                "basis": master.get("default_basis"),
                "unit": master.get("default_unit"),
                "currency": master.get("default_currency") or currency,
                "quantity": qty,
                "unit_price": unit_price,
                "tax_type": tax,
                "wht_type": item.get("wht_type", "None"),
            })

        remark = st.text_area("Remarks")
        save = st.form_submit_button("Create Draft", type="primary", width="stretch")

    if save:
        if not customer_id:
            st.error("Customer is required.")
            return
        if not any(r["description"] and r["unit_price"] > 0 for r in item_rows):
            st.error("Select at least one Charge Master item and enter a positive rate.")
            return
        if due_date < issue_date:
            st.error("Due Date cannot be earlier than Issue Date.")
            return
        try:
            master_customer = _customer_master(customer_id)
            doc_no = create_invoice(
                {
                    "doc_type": doc_type,
                    "job_no": job_no or None,
                    "customer_id": customer_id,
                    "customer_name": _customer_label(master_customer),
                    "issue_date": issue_date.isoformat(),
                    "due_date": due_date.isoformat(),
                    "ref_doc_no": reference.strip() or None,
                    "currency": currency,
                    "remark": remark.strip(),
                    "created_by": user.get("username", "system"),
                    "status": "DRAFT",
                },
                item_rows,
            )
            st.session_state["finance_v2_items"] = [{"charge_code": "", "quantity": 1.0, "unit_price": 0.0, "tax_type": TAX_TYPES[0], "wht_type": WHT_TYPES[0] if WHT_TYPES else "None"}]
            st.success(f"Created {doc_no} as Draft.")
            st.rerun()
        except Exception as exc:
            st.error(f"Unable to create document: {exc}")


def _edit_document(doc_no: str, user: Dict[str, Any]) -> None:
    invoice, items = get_invoice_snapshot(doc_no)
    if _invoice_status(doc_no, invoice.get("status")) != "Draft":
        st.info("Only Draft documents can be edited.")
        return
    customers = list_customers() or []
    customer_map = {int(c["id"]): _customer_label(c) for c in customers if c.get("id")}
    current = invoice.get("customer_id")
    if current not in customer_map:
        st.error("Customer master data is missing for this document.")
        return
    charge_map = _charge_master()
    with st.expander(f"Edit {doc_no}", expanded=True):
        with st.form(f"finance_edit_{doc_no}"):
            c1, c2 = st.columns(2)
            customer_id = c1.selectbox("Customer", list(customer_map), index=list(customer_map).index(current), format_func=lambda x: customer_map[x])
            job_no = c2.text_input("Linked Job", value=str(invoice.get("job_no") or ""))
            d1, d2, d3, d4 = st.columns(4)
            issue = d1.date_input("Issue Date", invoice.get("issue_date") or date.today())
            due = d2.date_input("Due Date", invoice.get("due_date") or date.today())
            currency = d3.selectbox("Currency", CURRENCIES, index=CURRENCIES.index(invoice.get("currency", "THB")) if invoice.get("currency", "THB") in CURRENCIES else 0)
            reference = d4.text_input("Reference / Job Ref.", value=str(invoice.get("ref_doc_no") or job_no or ""))
            clean_items = []
            for idx, item in enumerate(items):
                q1, q2, q3, q4 = st.columns([4, 1, 1.5, 1.5])
                existing_code = str(item.get("charge_code") or "").upper()
                codes = [""] + list(charge_map)
                code = q1.selectbox("Charge *", codes, index=codes.index(existing_code) if existing_code in codes else 0, format_func=lambda x: f"{x} — {charge_map[x].get('description', '')}" if x else "Select charge", key=f"edit_charge_{doc_no}_{idx}")
                master = charge_map.get(code, {}) if code else {}
                qty = q2.number_input("Qty", min_value=0.01, value=float(item.get("quantity") or 1), key=f"edit_qty_{doc_no}_{idx}")
                rate = q3.number_input("Unit Rate", min_value=0.0, value=float(item.get("unit_price") or 0), key=f"edit_rate_{doc_no}_{idx}")
                tax = q4.selectbox("Tax", TAX_TYPES, index=TAX_TYPES.index(item.get("tax_type")) if item.get("tax_type") in TAX_TYPES else 0, key=f"edit_tax_{doc_no}_{idx}")
                clean_items.append({
                    "charge_code": code or None,
                    "description": master.get("description") or item.get("description") or "",
                    "basis": master.get("default_basis"),
                    "unit": master.get("default_unit"),
                    "currency": master.get("default_currency") or currency,
                    "quantity": qty,
                    "unit_price": rate,
                    "tax_type": tax,
                    "wht_type": item.get("wht_type", "None"),
                })
            save = st.form_submit_button("Save Changes", type="primary", width="stretch")
        if save:
            if due < issue:
                st.error("Due Date cannot be earlier than Issue Date.")
                return
            update_invoice_draft(doc_no, {"customer_id": customer_id, "job_no": job_no or None, "issue_date": issue.isoformat(), "due_date": due.isoformat(), "ref_doc_no": reference.strip() or None, "currency": currency}, clean_items)
            st.success("Document updated.")
            st.rerun()


def _payments() -> None:
    section("Payments")
    rows = [r for r in (list_invoices() or []) if str(r.get("status", "")).upper() not in {"PAID", "CANCELLED"}]
    if not rows:
        st.info("No outstanding documents.")
        return
    labels = [f"{r.get('doc_no')} · {r.get('customer_name', '')} · {float(r.get('grand_total', 0) or 0):,.2f} {r.get('currency', 'THB')}" for r in rows]
    idx = st.selectbox("Outstanding document", range(len(labels)), format_func=lambda i: labels[i], key="finance_pay_doc")
    rec = rows[idx]
    c1, c2 = st.columns(2)
    amount = c1.number_input("Payment Amount", min_value=0.01, value=float(rec.get("outstanding", rec.get("grand_total", 0)) or 0), key="finance_pay_amount")
    method = c2.selectbox("Payment Method", PAYMENT_METHODS, key="finance_pay_method")
    reference = st.text_input("Transaction Reference", key="finance_pay_reference")
    payment_date = st.date_input("Payment Date", date.today(), key="finance_pay_date")
    if st.button("Record Payment", type="primary", width="stretch", key="finance_pay_save"):
        try:
            record_payment({"doc_no": rec["doc_no"], "amount": amount, "method": method, "reference": reference.strip(), "date": payment_date.isoformat()})
            st.success("Payment recorded.")
            st.rerun()
        except Exception as exc:
            st.error(f"Payment failed: {exc}")


def render() -> None:
    page_header("billing", status_text="Online")
    user = st.session_state.get("user", {})
    role = str(user.get("role", "")).lower()
    can_edit = can_write(role, "billing")

    tabs = st.tabs(["Documents", "Payments"] + (["New Document"] if can_edit else []))
    with tabs[0]:
        rows = list_invoices() or []
        q = st.text_input("Search", placeholder="Document, customer or Job", key="finance_v2_search")
        if q.strip():
            ql = q.strip().lower()
            rows = [r for r in rows if ql in str(r).lower()]
        st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")
        if rows:
            choices = [r.get("doc_no") for r in rows if r.get("doc_no")]
            selected = st.selectbox("Select document", choices, key="finance_v2_selected")
            rec = next(r for r in rows if r.get("doc_no") == selected)
            status = _invoice_status(selected, rec.get("status"))
            actions = st.columns([3, 1, 1, 1, 1])
            actions[0].caption(f"{rec.get('doc_type', 'DOC')} · {rec.get('customer_name', '—')} · {status}")
            with actions[1]:
                _pdf_action(selected)
            with actions[2]:
                if can_edit and status == "Draft" and st.button("Edit", key=f"finance_edit_{selected}", width="stretch"):
                    st.session_state["finance_edit"] = selected
                    st.rerun()
            with actions[3]:
                if can_edit and status == "Draft" and st.button("Submit", key=f"finance_submit_{selected}", width="stretch"):
                    submit_for_approval("invoice", selected, user)
                    st.rerun()
                elif can_approve("invoice", user) and status == "Pending Approval" and st.button("Approve", key=f"finance_approve_{selected}", type="primary", width="stretch"):
                    approve_document("invoice", selected, user)
                    st.rerun()
            with actions[4]:
                if can_edit and st.button("Duplicate", key=f"finance_duplicate_{selected}", width="stretch"):
                    new_no = duplicate_invoice(selected, user)
                    st.success(f"Created {new_no} as Draft.")
                    st.rerun()
            if can_edit and st.session_state.get("finance_edit") == selected:
                _edit_document(selected, user)
    with tabs[1]:
        _payments()
    if can_edit:
        with tabs[2]:
            _new_document(user)
