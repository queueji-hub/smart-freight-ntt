"""Invoice / Billing Note / CN / DN / SOA management."""
from datetime import date, datetime, timedelta
from typing import List, Dict, Any, Optional
from database.connection import get_connection
from managers.doc_number import generate_doc_number

TAX_TYPES = ["VAT 7%", "Non-VAT", "Advance"]
WHT_TYPES = ["None", "WHT 1%", "WHT 3%"]

def _ensure_tables():
    """Ensure invoices and invoice_items tables exist."""
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS invoices (
                id SERIAL PRIMARY KEY,
                doc_no TEXT UNIQUE NOT NULL,
                doc_type TEXT NOT NULL,
                shipment_id INTEGER,
                job_no TEXT,
                customer_id INTEGER,
                customer_name TEXT,
                issue_date DATE,
                due_date DATE,
                currency TEXT DEFAULT 'THB',
                subtotal NUMERIC(15,2),
                vat_rate NUMERIC(5,2),
                vat_amount NUMERIC(15,2),
                wht_rate NUMERIC(5,2),
                wht_amount NUMERIC(15,2),
                total_amount NUMERIC(15,2),
                paid_amount NUMERIC(15,2) DEFAULT 0,
                outstanding NUMERIC(15,2),
                payment_status TEXT DEFAULT 'Unpaid',
                payment_date DATE,
                ref_doc_no TEXT,
                remark TEXT,
                created_by TEXT,
                advance_amount NUMERIC(15,2) DEFAULT 0,
                non_vat_amount NUMERIC(15,2) DEFAULT 0,
                wht_1_amount NUMERIC(15,2) DEFAULT 0,
                wht_3_amount NUMERIC(15,2) DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS invoice_items (
                id SERIAL PRIMARY KEY,
                invoice_id INTEGER REFERENCES invoices(id) ON DELETE CASCADE,
                description TEXT,
                quantity NUMERIC(15,2),
                unit_price NUMERIC(15,2),
                amount NUMERIC(15,2),
                tax_type TEXT,
                wht_type TEXT,
                sort_order INTEGER
            )
        """)

def calculate_summary(items: List[Dict[str, Any]]) -> Dict[str, float]:
    """Calculate all financial breakdown."""
    total_before_vat = 0.0
    total_vat_7 = 0.0
    total_advance = 0.0
    wht_1_amount = 0.0
    wht_3_amount = 0.0
    
    for item in items:
        amount = float(item.get("amount", 0) or 0)
        tax_type = item.get("tax_type") or "VAT 7%"
        wht_type = item.get("wht_type") or "None"
        
        if tax_type == "Advance":
            total_advance += amount
            continue
        
        total_before_vat += amount
        if tax_type == "VAT 7%":
            total_vat_7 += amount * 0.07
        
        if wht_type == "WHT 1%":
            wht_1_amount += amount * 0.01
        elif wht_type == "WHT 3%":
            wht_3_amount += amount * 0.03
    
    total_before_wht = total_before_vat + total_vat_7 + total_advance
    grand_total = total_before_wht - wht_1_amount - wht_3_amount
    
    return {
        "total_before_vat": round(total_before_vat, 2),
        "total_vat_7": round(total_vat_7, 2),
        "total_advance": round(total_advance, 2),
        "total_before_wht": round(total_before_wht, 2),
        "wht_1_amount": round(wht_1_amount, 2),
        "wht_3_amount": round(wht_3_amount, 2),
        "wht_total": round(wht_1_amount + wht_3_amount, 2),
        "grand_total": round(grand_total, 2),
    }

def create_invoice(data: Dict[str, Any], items: List[Dict[str, Any]]) -> str:
    _ensure_tables()
    doc_type = data.get("doc_type", "INV")
    doc_no = generate_doc_number(doc_type, data.get("issue_date"))
    summary = calculate_summary(items)
    
    with get_connection() as conn:
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
        invoice_id = cur.fetchone()[0]
        
        for idx, item in enumerate(items):
            conn.execute("""
                INSERT INTO invoice_items (invoice_id, description, quantity, unit_price, amount, tax_type, wht_type, sort_order)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
            """, (invoice_id, item.get("description"), item.get("quantity", 1), 
                  item.get("unit_price", 0), item.get("amount", 0),
                  item.get("tax_type", "VAT 7%"), item.get("wht_type", "None"), idx))
    return doc_no

def get_invoice_by_no(doc_no: str) -> Optional[Dict[str, Any]]:
    _ensure_tables()
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM invoices WHERE doc_no=%s", (doc_no,)).fetchone()
        if not row: return None
        invoice = dict(row)
        items = conn.execute("SELECT * FROM invoice_items WHERE invoice_id=%s ORDER BY sort_order", (invoice["id"],)).fetchall()
        invoice["items"] = [dict(i) for i in items]
        invoice["summary"] = calculate_summary(invoice["items"])
        return invoice

def get_outstanding_summary() -> Dict[str, Any]:
    """Calculate total outstanding invoices for Dashboard."""
    _ensure_tables()
    with get_connection() as conn:
        # ใช้ Alias 'cnt' และ 'outstanding' ให้ตรงกับความต้องการของ Dashboard
        row = conn.execute("""
            SELECT COUNT(*) as cnt, COALESCE(SUM(outstanding), 0) as outstanding
            FROM invoices 
            WHERE payment_status != 'Paid'
        """).fetchone()
        
        # กรณีไม่มีข้อมูลในตารางเลย
        if not row:
            return {"total_invoices": 0, "outstanding": 0.0}
            
        # ตรวจสอบรูปแบบ: ถ้าเป็น dict (จาก Driver) หรือ tuple (จาก DB แบบดั้งเดิม)
        if isinstance(row, dict):
            return {
                "total_invoices": row.get('cnt', 0), 
                "outstanding": float(row.get('outstanding', 0))
            }
        
        # กรณีเป็น tuple เข้าถึงด้วย index
        return {
            "total_invoices": row[0], 
            "outstanding": float(row[1])
        }