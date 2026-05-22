"""Invoice / Billing Note / CN / DN / SOA management."""
from datetime import date, datetime, timedelta
from typing import List, Dict, Any, Optional
from database.connection import get_connection
from managers.doc_number import generate_doc_number


def calculate_totals(items: List[Dict[str, Any]],
                      vat_rate: float = 7.0,
                      wht_rate: float = 0.0) -> Dict[str, float]:
    """Calculate subtotal, VAT, WHT, total amounts."""
    subtotal = sum(float(i.get("amount", 0) or 0) for i in items)
    vat_amount = subtotal * (vat_rate / 100)
    after_vat = subtotal + vat_amount
    wht_amount = subtotal * (wht_rate / 100)  # WHT calculated on subtotal (Thai standard)
    total = after_vat - wht_amount
    return {
        "subtotal": round(subtotal, 2),
        "vat_amount": round(vat_amount, 2),
        "wht_amount": round(wht_amount, 2),
        "total_amount": round(total, 2),
    }


def create_invoice(data: Dict[str, Any], items: List[Dict[str, Any]]) -> str:
    """Create new invoice/CN/DN/BN/SOA. Returns the doc_no."""
    doc_type = data.get("doc_type", "INV")
    doc_no = generate_doc_number(doc_type, data.get("issue_date"))
    
    # Auto-fill due_date from credit terms if not provided
    issue_date = data.get("issue_date")
    if isinstance(issue_date, str):
        issue_date = datetime.strptime(issue_date, "%Y-%m-%d").date()
    elif issue_date is None:
        issue_date = date.today()
    
    due_date = data.get("due_date")
    if not due_date and data.get("credit_terms_days"):
        due_date = (issue_date + timedelta(days=data["credit_terms_days"])).isoformat()
    
    # Calculate totals
    totals = calculate_totals(
        items, vat_rate=data.get("vat_rate", 7),
        wht_rate=data.get("wht_rate", 0)
    )
    
    with get_connection() as conn:
        cur = conn.execute("""
            INSERT INTO invoices (
                doc_no, doc_type, shipment_id, job_no,
                customer_id, customer_name, issue_date, due_date,
                currency, subtotal, vat_rate, vat_amount,
                wht_rate, wht_amount, total_amount,
                paid_amount, outstanding, payment_status,
                ref_doc_no, remark, created_by
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            doc_no, doc_type, data.get("shipment_id"), data.get("job_no"),
            data.get("customer_id"), data.get("customer_name"),
            issue_date.isoformat() if isinstance(issue_date, date) else issue_date,
            due_date,
            data.get("currency", "THB"),
            totals["subtotal"], data.get("vat_rate", 7), totals["vat_amount"],
            data.get("wht_rate", 0), totals["wht_amount"], totals["total_amount"],
            0, totals["total_amount"], "Unpaid",
            data.get("ref_doc_no"), data.get("remark"), data.get("created_by"),
        ))
        invoice_id = cur.lastrowid
        
        for idx, item in enumerate(items):
            qty = float(item.get("quantity", 1) or 1)
            unit_price = float(item.get("unit_price", 0) or 0)
            amount = item.get("amount") or (qty * unit_price)
            conn.execute("""
                INSERT INTO invoice_items
                (invoice_id, description, quantity, unit_price, amount, sort_order)
                VALUES (?,?,?,?,?,?)
            """, (invoice_id, item.get("description"), qty, unit_price,
                  round(amount, 2), idx))
    
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
