from typing import Dict, Any, List, Optional
import time
from database.connection import get_connection
from managers.tenant_context import get_current_tenant_id
from managers.ap_manager import create_ap_voucher

def process_ap_invoice_ocr(document_id: int, file_path: str, user: Dict[str, Any]) -> Dict[str, Any]:
    """
    Mock OCR Processing for AP Invoices.
    Reads a document and creates a DRAFT AP Voucher for human review.
    Must never auto-post.
    """
    tenant_id = get_current_tenant_id()
    
    # Mock OCR extraction logic (in real world, this would call AWS Textract, Google Document AI, or Rossum)
    # We simulate a delay for processing
    time.sleep(1)
    
    extracted_data = {
        "vendor_id": None, # Needs manual review or fuzzy matching
        "vendor_name": "EXTRACTED VENDOR LLC",
        "doc_no": f"OCR-INV-{int(time.time())}",
        "issue_date": "2026-10-01",
        "due_date": "2026-10-31",
        "currency": "THB",
        "total_amount": 10000.0,
        "tax_amount": 700.0,
        "grand_total": 10700.0,
        "job_no": None # Needs to be linked manually
    }
    
    # Create a DRAFT AP Voucher
    ap_data = {
        "vendor_id": None,
        "vendor_name": extracted_data["vendor_name"],
        "doc_no": extracted_data["doc_no"],
        "job_no": extracted_data["job_no"],
        "issue_date": extracted_data["issue_date"],
        "due_date": extracted_data["due_date"],
        "currency": extracted_data["currency"],
        "exchange_rate": 1.0,
        "remark": "Auto-extracted via OCR. Please review.",
        "status": "DRAFT", # CRITICAL: Must be DRAFT
        "created_by": "OCR_SYSTEM"
    }
    
    ap_items = [
        {
            "description": "OCR Extracted Line Item",
            "quantity": 1,
            "unit_price": extracted_data["total_amount"],
            "tax_type": "VAT 7%" if extracted_data["tax_amount"] > 0 else "Non-VAT",
            "wht_type": "None"
        }
    ]
    
    try:
        ap_id = create_ap_voucher(ap_data, ap_items)
        
        # Link document to the new AP Voucher
        from managers.document_manager import link_document
        link_document(document_id, "ap_voucher", str(ap_id), user)
        
        return {
            "success": True,
            "ap_voucher_id": ap_id,
            "extracted_data": extracted_data,
            "message": "OCR successful. Draft AP Voucher created for review."
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }
