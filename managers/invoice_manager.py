from typing import List, Dict, Any, Optional
from database.connection import get_connection
from managers.doc_number import generate_doc_number

TAX_TYPES = ["VAT 7%", "Non-VAT", "Advance"]
WHT_TYPES = ["None", "WHT 1%", "WHT 3%"]

def create_invoice(data: Dict[str, Any], items: List[Dict[str, Any]]) -> str:
    """Create invoice with items inside a single transaction."""
    doc_type = data.get("doc_type", "INV")
    doc_no = generate_doc_number(doc_type, data.get("issue_date"))
    summary = calculate_summary(items)
    
    with get_connection() as conn:
        # 1. Insert Invoice Header
        cur = conn.execute("""
            INSERT INTO invoices (
                doc_no, doc_type, shipment_id, job_no, customer_id, customer_name, 
                issue_date, due_date, currency, subtotal, vat_rate, vat_amount, 
                wht_amount, total_amount, outstanding, payment_status, 
                ref_doc_no, remark, created_by, advance_amount, 
                wht_1_amount, wht_3_amount
            ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            RETURNING id
        """, (
            doc_no, doc_type, data.get("shipment_id"), data.get("job_no"),
            data.get("customer_id"), data.get("customer_name"),
            data.get("issue_date"), data.get("due_date"),
            data.get("currency", "THB"), summary["total_before_vat"], 7.0, 
            summary["total_vat_7"], summary["wht_total"], summary["grand_total"], 
            summary["grand_total"], "Unpaid", data.get("ref_doc_no"), 
            data.get("remark"), data.get("created_by"), summary["total_advance"],
            summary["wht_1_amount"], summary["wht_3_amount"]
        ))
        invoice_id = cur.fetchone()['id']
        
        # 2. Insert Invoice Items
        for idx, item in enumerate(items):
            conn.execute("""
                INSERT INTO invoice_items (invoice_id, description, quantity, unit_price, amount, tax_type, wht_type, sort_order)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
            """, (invoice_id, item.get("description"), item.get("quantity", 1), 
                  item.get("unit_price", 0), item.get("amount", 0),
                  item.get("tax_type", "VAT 7%"), item.get("wht_type", "None"), idx))
        
        conn.commit()
    return doc_no

def get_invoice_by_no(doc_no: str) -> Optional[Dict[str, Any]]:
    with get_connection() as conn:
        invoice = conn.execute("SELECT * FROM invoices WHERE doc_no=%s", (doc_no,)).fetchone()
        if not invoice: return None
        
        items = conn.execute("SELECT * FROM invoice_items WHERE invoice_id=%s ORDER BY sort_order", 
                             (invoice['id'],)).fetchall()
        
        invoice = dict(invoice)
        invoice["items"] = [dict(i) for i in items]
        invoice["summary"] = calculate_summary(invoice["items"])
        return invoice