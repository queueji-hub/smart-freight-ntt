"""Job-centric Document Center.

No file upload/storage UI. Documents are generated from authoritative Job/transaction data.
"""
from __future__ import annotations

import os
import streamlit as st

from managers.booking_manager import get_booking
from managers.bl_workflow_service import list_bls
from managers.document_approval_manager import approve_document, can_approve, get_approval_status, submit_for_approval
from managers.invoice_manager import list_invoices
from managers.profit_manager import get_profit_summary
from managers.shipment_manager import get_shipment, list_shipments
from ui.design_system import page_header, section


def _pdf_download(key: str, generator, filename: str, *args, **kwargs) -> None:
    if st.button("PDF", key=f"doc_pdf_{key}", type="primary", width="stretch"):
        try:
            output = generator(*args, **kwargs)
            if not output or not os.path.exists(output):
                raise FileNotFoundError("PDF generator did not return a valid file.")
            with open(output, "rb") as fh:
                st.session_state[f"doc_pdf_bytes_{key}"] = fh.read()
            st.session_state[f"doc_pdf_name_{key}"] = os.path.basename(output)
        except Exception as exc:
            st.error(f"PDF failed: {exc}")
    if st.session_state.get(f"doc_pdf_bytes_{key}"):
        st.download_button(
            "Download",
            st.session_state[f"doc_pdf_bytes_{key}"],
            file_name=st.session_state.get(f"doc_pdf_name_{key}", filename),
            mime="application/pdf",
            key=f"doc_dl_{key}",
            width="stretch",
        )


def _approval_actions(doc_type: str, doc_no: str, status: str, user: dict, key: str) -> None:
    c1, c2 = st.columns(2)
    if status == "Draft" and st.session_state.get("_can_write_documents", False):
        with c1:
            if st.button("Submit", key=f"doc_submit_{key}", width="stretch"):
                try:
                    submit_for_approval(doc_type, doc_no, user)
                    st.rerun()
                except Exception as exc:
                    st.error(str(exc))
    if status == "Pending Approval" and can_approve(doc_type, user):
        with c2:
            if st.button("Approve", key=f"doc_approve_{key}", type="primary", width="stretch"):
                try:
                    approve_document(doc_type, doc_no, user)
                    st.rerun()
                except Exception as exc:
                    st.error(str(exc))


def render() -> None:
    page_header("document", status_text="Online")
    user = st.session_state.get("user", {})
    role = str(user.get("role", "")).lower()
    can_write_docs = role in {"admin", "manager", "accounting", "operations", "sales"}
    st.session_state["_can_write_documents"] = can_write_docs

    jobs = list_shipments(limit=200) or []
    if not jobs:
        st.info("No Jobs available. Create a Job first.")
        return

    job_options = [j.get("job_no") for j in jobs if j.get("job_no")]
    selected_job_no = st.selectbox("Job", job_options, key="document_v2_job")
    job = get_shipment(selected_job_no)
    if not job:
        st.error("Selected Job was not found.")
        return

    section("Job Documents")
    summary = st.columns(5)
    summary[0].metric("Job", selected_job_no)
    summary[1].metric("Customer", job.get("customer_name") or "—")
    summary[2].metric("Mode", job.get("mode") or job.get("job_type") or "—")
    summary[3].metric("POL", job.get("pol") or "—")
    summary[4].metric("POD", job.get("pod") or "—")

    # Booking Confirmation
    booking_no = job.get("booking_no")
    if booking_no:
        booking = get_booking(booking_no, user.get("tenant_id"))
        if booking:
            status = get_approval_status("booking", booking_no)
            c1, c2, c3 = st.columns([5, 1, 1])
            c1.write(f"**Booking Confirmation** · `{booking_no}` · {status}")
            with c2:
                def booking_pdf(record=booking, status=status):
                    from pdf.booking_pdf import generate_booking_pdf
                    return generate_booking_pdf(record, approval_status=status)
                _pdf_download(f"booking_{booking_no}", booking_pdf, f"BC_{booking_no}.pdf")
            with c3:
                _approval_actions("booking", booking_no, status, user, f"booking_{booking_no}")

    # B/L
    bls = list_bls(job_no=selected_job_no) or []
    for bl in bls:
        bl_no = bl.get("bl_no")
        status = get_approval_status("bl", bl_no)
        c1, c2, c3 = st.columns([5, 1, 1])
        c1.write(f"**{bl.get('bl_type', 'B/L')}** · `{bl_no}` · {status}")
        with c2:
            def bl_pdf(record=bl):
                from pdf.bl_pdf import generate_bl_pdf
                payload = {"bl": record, "job": job, "booking": booking if booking_no and 'booking' in locals() else {}, "containers": []}
                return generate_bl_pdf(payload)
            _pdf_download(f"bl_{bl_no}", bl_pdf, f"{bl_no}.pdf")
        with c3:
            _approval_actions("bl", bl_no, status, user, f"bl_{bl_no}")

    # Financial documents
    invoices = [r for r in (list_invoices() or []) if r.get("job_no") == selected_job_no]
    for inv in invoices:
        doc_no = inv.get("doc_no")
        status = get_approval_status("invoice", doc_no)
        c1, c2, c3 = st.columns([5, 1, 1])
        c1.write(f"**{inv.get('doc_type', 'Invoice')}** · `{doc_no}` · {status}")
        with c2:
            def invoice_pdf(doc_no=doc_no):
                from pdf.invoice_pdf import generate_invoice_pdf
                from managers.document_duplicate_service import get_invoice_snapshot
                data, items = get_invoice_snapshot(doc_no)
                data = {**data, "items": items, "approval_status": status, "status": status}
                return generate_invoice_pdf(data)
            _pdf_download(f"invoice_{doc_no}", invoice_pdf, f"{doc_no}.pdf")
        with c3:
            _approval_actions("invoice", doc_no, status, user, f"invoice_{doc_no}")

    # Job Sheet
    section("Operational Reports")
    c1, c2 = st.columns([5, 1])
    c1.write("**Job Sheet** · operational snapshot")
    with c2:
        profit = get_profit_summary(job.get("id"))
        def job_sheet_pdf():
            from pdf.report_generator import generate_job_sheet_pdf
            return generate_job_sheet_pdf(job_data=job, profit_data=profit, milestones=[])
        _pdf_download(f"job_{selected_job_no}", job_sheet_pdf, f"{selected_job_no}_JobSheet.pdf")

    c1, c2 = st.columns([5, 1])
    c1.write("**Job Profitability** · revenue / cost / margin")
    with c2:
        def profitability_pdf():
            from pdf.profitability_pdf import generate_profitability_pdf
            return generate_profitability_pdf(job, profit)
        _pdf_download(f"profit_{selected_job_no}", profitability_pdf, f"Profitability_{selected_job_no}.pdf")
