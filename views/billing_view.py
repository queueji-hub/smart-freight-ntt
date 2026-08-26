"""Billing & Financial Documents — Phase 30 UI standard.

Keeps the existing financial manager as the source of truth and adds a compact,
safe document action layer: PDF, Edit (DRAFT only), and Duplicate (new DRAFT).
"""

import os
import uuid
from datetime import date, timedelta
from typing import Dict, Any, List

import pandas as pd
import streamlit as st

from managers.auth_manager import can_write
from managers.customer_manager import get_customer, list_customers
from managers.invoice_manager import (
    TAX_TYPES,
    WHT_TYPES,
    calculate_summary,
    create_invoice,
    list_invoices,
    record_payment,
    get_outstanding_summary,
)
from views.navigation_helper import get_active_tab, redirect_to_tab
from managers.shipment_manager import list_shipments
from managers.document_duplicate_service import (
    duplicate_invoice,
    get_invoice_snapshot,
    update_invoice_draft,
)
from managers.document_approval_manager import get_approval_status

DOC_TYPES: Dict[str, str] = {
    "INV": "Invoice",
    "BN": "Billing Note",
    "CN": "Credit Note",
    "DN": "Debit Note",
    "SOA": "Statement of Account",
}
CURRENCIES = ["THB", "USD", "EUR", "CNY"]
PAYMENT_METHODS = ["Bank Transfer", "Cash", "Cheque", "Credit Card"]


def _empty_item() -> Dict[str, Any]:
    return {
        "id": str(uuid.uuid4())[:8],
        "description": "",
        "quantity": 1.0,
        "unit_price": 0.0,
        "tax_type": TAX_TYPES[0] if TAX_TYPES else "VAT 7%",
        "wht_type": WHT_TYPES[0] if WHT_TYPES else "None",
    }


def _render_kpis() -> None:
    try:
        kpi = get_outstanding_summary() or {}
    except Exception as exc:
        st.warning(f"Unable to load financial KPIs: {exc}")
        kpi = {}
    c1, c2, c3 = st.columns(3)
    c1.metric("Billed", f"฿ {float(kpi.get('billed', 0)):,.2f}")
    c2.metric("Paid", f"฿ {float(kpi.get('paid', 0)):,.2f}")
    c3.metric("Outstanding", f"฿ {float(kpi.get('outstanding', 0)):,.2f}")


def _approval_status(doc_no: str, fallback: str = "Draft") -> str:
    try:
        return get_approval_status("invoice", doc_no)
    except Exception:
        value = str(fallback or "Draft").strip().upper()
        return "Approved" if value == "APPROVED" else ("Pending Approval" if value in {"PENDING", "PENDING APPROVAL", "SUBMITTED"} else "Draft")


def _prepare_invoice_pdf(doc_no: str) -> None:
    """Generate the invoice PDF only after the user explicitly clicks PDF."""
    bytes_key = f"inv_pdf_bytes_{doc_no}"
    name_key = f"inv_pdf_name_{doc_no}"
    try:
        from pdf.invoice_pdf import generate_invoice_pdf

        inv, _items = get_invoice_snapshot(doc_no)
        status = _approval_status(doc_no, inv.get("status"))
        # Keep the existing PDF generator signature unchanged. Its current
        # watermark decision is based on payment_status/status, so map the
        # approval state into a temporary render-only copy.
        inv = dict(inv)
        inv["approval_status"] = status
        inv["status"] = status
        inv["payment_status"] = "ISSUED" if status == "Approved" else "DRAFT"
        pdf_path = generate_invoice_pdf(inv)
        if not pdf_path or not os.path.exists(pdf_path):
            raise FileNotFoundError("Invoice PDF generator did not return a valid file.")
        with open(pdf_path, "rb") as fh:
            st.session_state[bytes_key] = fh.read()
        st.session_state[name_key] = os.path.basename(pdf_path)
    except Exception as exc:
        st.error(f"PDF: {exc}")


def render() -> None:
    user = st.session_state.get("user", {})
    can_edit = can_write(user.get("role", ""), "billing")

    st.subheader("Billing & Finance")
    st.caption("Financial documents, payments and controlled document operations")
    _render_kpis()
    st.divider()

    tab_opts = ["Documents", "Payments"] + (["New Document"] if can_edit else [])
    get_active_tab("billing_active_tab", tab_opts)

    active_tab = st.radio(
        "Billing Navigation",
        tab_opts,
        horizontal=True,
        key="billing_active_tab",
        label_visibility="collapsed"
    )

    if active_tab == "Documents":
        _list_view(user, can_edit)
    elif active_tab == "Payments":
        _payment_view()
    elif active_tab == "New Document" and can_edit:
        _create_form(user)


def _create_form(user: Dict[str, Any]) -> None:
    st.markdown("### New Financial Document")
    c1, c2 = st.columns(2)
    with c1:
        doc_type = st.selectbox("Document Type", list(DOC_TYPES), format_func=lambda x: DOC_TYPES[x], key="fin_new_type")
        customers = list_customers() or []
        options = [(0, "Select customer")] + [
            (c.get("id"), f"{c.get('customer_code') or c.get('party_code') or 'C'} — {c.get('display_name') or c.get('company_name', 'Unknown')}")
            for c in customers if c.get("id")
        ]
        idx = st.selectbox("Customer", range(len(options)), format_func=lambda i: options[i][1], key="fin_new_customer")
        customer_id, _customer_label = options[idx]
        jobs = list_shipments() or []
        jobs_opt = [("", "No linked Job")] + [(j.get("job_no"), f"{j.get('job_no')} — {j.get('customer_name', '')}") for j in jobs[:200]]
        job_idx = st.selectbox("Linked Job", range(len(jobs_opt)), format_func=lambda i: jobs_opt[i][1], key="fin_new_job")
        job_no = jobs_opt[job_idx][0]
    with c2:
        issue_date = st.date_input("Issue Date", date.today(), key="fin_new_issue")
        due_date = st.date_input("Due Date", date.today() + timedelta(days=30), key="fin_new_due")
        currency = st.selectbox("Currency", CURRENCIES, key="fin_new_currency")
        ref_doc = st.text_input("Reference", key="fin_new_ref")

    if "billing_items" not in st.session_state:
        st.session_state["billing_items"] = [_empty_item()]

    st.markdown("### Line Items")
    for item in st.session_state["billing_items"]:
        cols = st.columns([4, 1, 1.5, 1.5, 1.5, .5])
        item["description"] = cols[0].text_input("Description", item["description"], key=f"nd_{item['id']}", label_visibility="collapsed", placeholder="Description")
        item["quantity"] = cols[1].number_input("Qty", min_value=.01, value=float(item["quantity"]), key=f"nq_{item['id']}", label_visibility="collapsed")
        item["unit_price"] = cols[2].number_input("Unit Price", min_value=0.0, value=float(item["unit_price"]), step=100.0, key=f"np_{item['id']}", label_visibility="collapsed")
        cols[3].markdown(f"**{item['quantity'] * item['unit_price']:,.2f}**")
        item["tax_type"] = cols[4].selectbox("Tax", TAX_TYPES, index=TAX_TYPES.index(item["tax_type"]) if item["tax_type"] in TAX_TYPES else 0, key=f"nt_{item['id']}", label_visibility="collapsed")
        if cols[5].button("×", key=f"nx_{item['id']}"):
            st.session_state["billing_items"] = [x for x in st.session_state["billing_items"] if x["id"] != item["id"]]
            st.rerun()

    ac1, ac2 = st.columns([1, 5])
    if ac1.button("+ Add Item", key="fin_add_item"):
        st.session_state["billing_items"].append(_empty_item())
        st.rerun()
    summary = calculate_summary(st.session_state["billing_items"])
    ac2.markdown(f"**Total: {float(summary.get('grand_total', 0)):,.2f} {currency}**")
    remark = st.text_area("Remarks", key="fin_new_remark")

    if st.button("Create Document", type="primary", use_container_width=True, key="fin_create"):
        if not customer_id:
            st.error("Customer is required.")
            return
        if not any(i.get("description", "").strip() for i in st.session_state["billing_items"]):
            st.error("At least one line item is required.")
            return
        try:
            payload = {
                "doc_type": doc_type, "job_no": job_no or None, "customer_id": customer_id,
                "issue_date": issue_date.isoformat(),
                "due_date": due_date.isoformat(), "currency": currency,
                "ref_doc_no": ref_doc.strip(), "remark": remark.strip(),
                "created_by": user.get("username", "System"), "status": "DRAFT",
            }
            doc_no = create_invoice(payload, st.session_state["billing_items"])
            redirect_to_tab("billing_active_tab", "Documents")
            st.session_state["fin_action_doc"] = doc_no
            st.session_state["billing_items"] = [_empty_item()]
            st.success(f"Created {doc_no}")
            st.rerun()
        except Exception as exc:
            st.error(f"Create failed: {exc}")



def _list_view(user: Dict[str, Any], can_edit: bool) -> None:
    st.markdown("### Financial Documents")
    try:
        rows = list_invoices() or []
    except Exception as exc:
        st.error(f"Failed to load documents: {exc}")
        return
    if not rows:
        st.info("No financial documents found.")
        return

    c1, c2 = st.columns([3, 1])
    search = c1.text_input("Search", placeholder="Document or customer", key="fin_search")
    status = c2.selectbox("Status", ["All", "DRAFT", "ISSUED", "PARTIAL", "PAID", "CANCELLED"], key="fin_status")
    filtered = rows
    if search:
        q = search.lower()
        filtered = [r for r in filtered if q in str(r).lower()]
    if status != "All":
        filtered = [r for r in filtered if str(r.get("status", "")).upper() == status]

    df = pd.DataFrame(filtered)
    st.dataframe(df, use_container_width=True, hide_index=True, column_config={
        "doc_no": st.column_config.TextColumn("Document No.", width="medium"),
        "doc_type": st.column_config.TextColumn("Type", width="small"),
        "customer_name": st.column_config.TextColumn("Customer", width="large"),
        "issue_date": st.column_config.DateColumn("Issue Date"),
        "due_date": st.column_config.DateColumn("Due Date"),
        "grand_total": st.column_config.NumberColumn("Total", format="%.2f"),
        "status": st.column_config.TextColumn("Status", width="small"),
    })

    st.markdown("### Document Actions")
    doc_nos = [r.get("doc_no") for r in filtered if r.get("doc_no")]
    if not doc_nos:
        return
    selected = st.selectbox("Select document", doc_nos, key="fin_action_doc")
    rec = next(r for r in filtered if r.get("doc_no") == selected)
    a1, a2, a3, a4 = st.columns([3, 1, 1, 1])
    with a1:
        st.caption(f"{rec.get('doc_type', 'DOC')} · {rec.get('customer_name', '')} · {_approval_status(selected, rec.get('status'))}")
    with a2:
        bytes_key = f"inv_pdf_bytes_{selected}"
        name_key = f"inv_pdf_name_{selected}"
        if st.button("PDF", key=f"fin_pdf_prepare_{selected}", type="primary", use_container_width=True):
            _prepare_invoice_pdf(selected)
            st.rerun()
        if bytes_key in st.session_state:
            st.download_button(
                "Download",
                st.session_state[bytes_key],
                file_name=st.session_state.get(name_key, f"{selected}.pdf"),
                mime="application/pdf",
                key=f"fin_pdf_download_{selected}",
                use_container_width=True,
            )
    with a3:
        if can_edit and str(rec.get("status", "")).upper() == "DRAFT":
            if st.button("Edit", key=f"fin_edit_{selected}", use_container_width=True):
                st.session_state["fin_edit_doc"] = selected
                st.rerun()
        else:
            st.button("Edit", disabled=True, key=f"fin_edit_disabled_{selected}", use_container_width=True)
    with a4:
        if can_edit:
            if st.button("Duplicate", key=f"fin_dup_{selected}", use_container_width=True):
                try:
                    new_no = duplicate_invoice(selected, user)
                    st.success(f"Duplicated as {new_no}")
                    st.rerun()
                except Exception as exc:
                    st.error(f"Duplicate failed: {exc}")

    if can_edit and st.session_state.get("fin_edit_doc") == selected:
        _edit_form(selected, user)


def _edit_form(doc_no: str, user: Dict[str, Any]) -> None:
    st.markdown(f"#### Edit {doc_no}")
    try:
        inv, items = get_invoice_snapshot(doc_no)
    except Exception as exc:
        st.error(str(exc))
        return
    if str(inv.get("payment_status", "")).upper() != "DRAFT":
        st.warning("Only DRAFT documents can be edited.")
        return

    customers = list_customers() or []
    customer_map = {c.get("id"): c.get("company_name", "Unknown") for c in customers if c.get("id")}
    customer_ids = list(customer_map)
    current_customer_id = inv.get("customer_id")
    if current_customer_id not in customer_ids:
        st.error("Customer master data is missing for this invoice.")
        return
    customer_index = customer_ids.index(current_customer_id)

    c1, c2 = st.columns(2)
    selected_customer_id = c1.selectbox(
        "Customer",
        customer_ids,
        index=customer_index,
        format_func=lambda x: customer_map.get(x, "Unknown"),
        key=f"fe_customer_{doc_no}",
    )
    job_no = c2.text_input("Linked Job", value=str(inv.get("job_no") or ""), key=f"fe_j_{doc_no}")
    d1, d2, d3 = st.columns(3)
    issue = d1.date_input("Issue Date", value=inv.get("issue_date") or date.today(), key=f"fe_i_{doc_no}")
    due = d2.date_input("Due Date", value=inv.get("due_date") or date.today(), key=f"fe_d_{doc_no}")
    currency = d3.selectbox("Currency", CURRENCIES, index=CURRENCIES.index(inv.get("currency", "THB")) if inv.get("currency", "THB") in CURRENCIES else 0, key=f"fe_cur_{doc_no}")
    ref = st.text_input("Reference", value=str(inv.get("ref_doc_no") or ""), key=f"fe_r_{doc_no}")
    remark = st.text_area("Remarks", value=str(inv.get("remark") or ""), key=f"fe_m_{doc_no}")

    clean_items: List[Dict[str, Any]] = []
    for idx, item in enumerate(items):
        q1, q2, q3, q4 = st.columns([4, 1, 1.5, 1.5])
        desc = q1.text_input("Description", value=str(item.get("description") or ""), key=f"fei_desc_{doc_no}_{idx}")
        qty = q2.number_input("Qty", min_value=.01, value=float(item.get("quantity") or 1), key=f"fei_qty_{doc_no}_{idx}")
        price = q3.number_input("Unit Price", min_value=0.0, value=float(item.get("unit_price") or 0), key=f"fei_price_{doc_no}_{idx}")
        tax = q4.selectbox("Tax", TAX_TYPES, index=TAX_TYPES.index(item.get("tax_type")) if item.get("tax_type") in TAX_TYPES else 0, key=f"fei_tax_{doc_no}_{idx}")
        clean_items.append({"description": desc, "quantity": qty, "unit_price": price, "tax_type": tax, "wht_type": item.get("wht_type", "None")})

    b1, b2 = st.columns([1, 5])
    if b1.button("Save", type="primary", key=f"fe_save_{doc_no}"):
        try:
            update_invoice_draft(doc_no, {
                "customer_id": selected_customer_id,
                "job_no": job_no or None, "issue_date": issue.isoformat(), "due_date": due.isoformat(),
                "currency": currency, "ref_doc_no": ref.strip(), "remark": remark.strip(),
            }, clean_items)
            st.success(f"{doc_no} updated")
            st.session_state.pop("fin_edit_doc", None)
            st.rerun()
        except Exception as exc:
            st.error(f"Update failed: {exc}")
    if b2.button("Cancel", key=f"fe_cancel_{doc_no}"):
        st.session_state.pop("fin_edit_doc", None)
        st.rerun()


def _payment_view() -> None:
    st.markdown("### Payments")
    try:
        invoices = [i for i in (list_invoices() or []) if str(i.get("status", "")).upper() != "PAID"]
    except Exception as exc:
        st.error(f"Failed to load payments: {exc}")
        return
    if not invoices:
        st.info("No outstanding documents.")
        return
    mapping = {f"{i['doc_no']} · {i.get('customer_name', '')} · {float(i.get('grand_total', 0)):,.2f} {i.get('currency', 'THB')}": i for i in invoices}
    selected = st.selectbox("Outstanding document", list(mapping), key="pay_doc")
    inv = mapping[selected]
    c1, c2 = st.columns(2)
    amount = c1.number_input("Payment Amount", min_value=.01, value=float(inv.get("grand_total", 0) or 0), key="pay_amt")
    method = c2.selectbox("Payment Method", PAYMENT_METHODS, key="pay_method")
    reference = st.text_input("Transaction Reference", key="pay_ref")
    payment_date = st.date_input("Payment Date", date.today(), key="pay_date")
    if st.button("Record Payment", type="primary", key="pay_save"):
        try:
            record_payment({"doc_no": inv["doc_no"], "amount": amount, "method": method, "reference": reference.strip(), "date": payment_date.isoformat()})
            st.success(f"Payment recorded for {inv['doc_no']}.")
            st.rerun()
        except Exception as exc:
            st.error(f"Payment failed: {exc}")
