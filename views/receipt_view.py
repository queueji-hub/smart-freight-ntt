"""Receipt PDF action layer for Billing & Finance.

This view deliberately reuses the canonical invoice/financial manager and
customer directory. It does not create a second financial data store.
"""
import os
import streamlit as st

from managers.document_duplicate_service import get_invoice_snapshot
from managers.customer_manager import get_customer
from pdf.receipt_pdf import generate_receipt_pdf


def render_receipt_action(doc_no: str) -> None:
    """Render a single receipt/tax-invoice PDF action for an existing document."""
    try:
        invoice, items = get_invoice_snapshot(doc_no)
        invoice = dict(invoice or {})
        invoice["items"] = items or []
        customer = get_customer(invoice.get("customer_id")) if invoice.get("customer_id") else None
        pdf_path = generate_receipt_pdf(invoice, customer=customer)
        with open(pdf_path, "rb") as fh:
            st.download_button(
                "Receipt / Tax Invoice",
                fh.read(),
                file_name=os.path.basename(pdf_path),
                mime="application/pdf",
                key=f"receipt_pdf_{doc_no}",
                use_container_width=True,
            )
    except Exception as exc:
        st.error(f"Receipt PDF: {exc}")
