from __future__ import annotations
"""
Invoice / Billing / AR Financial Manager Module
Progress Transport Systems (PTS) Grade Multi-Currency & Full Tax/WHT Support
"""

from typing import List, Dict, Any, Optional
from database.connection import get_connection
from managers.tenant_context import get_current_tenant_id
from managers.document_numbering_service import generate_document_number, normalize_doc_no
from contracts.invoice_contract import validate_invoice_summary
from datetime import datetime, timedelta, date
from decimal import Decimal, ROUND_HALF_UP

# =========================================================
# GLOBALS & CONSTANTS
# =========================================================
TAX_RATES: Dict[str, float] = {
    "VAT 7%": 0.07,
    "07": 0.07,
    "Non-VAT": 0.0,
    "00": 0.0,
    "Advance": 0.0,
    "Exempt": 0.0,
}

WHT_RATES: Dict[str, float] = {
    "None": 0.0,
    "0": 0.0,
    "WHT 1%": 0.01,
    "1": 0.01,
    "WHT 3%": 0.03,
    "3": 0.03,
    "WHT 5%": 0.05,
    "5": 0.05,
}

TAX_TYPES: List[str] = ["VAT 7%", "Non-VAT", "Advance", "07", "00"]
WHT_TYPES: List[str] = ["None", "WHT 1%", "WHT 3%", "WHT 5%"]


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
# CORE CALCULATION ENGINE (PTS COMPLIANT)
# =========================================================
def calculate_summary(
    items: List[Dict[str, Any]],
    total_advance_input: float = 0.0,
    less_vat_sub: float = 0.0,
    plus_wht_diff: float = 0.0,
    diff_amount: float = 0.0,
) -> Dict[str, Decimal]:
    """Computes precise PTS financial summaries for line items."""
    amount_no_vat = Decimal('0.0')
    amount_vat = Decimal('0.0')
    vat_total = Decimal('0.0')
    advance_calc = Decimal(str(total_advance_input or 0.0))
    wht_1 = Decimal('0.0')
    wht_3 = Decimal('0.0')

    for item in items:
        qty = Decimal(str(item.get("quantity") or item.get("qty") or 1))
        price = Decimal(str(item.get("unit_price") or item.get("price") or 0.0))
        exch = Decimal(str(item.get("exch_rate") or item.get("exchange_rate") or 1.0))
        if exch <= Decimal('0'):
            exch = Decimal('1.0')
        
        # Base THB line amount
        amount_thb = (qty * price * exch).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

        tax = str(item.get("tax_type") or item.get("tax") or "VAT 7%").strip()
        wht = str(item.get("wht_type") or item.get("wht") or "None").strip()

        if tax == "Advance" or "ADV" in tax.upper():
            advance_calc += amount_thb
        elif tax in ("VAT 7%", "07", "7%"):
            amount_vat += amount_thb
            vat_total += (amount_thb * Decimal('0.07')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        else:
            amount_no_vat += amount_thb

        if wht in ("WHT 1%", "1", "1%"):
            wht_1 += (amount_thb * Decimal('0.01')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        elif wht in ("WHT 3%", "3", "3%"):
            wht_3 += (amount_thb * Decimal('0.03')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        elif wht in ("WHT 5%", "5", "5%"):
            wht_3 += (amount_thb * Decimal('0.05')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

    subtotal = amount_no_vat + amount_vat
    d_less_vat = Decimal(str(less_vat_sub or 0.0)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    d_plus_wht = Decimal(str(plus_wht_diff or 0.0)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    d_diff = Decimal(str(diff_amount or 0.0)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

    vat_total = max(Decimal('0.00'), vat_total - d_less_vat)
    wht_total = wht_1 + wht_3 + d_plus_wht
    total_amount = subtotal + vat_total + d_diff
    net_payable = total_amount - wht_total + advance_calc

    def _r(d: Decimal) -> Decimal:
        return d.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


    res = {
        "amount_no_vat": _r(amount_no_vat),
        "amount_vat": _r(amount_vat),
        "total_before_vat": _r(subtotal),
        "total_vat_7": _r(vat_total),
        "total_advance": _r(advance_calc),
        "wht_1_amount": _r(wht_1),
        "wht_3_amount": _r(wht_3),
        "wht_total": _r(wht_total),
        "less_vat_sub": _r(Decimal(str(less_vat_sub or 0.0))),
        "plus_wht_diff": _r(Decimal(str(plus_wht_diff or 0.0))),
        "diff_amount": _r(Decimal(str(diff_amount or 0.0))),
        "grand_total": _r(total_amount),
        "net_payable": _r(net_payable),
    }
    return validate_invoice_summary(res)


# =========================================================
# INVOICE TRANSACTIONAL CRUD
# =========================================================
def create_invoice(data: Dict[str, Any], items: List[Dict[str, Any]]) -> str:
    """Creates invoice / receipt header and lines atomically matching PTS structure."""
    tenant_id = get_current_tenant_id()
    issue_date = data.get("issue_date") or data.get("doc_date") or data.get("receipt_date") or datetime.now().strftime("%Y-%m-%d")
    due_date = data.get("due_date") or (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
    doc_type = data.get("doc_type", "INV")
    
    doc_no = data.get("doc_no")
    if not doc_no or str(doc_no).strip() == "":
        doc_no = generate_document_number(doc_type, issue_date)

    summary = calculate_summary(
        items,
        total_advance_input=float(data.get("total_advance") or 0.0),
        less_vat_sub=float(data.get("less_vat_sub") or 0.0),
        plus_wht_diff=float(data.get("plus_wht_diff") or 0.0),
        diff_amount=float(data.get("diff_amount") or 0.0),
    )

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
                        doc_no, doc_type, customer_id, customer_name, customer_address, customer_tax_id, customer_branch,
                        job_no, master_job_no, shipment_no, service_type, feeder_vessel, vessel_voyage,
                        pol, pod, delivery_port, mbl_mawb_no, hbl_hawb_no, tax_receipt_no, csr_report_no,
                        issue_date, due_date, currency, ref_doc_no, remark,
                        total_advance, less_vat_sub, plus_wht_diff, amount_no_vat, amount_vat,
                        subtotal, vat_amount, vat_7_amount, wht_amount, wht_1_amount, wht_3_amount,
                        diff_amount, total_amount, net_payable,
                        outstanding, payment_status, created_by, tenant_id
                    )
                    VALUES (
                        %s, %s, %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s, %s,
                        %s, %s, %s,
                        %s, %s, %s, %s
                    )
                    RETURNING id;
                """, (
                    doc_no,
                    doc_type,
                    data.get("customer_id"),
                    canonical_customer_name,
                    data.get("customer_address"),
                    data.get("customer_tax_id"),
                    data.get("customer_branch", "00000"),
                    data.get("job_no"),
                    data.get("master_job_no") or data.get("job_no"),
                    data.get("shipment_no"),
                    data.get("service_type", "Seafreight Export"),
                    data.get("feeder_vessel"),
                    data.get("vessel_voyage"),
                    data.get("pol"),
                    data.get("pod"),
                    data.get("delivery_port"),
                    data.get("mbl_mawb_no"),
                    data.get("hbl_hawb_no"),
                    data.get("tax_receipt_no") or (f"TR{doc_no[2:]}" if doc_no.startswith("RC") else None),
                    data.get("csr_report_no"),
                    issue_date,
                    due_date,
                    data.get("currency", "THB"),
                    data.get("ref_doc_no"),
                    data.get("remark"),
                    summary["total_advance"],
                    summary["less_vat_sub"],
                    summary["plus_wht_diff"],
                    summary["amount_no_vat"],
                    summary["amount_vat"],
                    summary["total_before_vat"],
                    summary["total_vat_7"],
                    summary["total_vat_7"],
                    summary["wht_total"],
                    summary["wht_1_amount"],
                    summary["wht_3_amount"],
                    summary["diff_amount"],
                    summary["grand_total"],
                    summary["net_payable"],
                    summary["net_payable"],
                    data.get("status", "ACTIVE" if doc_type == "RC" else "DRAFT"),
                    data.get("created_by", "System"),
                    tenant_id
                ))
                invoice_result = cur.fetchone()
                invoice_id = invoice_result[0] if isinstance(invoice_result, (tuple, list)) else invoice_result["id"]

                # Insert line items with full multi-currency and tax rates
                for idx, item in enumerate(items):
                    qty = Decimal(str(item.get("quantity") or item.get("qty") or 1))
                    price = Decimal(str(item.get("unit_price") or item.get("price") or 0))
                    exch = Decimal(str(item.get("exch_rate") or item.get("exchange_rate") or 1.0))
                    line_amount = qty * price * exch

                    cur.execute("""
                        INSERT INTO invoice_items (
                            invoice_id, charge_id, description, pc_type,
                            quantity, price, curr, exch_rate, unit, unit_price,
                            amount, tax_type, wht_type, sort_order, tenant_id
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
                    """, (
                        invoice_id,
                        item.get("charge_code") or item.get("charge_id") or "SVC",
                        item.get("description", "Service Charge"),
                        item.get("pc_type", "PP-E"),
                        qty,
                        price,
                        item.get("curr", item.get("currency", "THB")),
                        exch,
                        item.get("unit", "M3"),
                        price,
                        line_amount,
                        item.get("tax_type", "VAT 7%"),
                        item.get("wht_type", "None"),
                        idx,
                        tenant_id
                    ))

                # Handle collection parts if provided
                payments = data.get("payments") or []
                for p in payments:
                    cur.execute("""
                        INSERT INTO invoice_payments (
                            invoice_id, doc_no, payment_amount, payment_method,
                            pay_by, chq_no, chq_date, bank_name, branch_name,
                            payment_reference, payment_date, tenant_id
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
                    """, (
                        invoice_id,
                        doc_no,
                        Decimal(str(p.get("amount", 0.0))),
                        p.get("pay_by") or p.get("method", "Bank Transfer"),
                        p.get("pay_by", "Bank Transfer"),
                        p.get("chq_no"),
                        p.get("chq_date"),
                        p.get("bank_name"),
                        p.get("branch_name"),
                        p.get("reference") or p.get("chq_no") or "",
                        p.get("date") or issue_date,
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
    """Fetch invoice and receipt records for the current tenant."""
    tenant_id = get_current_tenant_id()
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    id, doc_no, doc_type, customer_id, customer_name, customer_address,
                    customer_tax_id, customer_branch, job_no, master_job_no, shipment_no,
                    service_type, feeder_vessel, vessel_voyage, pol, pod, delivery_port,
                    mbl_mawb_no, hbl_hawb_no, tax_receipt_no, csr_report_no,
                    issue_date, due_date, currency, ref_doc_no, remark,
                    total_advance, less_vat_sub, plus_wht_diff, amount_no_vat, amount_vat,
                    subtotal, vat_amount, vat_7_amount, wht_amount, wht_1_amount, wht_3_amount,
                    diff_amount, total_amount, grand_total, net_payable,
                    outstanding, payment_status AS status
                FROM invoices
                WHERE tenant_id = %s
                ORDER BY id DESC;
            """, (tenant_id,))
            rows = cur.fetchall()
            if not rows:
                return []
            return [dict(r) for r in rows]


def get_invoice_snapshot(doc_no: str) -> tuple:
    """Retrieve an invoice snapshot (invoice dict, items list, payments list) for the given doc_no."""
    tenant_id = get_current_tenant_id()
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM invoices WHERE doc_no = %s AND tenant_id = %s LIMIT 1", (doc_no, tenant_id))
            inv_row = cur.fetchone()
            if not inv_row:
                return {}, []
            invoice = dict(inv_row)
            inv_id = invoice.get("id")

            cur.execute("SELECT * FROM invoice_items WHERE invoice_id = %s AND tenant_id = %s ORDER BY sort_order ASC, id ASC", (inv_id, tenant_id))
            item_rows = cur.fetchall() or []
            items = [dict(i) for i in item_rows]

            cur.execute("SELECT * FROM invoice_payments WHERE invoice_id = %s AND tenant_id = %s ORDER BY id ASC", (inv_id, tenant_id))
            pay_rows = cur.fetchall() or []
            invoice["payments"] = [dict(p) for p in pay_rows]

            return invoice, items


# =========================================================
# PAYMENT ACCOUNTS RECEIVABLE ENGINE
# =========================================================
def record_payment(payload: Dict[str, Any]) -> None:
    """Process an AR payment with tenant-isolated row locking."""
    tenant_id = get_current_tenant_id()
    doc_no = payload.get("doc_no")
    amount = Decimal(str(payload.get("amount", 0.0)))
    pay_by = payload.get("pay_by") or payload.get("method", "Bank Transfer")
    chq_no = payload.get("chq_no", "")
    chq_date = payload.get("chq_date")
    bank_name = payload.get("bank_name", "")
    branch_name = payload.get("branch_name", "")
    reference = payload.get("reference") or chq_no
    payment_date = payload.get("date") or date.today().isoformat()

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
                    raise ValueError(f"Document invoice '{doc_no}' not found.")

                inv_id = invoice["id"] if isinstance(invoice, dict) else invoice[0]
                current_outstanding = Decimal(str(invoice["outstanding"] if isinstance(invoice, dict) else invoice[2]))
                new_outstanding = max(Decimal('0.0'), current_outstanding - amount)
                new_status = "PAID" if new_outstanding <= Decimal('0.05') else "PARTIAL"

                cur.execute("""
                    INSERT INTO invoice_payments (
                        invoice_id, doc_no, payment_amount, payment_method, pay_by,
                        chq_no, chq_date, bank_name, branch_name,
                        payment_reference, payment_date, tenant_id
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
                """, (
                    inv_id, doc_no, amount, pay_by, pay_by,
                    chq_no, chq_date, bank_name, branch_name,
                    reference, payment_date, tenant_id
                ))

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
            billed = Decimal(str(row["total_billed"] if isinstance(row, dict) else row[0]))
            paid = Decimal(str(row["total_paid"] if isinstance(row, dict) else row[1]))
            outstanding = Decimal(str(row["total_outstanding"] if isinstance(row, dict) else row[2]))

    return {"billed": billed, "paid": paid, "outstanding": outstanding}


def cancel_invoice_document(doc_no: str, user: Optional[Dict[str, Any]] = None) -> bool:
    """Cancels an invoice/receipt/billing document and releases linked job_costs back to UNBILLED."""
    if not doc_no:
        return False
    tenant_id = get_current_tenant_id()
    with get_connection() as conn:
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT id, doc_no, payment_status FROM invoices WHERE doc_no = %s AND tenant_id = %s LIMIT 1", (doc_no, tenant_id))
                inv = cur.fetchone()
                if not inv:
                    raise ValueError(f"Document '{doc_no}' not found.")
                
                inv_id = inv["id"] if isinstance(inv, dict) or hasattr(inv, "keys") else inv[0]
                
                # 1. Update invoice status to CANCELLED
                cur.execute("""
                    UPDATE invoices
                    SET payment_status = 'CANCELLED',
                        outstanding = 0
                    WHERE id = %s AND tenant_id = %s
                """, (inv_id, tenant_id))
                
                # 2. Release linked job_costs so AR lines can be billed or edited again
                cur.execute("""
                    UPDATE job_costs
                    SET billing_status = 'UNBILLED',
                        invoice_no = NULL
                    WHERE invoice_no = %s AND tenant_id = %s
                """, (doc_no, tenant_id))
                
                conn.commit()
                return True
        except Exception as e:
            conn.rollback()
            raise RuntimeError(f"Failed to cancel document: {str(e)}")
