"""
Invoice / Billing Financial Manager Module
PostgreSQL Production Ready (ERP Grade with Atomicity)
"""

from typing import List, Dict, Any, Optional
from database.connection import get_connection
from managers.doc_number import generate_doc_number
from contracts.invoice_contract import validate_invoice_summary

# =========================================================
# GLOBALS & CONSTANTS
# =========================================================
TAX_RATES: Dict[str, float] = {
    "VAT 7%": 0.07,
    "Non-VAT": 0.0,
    "Advance": 0.0
}

WHT_RATES: Dict[str, float] = {
    "None": 0.0,
    "WHT 1%": 0.01,
    "WHT 3%": 0.03
}

# Exported lists for UI selections
TAX_TYPES: List[str] = list(TAX_RATES.keys())
WHT_TYPES: List[str] = list(WHT_RATES.keys())

# =========================================================
# CORE CALCULATION ENGINE
# =========================================================
def calculate_summary(items: List[Dict[str, Any]]) -> Dict[str, float]:
    """
    Computes precise financial summaries for lines items.
    Handles calculations carefully avoiding floating-point precision issues.
    """
    subtotal: float = 0.0
    vat_total: float = 0.0
    advance: float = 0.0
    wht_1: float = 0.0
    wht_3: float = 0.0

    for item in items:
        # Calculate line item amount if not explicitly passed
        qty = float(item.get("quantity", 1))
        unit_price = float(item.get("unit_price", 0))
        amount = float(item.get("amount", qty * unit_price))
        
        tax_type = item.get("tax_type", "VAT 7%")
        wht_type = item.get("wht_type", "None")

        subtotal += amount
        vat_total += amount * TAX_RATES.get(tax_type, 0.0)

        if tax_type == "Advance":
            advance += amount

        wht_amount = amount * WHT_RATES.get(wht_type, 0.0)
        if wht_type == "WHT 1%":
            wht_1 += wht_amount
        elif wht_type == "WHT 3%":
            wht_3 += wht_amount

    wht_total = wht_1 + wht_3
    grand_total = subtotal + vat_total - wht_total

    # Contract verification guardrail
    return validate_invoice_summary({
        "total_before_vat": round(subtotal, 2),
        "total_vat_7": round(vat_total, 2),
        "total_advance": round(advance, 2),
        "wht_1_amount": round(wht_1, 2),
        "wht_3_amount": round(wht_3, 2),
        "wht_total": round(wht_total, 2),
        "grand_total": round(grand_total, 2),
    })

# =========================================================
# INVOICE TRANSACTIONAL CRUD
# =========================================================
def create_invoice(data: Dict[str, Any], items: List[Dict[str, Any]]) -> str:
    """
    Creates an invoice along with its line items atomically using PostgreSQL transaction block.
    """
    doc_no = generate_doc_number(data.get("doc_type", "INV"), data.get("issue_date"))
    summary = calculate_summary(items)

    with get_connection() as conn:
        # PostgreSQL explicit cursor context management
        with conn.cursor() as cur:
            try:
                # 1. Insert Master Document Header
                cur.execute("""
                    INSERT INTO invoices (
                        doc_no, doc_type, customer_id, customer_name, job_no,
                        issue_date, due_date, currency, ref_doc_no, remark,
                        subtotal, vat_amount, wht_amount, total_amount,
                        outstanding, payment_status, created_by
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id;
                """, (
                    doc_no,
                    data.get("doc_type", "INV"),
                    data.get("customer_id"),
                    data.get("customer_name"),
                    data.get("job_no"),
                    data.get("issue_date"),
                    data.get("due_date"),
                    data.get("currency", "THB"),
                    data.get("ref_doc_no"),
                    data.get("remark"),
                    summary["total_before_vat"],
                    summary["total_vat_7"],
                    summary["wht_total"],
                    summary["grand_total"],
                    summary["grand_total"],  # Initially outstanding equals grand total
                    data.get("status", "DRAFT"),
                    data.get("created_by", "System")
                ))
                
                # Fetch generated invoice ID safely across standard psycopg drivers
                invoice_result = cur.fetchone()
                invoice_id = invoice_result[0] if isinstance(invoice_result, (tuple, list)) else invoice_result["id"]

                # 2. Insert Document Line Items
                for idx, item in enumerate(items):
                    qty = float(item.get("quantity", 1))
                    price = float(item.get("unit_price", 0))
                    line_amount = qty * price

                    cur.execute("""
                        INSERT INTO invoice_items (
                            invoice_id, description, quantity, unit_price,
                            amount, tax_type, wht_type, sort_order
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s);
                    """, (
                        invoice_id,
                        item.get("description", "Line Item"),
                        qty,
                        price,
                        line_amount,
                        item.get("tax_type", "VAT 7%"),
                        item.get("wht_type", "None"),
                        idx
                    ))

                # Commit transaction when all inserts succeed
                conn.commit()
                return doc_no

            except Exception as e:
                conn.rollback()
                raise RuntimeError(f"Database transaction failed: {str(e)}")

# =========================================================
# DATA FETCHING & SYNCHRONIZATION
# =========================================================
def list_invoices() -> List[Dict[str, Any]]:
    """
    Fetches historical invoice logs and structures them as dictionaries for UI DataFrames.
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT 
                    doc_no, doc_type, customer_name, issue_date, due_date, 
                    currency, total_amount, total_amount AS grand_total, 
                    outstanding, payment_status AS status
                FROM invoices 
                ORDER BY id DESC;
            """)
            
            # Dynamic dictionary mapping mapping column names to values
            if hasattr(cur, "description") and cur.description:
                columns = [col[0] for col in cur.description]
                return [dict(zip(columns, row)) for row in cur.fetchall()]
            return []

# =========================================================
# PAYMENT ACCOUNTS RECEIVABLE ENGINE
# =========================================================
def record_payment(payload: Dict[str, Any]) -> None:
    """
    Processes incoming invoices payments and modifies outstanding amounts.
    Accepts full operational tracking payload matching the ERP front-end interface.
    """
    doc_no = payload.get("doc_no")
    amount = float(payload.get("amount", 0.0))
    method = payload.get("method", "Bank Transfer")
    reference = payload.get("reference", "")
    payment_date = payload.get("date")

    if not doc_no:
        raise ValueError("Missing document identifier context (doc_no).")

    with get_connection() as conn:
        with conn.cursor() as cur:
            try:
                # 1. Fetch current balance details safely inside isolated transaction row lock
                cur.execute("""
                    SELECT id, total_amount, outstanding 
                    FROM invoices 
                    WHERE doc_no = %s 
                    FOR UPDATE;
                """, (doc_no,))
                
                invoice = cur.fetchone()
                if not invoice:
                    raise ValueError(f"Document invoice identity sequence '{doc_no}' not found.")
                
                # Dynamic index handling depending on cursor row factory
                inv_id = invoice[0] if isinstance(invoice, (tuple, list)) else invoice["id"]
                current_outstanding = float(invoice[2] if isinstance(invoice, (tuple, list)) else invoice["outstanding"])

                # Calculate modern AR constraints
                new_outstanding = max(0.0, current_outstanding - amount)
                new_status = "PAID" if new_outstanding <= 0.05 else "PARTIAL"

                # 2. Add payment audit trail log history (ERP Auditing Standard)
                cur.execute("""
                    INSERT INTO invoice_payments (
                        invoice_id, doc_no, payment_amount, payment_method, 
                        payment_reference, payment_date
                    )
                    VALUES (%s, %s, %s, %s, %s, %s);
                """, (inv_id, doc_no, amount, method, reference, payment_date))

                # 3. Apply state back mutation onto the invoice master record
                cur.execute("""
                    UPDATE invoices
                    SET outstanding = %s,
                        payment_status = %s
                    WHERE id = %s;
                """, (new_outstanding, new_status, inv_id))

                conn.commit()

            except Exception as e:
                conn.rollback()
                raise RuntimeError(f"Payment entry recording failed: {str(e)}")

def get_outstanding_summary() -> Dict[str, float]:
    """
    Compiles full aggregate corporate balance operations statistics.
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    COALESCE(SUM(total_amount), 0.0) as total_billed,
                    COALESCE(SUM(total_amount - outstanding), 0.0) as total_paid,
                    COALESCE(SUM(outstanding), 0.0) as total_outstanding
                FROM invoices
                WHERE payment_status != 'CANCELLED';
            """)
            row = cur.fetchone()
            
            # Map elements regardless of cursor implementation type
            billed = float(row[0] if isinstance(row, (tuple, list)) else row["total_billed"])
            paid = float(row[1] if isinstance(row, (tuple, list)) else row["total_paid"])
            outstanding = float(row[2] if isinstance(row, (tuple, list)) else row["total_outstanding"])

    return {
        "billed": billed,
        "paid": paid,
        "outstanding": outstanding
    }