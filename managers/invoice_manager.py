from managers.tenant_context import get_current_tenant_id
"""
Invoice / Billing Financial Manager Module
PostgreSQL Production Ready (ERP Grade with Atomicity)
"""

from typing import List, Dict, Any, Optional
from database.connection import get_connection
from managers.document_numbering_service import generate_document_number, normalize_doc_no
from contracts.invoice_contract import validate_invoice_summary
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP

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

TAX_TYPES: List[str] = list(TAX_RATES.keys())
WHT_TYPES: List[str] = list(WHT_RATES.keys())


def _resolve_customer_name(cur, tenant_id: str, customer_id: Any, fallback: Optional[str] = None) -> Optional[str]:
    """Resolve the invoice customer display snapshot from canonical Customer Master."""
    if customer_id is None:
        return fallback
    cur.execute(
        "SELECT company_name FROM customers WHERE tenant_id=%s AND id=%s LIMIT 1",
        (tenant_id, customer_id),
    )
    row = cur.fetchone()
    if row:
        value = row["company_name"] if isinstance(row, dict) else row[0]
        if value:
            return str(value)
    return fallback


# =========================================================
# CORE CALCULATION ENGINE
# =========================================================
def calculate_summary(items: List[Dict[str, Any]]) -> Dict[str, Decimal]:
    """Computes precise financial summaries for line items."""
    subtotal = Decimal('0.0')
    vat_total = Decimal('0.0')
    advance = Decimal('0.0')
    wht_1 = Decimal('0.0')
    wht_3 = Decimal('0.0')

    for item in items:
        qty = Decimal(str(item.get("quantity", 1)))
        price = Decimal(str(item.get("unit_price", 0.0)))
        amount = qty * price

        tax = item.get("tax_type", "VAT 7%")
        wht = item.get("wht_type", "None")

        if tax == "Advance":
            advance += amount
        else:
            subtotal += amount
            if tax == "VAT 7%":
                vat_total += amount * Decimal('0.07')

        if wht == "WHT 1%":
            wht_1 += amount * Decimal('0.01')
        elif wht == "WHT 3%":
            wht_3 += amount * Decimal('0.03')

    wht_total = wht_1 + wht_3
    grand_total = subtotal + vat_total - wht_total

    def _r(d: Decimal) -> Decimal:
        return d.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

    return validate_invoice_summary({
        "total_before_vat": _r(subtotal),
        "total_vat_7": _r(vat_total),
        "total_advance": _r(advance),
        "wht_1_amount": _r(wht_1),
        "wht_3_amount": _r(wht_3),
        "wht_total": _r(wht_total),
        "grand_total": _r(grand_total),
    })


# =========================================================
# INVOICE TRANSACTIONAL CRUD
# =========================================================
def create_invoice(data: Dict[str, Any], items: List[Dict[str, Any]]) -> str:
    """Creates invoice header and lines atomically using PostgreSQL."""
    tenant_id = get_current_tenant_id()
    issue_date = data.get("issue_date") or data.get("doc_date") or data.get("invoice_date") or datetime.now().strftime("%Y-%m-%d")
    due_date = data.get("due_date") or (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
    doc_no = generate_document_number(data.get("doc_type", "INV"), issue_date)
    summary = calculate_summary(items)

    with get_connection() as conn:
        with conn.cursor() as cur:
            try:
                canonical_customer_name = _resolve_customer_name(
                    cur,
                    tenant_id,
                    data.get("customer_id"),
                    fallback=data.get("customer_name"),
                )

                cur.execute("""
                    INSERT INTO invoices (
                        doc_no, doc_type, customer_id, customer_name, job_no,
                        issue_date, due_date, currency, ref_doc_no, remark,
                        subtotal, vat_amount, wht_amount, total_amount,
                        outstanding, payment_status, created_by, tenant_id
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id;
                """, (
                    doc_no,
                    data.get("doc_type", "INV"),
                    data.get("customer_id"),
                    canonical_customer_name,
                    data.get("job_no"),
                    issue_date,
                    due_date,
                    data.get("currency", "THB"),
                    data.get("ref_doc_no"),
                    data.get("remark"),
                    summary["total_before_vat"],
                    summary["total_vat_7"],
                    summary["wht_total"],
                    summary["grand_total"],
                    summary["grand_total"],
                    data.get("status", "DRAFT"),
                    data.get("created_by", "System"),
                    tenant_id
                ))
                invoice_result = cur.fetchone()
                invoice_id = invoice_result[0] if isinstance(invoice_result, (tuple, list)) else invoice_result["id"]

                for idx, item in enumerate(items):
                    qty = Decimal(str(item.get("quantity", 1)))
                    price = Decimal(str(item.get("unit_price", 0)))
                    line_amount = qty * price

                    cur.execute("""
                        INSERT INTO invoice_items (
                            invoice_id, description, quantity, unit_price,
                            amount, tax_type, wht_type, sort_order, tenant_id
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s);
                    """, (
                        invoice_id,
                        item.get("description", "Line Item"),
                        qty,
                        price,
                        line_amount,
                        item.get("tax_type", "VAT 7%"),
                        item.get("wht_type", "None"),
                        idx,
                        tenant_id
                    ))

                conn.commit()
                return doc_no
            except Exception as e:
                conn.rollback()
                raise RuntimeError(f"Database transaction failed: {str(e)}")


# =========================================================
# DATA FETCHING & SYNCHRONIZATION
# =========================================================
def list_invoices() -> List[Dict[str, Any]]:
    """Fetch invoice records for the current tenant."""
    tenant_id = get_current_tenant_id()
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    doc_no, doc_type, customer_name, issue_date, due_date,
                    currency, total_amount, total_amount AS grand_total,
                    outstanding, payment_status AS status
                FROM invoices
                WHERE tenant_id = %s
                ORDER BY id DESC;
            """, (tenant_id,))
            rows = cur.fetchall()
            if not rows:
                return []
            if isinstance(rows[0], dict):
                return rows
            if hasattr(cur, "description") and cur.description:
                columns = [col[0] for col in cur.description]
                return [dict(zip(columns, row)) for row in rows]
            return []


# =========================================================
# PAYMENT ACCOUNTS RECEIVABLE ENGINE
# =========================================================
def record_payment(payload: Dict[str, Any]) -> None:
    """Process an AR payment with tenant-isolated row locking."""
    tenant_id = get_current_tenant_id()
    doc_no = payload.get("doc_no")
    amount = Decimal(str(payload.get("amount", 0.0)))
    method = payload.get("method", "Bank Transfer")
    reference = payload.get("reference", "")
    payment_date = payload.get("date")

    if not doc_no:
        raise ValueError("Missing document identifier context (doc_no).")

    with get_connection() as conn:
        with conn.cursor() as cur:
            try:
                cur.execute("""
                    SELECT id, total_amount, outstanding
                    FROM invoices
                    WHERE doc_no = %s AND tenant_id = %s
                    FOR UPDATE;
                """, (doc_no, tenant_id))
                invoice = cur.fetchone()
                if not invoice:
                    raise ValueError(f"Document invoice identity sequence '{doc_no}' not found for current tenant.")

                inv_id = invoice[0] if isinstance(invoice, (tuple, list)) else invoice["id"]
                current_outstanding = Decimal(str(invoice[2] if isinstance(invoice, (tuple, list)) else invoice["outstanding"]))
                new_outstanding = max(Decimal('0.0'), current_outstanding - amount)
                new_status = "PAID" if new_outstanding <= Decimal('0.05') else "PARTIAL"

                cur.execute("""
                    INSERT INTO invoice_payments (
                        invoice_id, doc_no, payment_amount, payment_method,
                        payment_reference, payment_date, tenant_id
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s);
                """, (inv_id, doc_no, amount, method, reference, payment_date, tenant_id))

                cur.execute("""
                    UPDATE invoices
                    SET outstanding = %s,
                        payment_status = %s
                    WHERE id = %s AND tenant_id = %s;
                """, (new_outstanding, new_status, inv_id, tenant_id))
                conn.commit()
            except Exception as e:
                conn.rollback()
                raise RuntimeError(f"Payment entry recording failed: {str(e)}")


def get_outstanding_summary() -> Dict[str, Decimal]:
    """Compile aggregate AR balances for the current tenant."""
    tenant_id = get_current_tenant_id()
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    COALESCE(SUM(total_amount), 0.0) as total_billed,
                    COALESCE(SUM(total_amount - outstanding), 0.0) as total_paid,
                    COALESCE(SUM(outstanding), 0.0) as total_outstanding
                FROM invoices
                WHERE payment_status != 'CANCELLED' AND tenant_id = %s;
            """, (tenant_id,))
            row = cur.fetchone()
            billed = Decimal(str(row[0] if isinstance(row, (tuple, list)) else row["total_billed"]))
            paid = Decimal(str(row[1] if isinstance(row, (tuple, list)) else row["total_paid"]))
            outstanding = Decimal(str(row[2] if isinstance(row, (tuple, list)) else row["total_outstanding"]))

    return {"billed": billed, "paid": paid, "outstanding": outstanding}


def get_invoice_snapshot(doc_no: str) -> tuple:
    """Retrieve an invoice snapshot (invoice dict, items list) for the given doc_no."""
    from managers.document_duplicate_service import get_invoice_snapshot as _get_invoice_snapshot
    return _get_invoice_snapshot(doc_no)

