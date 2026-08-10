import os
import sys

# Add root directory to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from database.connection import get_connection
from managers.auth_manager import hash_password
from managers.customer_manager import create_customer
from managers.shipment_manager import create_shipment, add_job_container, get_job_financial_summary
from managers.vendor_manager import create_vendor
from managers.ap_manager import create_ap_voucher, update_ap_voucher_status
from managers.invoice_manager import create_invoice, record_payment
from managers.document_manager import upload_document, link_document
import managers.tenant_context as tc

def master_qa():
    print("=== D70 MASTER E2E FREIGHT PRODUCTION QA ===")
    
    tenant_id = "default"
    
    user = {"id": 999, "username": "qa_admin", "role": "admin", "tenant_id": tenant_id}
    
    # Mock tenant context at root level for things that check session state if we inject it
    class DummyUser:
        def __init__(self):
            self.user = user
    import streamlit as st
    st.session_state = DummyUser()
    
    # Ensure tenant isolated setup
    print("[1] Setup Tenant Isolated Master Data...")
    
    cust_id = create_customer({"company_name": "QA Exporter Ltd.", "country": "TH"})
    print(f"  -> Customer ID: {cust_id}")
    
    import uuid
    qa_run = str(uuid.uuid4())[:4]
    
    vendor_id = create_vendor({"vendor_code": f"V-QA-{qa_run}", "legal_name": "QA Ocean Line", "currency": "USD"}, user)
    print(f"  -> Vendor ID: {vendor_id}")
    
    print("\n[2] Execution of Job / Shipment...")
    job_no = create_shipment({
        "direction": "Export",
        "transport_mode": "Sea",
        "job_type": "FCL",
        "etd": "2026-10-01",
        "eta": "2026-10-30",
        "customer_id": cust_id
    }, user)
    print(f"  -> Job No: {job_no}")
    
    print("\n[3] Container Control (D65)...")
    add_job_container({
        "job_no": job_no,
        "container_no": f"QATU999{qa_run}",
        "container_type": "40HQ",
        "seal_no": "S-12345"
    })
    print(f"  -> Added Container to {job_no}")
    
    print("\n[4] Accounts Payable (D62 & D63)...")
    ap_id = create_ap_voucher({
        "vendor_id": vendor_id,
        "job_no": job_no,
        "invoice_no": f"INV-QA-V-{qa_run}",
        "invoice_date": "2026-09-15",
        "due_date": "2026-10-15",
        "currency": "USD",
        "exchange_rate": 35.0, # 1 USD = 35 THB
        "subtotal": 1000.0,
        "tax": 0.0,
        "total": 1000.0
    }, user)
    print(f"  -> Created AP Voucher ID: {ap_id}")
    update_ap_voucher_status(ap_id, "POSTED", user)
    print(f"  -> AP Voucher {ap_id} approved and POSTED.")
    
    print("\n[5] Accounts Receivable (D64)...")
    inv_no = create_invoice({
        "doc_type": "INV",
        "customer_id": cust_id,
        "job_no": job_no,
        "issue_date": "2026-09-20",
        "currency": "THB",
        "status": "APPROVED"
    }, [{"description": "Ocean Freight", "quantity": 1, "unit_price": 50000.0, "tax_type": "Non-VAT"}])
    print(f"  -> Created Customer Invoice No: {inv_no} for 50,000 THB")
    
    record_payment({
        "doc_no": inv_no,
        "amount": 50000.0,
        "method": "Bank Transfer",
        "date": "2026-09-25"
    })
    print(f"  -> Recorded payment of 50,000 THB for {inv_no}")
    
    print("\n[6] Job Profitability Integration (D63)...")
    # Resolve shipment_id
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM shipments WHERE job_no=%s AND tenant_id=%s", (job_no, tenant_id))
            shipment_id = cur.fetchone()["id"]
            
    summary = get_job_financial_summary(shipment_id)
    print(f"  -> Total Revenue (THB): {summary['total_revenue_thb']:,.2f}")
    print(f"  -> Total Cost (THB): {summary['total_cost_thb']:,.2f}")
    print(f"  -> Gross Profit (THB): {summary['gross_profit_thb']:,.2f}")
    print(f"  -> Margin (%): {summary['margin_percent']:.2f}%")
    
    assert summary['total_revenue_thb'] == 50000.0, "Revenue mismatch"
    assert summary['total_cost_thb'] == 35000.0, "Cost mismatch (AP not picked up correctly)"
    assert summary['gross_profit_thb'] == 15000.0, "Profit mismatch"
    
    print("\n[7] Document Control (D56, D57, D60)...")
    doc_id = upload_document("Commercial Invoice", "COMMERCIAL DOCUMENTS", "DOC-001", b"TEST FILE", "test.pdf", "application/pdf", "2026-09-20", "Test", user, "job", str(shipment_id))
    print(f"  -> Uploaded and Linked Document ID: {doc_id} to Job")
    link_document(doc_id, "ap_voucher", str(ap_id), user)
    print(f"  -> Polymorphic Link: Document {doc_id} also linked to AP Voucher {ap_id}")
    
    print("\n[OK] MASTER QA E2E PASSED!")

if __name__ == "__main__":
    master_qa()
