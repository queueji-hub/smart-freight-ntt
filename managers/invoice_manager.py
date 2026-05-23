"""Invoice / Billing Note / CN / DN / SOA management.

Per-row tax handling:
- tax_type: 'VAT 7%' | 'Non-VAT' | 'Advance' (เงินทดรองจ่าย)
- wht_type: 'None' | 'WHT 1%' | 'WHT 3%'

Financial summary structure:
1. Total Before VAT (taxable + non-vat items, excludes Advance)
2. Total VAT 7% (only from rows with tax_type='VAT 7%')
3. Total Advance (sum of rows with tax_type='Advance')
4. Total Before WHT (= Total Before VAT + VAT + Advance)
5. WHT 1% Amount (calculated only from rows with wht_type='WHT 1%')
6. WHT 3% Amount (calculated only from rows with wht_type='WHT 3%')
7. Grand Total = (Total Before VAT + VAT 7% + Advance) - (WHT 1% + WHT 3%)
"""
from datetime import date, datetime, timedelta
from typing import List, Dict, Any, Optional
from database.connection import get_connection
from managers.doc_number import generate_doc_number


TAX_TYPES = ["VAT 7%", "Non-VAT", "Advance"]
WHT_TYPES = ["None", "WHT 1%", "WHT 3%"]


def calculate_summary(items: List[Dict[str, Any]]) -> Dict[str, float]:
    """Calculate all financial breakdown from per-row tax/wht selections.
    
    Each item should have:
        amount: float (line subtotal = qty * unit_price)
        tax_type: 'VAT 7%' | 'Non-VAT' | 'Advance'
        wht_type: 'None' | 'WHT 1%' | 'WHT 3%'
    """
    total_before_vat = 0.0  # Sum of VAT-7% + Non-VAT amounts (excludes Advance)
    total_vat_7 = 0.0        # 7% of VAT-7% rows
    total_advance = 0.0      # Sum of Advance rows
    wht_1_amount = 0.0       # 1% of rows marked "WHT 1%"
    wht_3_amount = 0.0       # 3% of rows marked "WHT 3%"
    
    for item in items:
        amount = float(item.get("amount", 0) or 0)
        tax_type = item.get("tax_type") or "VAT 7%"
        wht_type = item.get("wht_type") or "None"
        
        if tax_type == "Advance":
            total_advance += amount
            # Advance is exempt from VAT and WHT
            continue
        
        # VAT 7% or Non-VAT both contribute to "before VAT" total
        total_before_vat += amount
        
        if tax_type == "VAT 7%":
            total_vat_7 += amount * 0.07
        # Non-VAT: no VAT
        
        # WHT calculated on amount (before VAT, Thai standard)
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
    """Create new invoice/CN/DN/BN/SOA. Returns the doc_no."""
    doc_type = data.get("doc_type", "INV")
    doc_no = generate_doc_number(doc_type, data.get("issue_date"))
    
    issue_date = data.get("issue_date")
    if isinstance(issue_date, str):
        issue_date = datetime.strptime(issue_date, "%Y-%m-%d").date()
    elif issue_date is None:
        issue_date = date.today()
    
    due_date = data.get("due_date")
    if not due_date and data.get("credit_terms_days"):
        due_date = (issue_date + timedelta(days=data["credit_terms_days"])).isoformat()
    
    summary = calculate_summary(items)
    
    with get_connection() as conn:
        cur = conn.execute("""
            INSERT INTO invoices (
                doc_no, doc_type, shipment_id, job_no,
                customer_id, customer_name, issue_date, due_date,
                currency, subtotal, vat_rate, vat_amount,
                wht_rate, wht_amount, total_amount,
                paid_amount, outstanding, payment_status,
                ref_doc_no, remark, created_by,
                advance_amount, non_vat_amount,
                wht_1_amount, wht_3_amount
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            doc_no, doc_type, data.get("shipment_id"), data.get("job_no"),
            data.get("customer_id"), data.get("customer_name"),
            issue_date.isoformat() if isinstance(issue_date, date) else issue_date,
            due_date,
            data.get("currency", "THB"),
            summary["total_before_vat"], 7.0, summary["total_vat_7"],
            0.0, summary["wht_total"], summary["grand_total"],
            0, summary["grand_total"], "Unpaid",
            data.get("ref_doc_no"), data.get("remark"), data.get("created_by"),
            summary["total_advance"], 0.0,
            summary["wht_1_amount"], summary["wht_3_amount"],
        ))
        invoice_id = cur.lastrowid
        
        for idx, item in enumerate(items):
            qty = float(item.get("quantity", 1) or 1)
            unit_price = float(item.get("unit_price", 0) or 0)
            amount = item.get("amount") or (qty * unit_price)
            conn.execute("""
                INSERT INTO invoice_items
                (invoice_id, description, quantity, unit_price, amount,
                 tax_type, wht_type, sort_order)
                VALUES (?,?,?,?,?,?,?,?)
            """, (invoice_id, item.get("description"), qty, unit_price,
                  round(amount, 2),
                  item.get("tax_type", "VAT 7%"),
                  item.get("wht_type", "None"),
                  idx))
    
    return doc_no


def get_invoice_by_no(doc_no: str) -> Optional[Dict[str, Any]]:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM invoices WHERE doc_no=?",
                            (doc_no,)).fetchone()
        if not row:
            return None
        invoice = dict(row)
        items = conn.execute(
            "SELECT * FROM invoice_items WHERE invoice_id=? ORDER BY sort_order",
            (invoice["id"],)
        ).fetchall()
        invoice["items"] = [dict(i) for i in items]
        # Recompute summary on read for consistency
        invoice["summary"] = calculate_summary(invoice["items"])
        return invoice


def list_invoices(doc_type: str = None, customer_id: int = None,
                   payment_status: str = None) -> List[Dict[str, Any]]:
    sql = "SELECT * FROM invoices WHERE 1=1"
    params = []
    if doc_type:
        sql += " AND doc_type=?"; params.append(doc_type)
    if customer_id:
        sql += " AND customer_id=?"; params.append(customer_id)
    if payment_status:
        sql += " AND payment_status=?"; params.append(payment_status)
    sql += " ORDER BY issue_date DESC, id DESC"
    with get_connection() as conn:
        rows = conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]


def record_payment(doc_no: str, amount: float,
                    payment_date: str = None) -> bool:
    """Record a payment against an invoice."""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT id, total_amount, paid_amount FROM invoices WHERE doc_no=?",
            (doc_no,)
        ).fetchone()
        if not row:
            return False
        new_paid = (row["paid_amount"] or 0) + amount
        outstanding = (row["total_amount"] or 0) - new_paid
        if outstanding <= 0.01:
            status = "Paid"
        elif new_paid > 0:
            status = "Partial"
        else:
            status = "Unpaid"
        conn.execute("""
            UPDATE invoices SET paid_amount=?, outstanding=?,
                payment_status=?, payment_date=?, updated_at=CURRENT_TIMESTAMP
            WHERE id=?
        """, (new_paid, max(outstanding, 0), status,
              payment_date or date.today().isoformat(), row["id"]))
    return True


def cancel_invoice(doc_no: str) -> bool:
    with get_connection() as conn:
        conn.execute("UPDATE invoices SET payment_status='Cancelled', "
                     "updated_at=CURRENT_TIMESTAMP WHERE doc_no=?", (doc_no,))
    return True


def get_outstanding_summary(customer_id: int = None) -> Dict[str, float]:
    """Get total outstanding for a customer or all."""
    sql = ("SELECT SUM(outstanding) AS total_outstanding, "
           "SUM(total_amount) AS total_billed, "
           "SUM(paid_amount) AS total_paid "
           "FROM invoices WHERE doc_type='INV' AND payment_status<>'Cancelled'")
    params = []
    if customer_id:
        sql += " AND customer_id=?"; params.append(customer_id)
    with get_connection() as conn:
        row = conn.execute(sql, params).fetchone()
    return {
        "outstanding": row["total_outstanding"] or 0,
        "billed": row["total_billed"] or 0,
        "paid": row["total_paid"] or 0,
    }


# Backward compat wrapper for existing callers
def calculate_totals(items, vat_rate=7.0, wht_rate=0.0):
    """Legacy wrapper — use calculate_summary() for new code."""
    summary = calculate_summary(items)
    return {
        "subtotal": summary["total_before_vat"],
        "vat_amount": summary["total_vat_7"],
        "wht_amount": summary["wht_total"],
        "total_amount": summary["grand_total"],
    }
