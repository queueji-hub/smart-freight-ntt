from managers.tenant_context import get_current_tenant_id
from typing import List, Dict, Any, Optional
from database.connection import get_connection
from managers.document_numbering_service import generate_document_number, normalize_doc_no
from contracts.invoice_contract import validate_invoice_summary
from core.audit import log_action
from decimal import Decimal, ROUND_HALF_UP


# =========================================================
# TAX CONFIG (stable for SaaS)
# =========================================================

TAX_RATES = {
    "VAT 7%": Decimal("0.07"),
    "NON_VAT": Decimal("0"),
    "ADVANCE": Decimal("0")
}

WHT_RATES = {
    "NONE": Decimal("0"),
    "WHT_1": Decimal("0.01"),
    "WHT_3": Decimal("0.03")
}

_TWO = Decimal("0.01")


# =========================================================
# INVOICE CALC ENGINE (DECIMAL SAFE)
# =========================================================

def calculate_summary(items: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Calculates invoice financial summary using strict Decimal arithmetic.
    Never uses float for monetary values.
    """
    subtotal = Decimal("0")
    vat_total = Decimal("0")
    wht_total = Decimal("0")
    advance_total = Decimal("0")

    for item in items:
        amount = Decimal(str(item.get("amount", 0)))
        tax_type = item.get("tax_type", "VAT 7%")
        wht_type = item.get("wht_type", "NONE")

        subtotal += amount
        vat_total += (amount * TAX_RATES.get(tax_type, Decimal("0"))).quantize(_TWO, rounding=ROUND_HALF_UP)

        if tax_type == "ADVANCE":
            advance_total += amount

        wht_total += (amount * WHT_RATES.get(wht_type, Decimal("0"))).quantize(_TWO, rounding=ROUND_HALF_UP)

    grand_total = (subtotal + vat_total - wht_total).quantize(_TWO, rounding=ROUND_HALF_UP)

    result = {
        "total_before_vat": float(subtotal.quantize(_TWO, rounding=ROUND_HALF_UP)),
        "total_vat_7": float(vat_total.quantize(_TWO, rounding=ROUND_HALF_UP)),
        "wht_total": float(wht_total.quantize(_TWO, rounding=ROUND_HALF_UP)),
        "wht_1_amount": 0.0,
        "wht_3_amount": 0.0,
        "total_advance": float(advance_total.quantize(_TWO, rounding=ROUND_HALF_UP)),
        "grand_total": float(grand_total)
    }

    return validate_invoice_summary(result)


# =========================================================
# CREATE INVOICE (AR CORE — TENANT ISOLATED)
# =========================================================

def create_invoice(
    tenant_id: str,
    data: Dict[str, Any],
    items: List[Dict[str, Any]],
    user: Dict[str, Any]
) -> str:
    """
    Creates an invoice with line items atomically.
    tenant_id parameter is accepted for API compatibility but
    the canonical tenant is ALWAYS resolved from session context.
    """
    # SECURITY: Never trust UI-supplied tenant_id
    tenant_id = get_current_tenant_id()

    doc_no = generate_document_number("INV", data.get("issue_date"))
    summary = calculate_summary(items)

    with get_connection() as conn:
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO invoices (
                        tenant_id,
                        doc_no,
                        doc_type,
                        customer_name,
                        issue_date,
                        due_date,
                        subtotal,
                        vat_amount,
                        wht_amount,
                        total_amount,
                        outstanding,
                        status,
                        created_by
                    )
                    VALUES (
                        %s,%s,'INV',
                        %s,%s,%s,
                        %s,%s,%s,%s,
                        %s,'OPEN',%s
                    )
                    RETURNING id
                """, (
                    tenant_id,
                    doc_no,
                    data.get("customer_name"),
                    data.get("issue_date"),
                    data.get("due_date"),
                    summary["total_before_vat"],
                    summary["total_vat_7"],
                    summary["wht_total"],
                    summary["grand_total"],
                    summary["grand_total"],
                    user["id"]
                ))

                row = cur.fetchone()
                invoice_id = row["id"] if isinstance(row, dict) else row[0]

                # Line items
                for idx, item in enumerate(items):
                    cur.execute("""
                        INSERT INTO invoice_items (
                            invoice_id,
                            description,
                            quantity,
                            unit_price,
                            amount,
                            tax_type,
                            wht_type,
                            sort_order
                        )
                        VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
                    """, (
                        invoice_id,
                        item.get("description"),
                        item.get("quantity", 1),
                        item.get("unit_price", 0),
                        item.get("amount", 0),
                        item.get("tax_type", "VAT 7%"),
                        item.get("wht_type", "NONE"),
                        idx
                    ))

                conn.commit()
                log_action(user["id"], tenant_id, "invoice", doc_no, "CREATE")

        except Exception as e:
            conn.rollback()
            raise RuntimeError(f"Invoice creation failed: {str(e)}")

    return doc_no


# =========================================================
# LIST INVOICES (TENANT ISOLATED)
# =========================================================

def list_invoices(tenant_id: str = None, status: str = None) -> List[Dict[str, Any]]:
    """
    Lists invoices for the current tenant.
    tenant_id parameter accepted for API compatibility but always overridden.
    """
    tenant_id = get_current_tenant_id()

    sql = "SELECT * FROM invoices WHERE tenant_id=%s"
    params = [tenant_id]

    if status:
        sql += " AND status=%s"
        params.append(status)

    sql += " ORDER BY id DESC"

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()
            return [dict(r) for r in rows]


# =========================================================
# PAYMENT ENGINE (DECIMAL SAFE + TENANT ISOLATED)
# =========================================================

def record_payment(
    tenant_id: str = None,
    invoice_id: int = None,
    amount: float = 0,
    user: Dict[str, Any] = None
) -> bool:
    """
    Records a payment against an invoice.
    Uses Decimal for all monetary arithmetic.
    Enforces tenant isolation via get_current_tenant_id().
    """
    tenant_id = get_current_tenant_id()

    with get_connection() as conn:
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT outstanding, doc_no
                    FROM invoices
                    WHERE id=%s AND tenant_id=%s
                """, (invoice_id, tenant_id))
                row = cur.fetchone()

                if not row:
                    raise ValueError(f"Invoice ID {invoice_id} not found for current tenant.")

                current_outstanding = Decimal(str(row["outstanding"]))
                payment_amount = Decimal(str(amount))

                new_outstanding = (current_outstanding - payment_amount).quantize(_TWO, rounding=ROUND_HALF_UP)
                if new_outstanding < Decimal("0"):
                    new_outstanding = Decimal("0")

                new_status = "PAID" if new_outstanding <= Decimal("0") else "PARTIAL"

                cur.execute("""
                    UPDATE invoices
                    SET outstanding=%s,
                        status=%s,
                        updated_at=CURRENT_TIMESTAMP
                    WHERE id=%s AND tenant_id=%s
                """, (
                    float(new_outstanding),
                    new_status,
                    invoice_id,
                    tenant_id
                ))

                conn.commit()
                log_action(user["id"], tenant_id, "invoice", str(row.get("doc_no", invoice_id)), "PAYMENT")
                return True

        except ValueError:
            raise
        except Exception as e:
            conn.rollback()
            raise RuntimeError(f"Payment recording failed: {str(e)}")


# =========================================================
# OUTSTANDING SUMMARY (AR DASHBOARD — TENANT ISOLATED)
# =========================================================

def get_outstanding_summary(tenant_id: str = None) -> Dict[str, Any]:
    """
    Returns aggregate AR summary for the current tenant.
    Uses Decimal for precision.
    """
    tenant_id = get_current_tenant_id()

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    COALESCE(SUM(total_amount),0) as billed,
                    COALESCE(SUM(outstanding),0) as outstanding
                FROM invoices
                WHERE tenant_id=%s
            """, (tenant_id,))
            row = cur.fetchone()

            billed = Decimal(str(row["billed"])).quantize(_TWO, rounding=ROUND_HALF_UP)
            outstanding = Decimal(str(row["outstanding"])).quantize(_TWO, rounding=ROUND_HALF_UP)

            return {
                "billed": float(billed),
                "outstanding": float(outstanding)
            }


# =========================================================
# GET INVOICE DETAIL (TENANT ISOLATED)
# =========================================================

def get_invoice(invoice_id: int, tenant_id: str = None) -> Optional[Dict[str, Any]]:
    """
    Fetches a single invoice with its line items.
    Enforces tenant isolation.
    """
    tenant_id = get_current_tenant_id()

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT *
                FROM invoices
                WHERE id=%s AND tenant_id=%s
            """, (invoice_id, tenant_id))
            inv = cur.fetchone()

            if not inv:
                return None

            cur.execute("""
                SELECT *
                FROM invoice_items
                WHERE invoice_id=%s
                ORDER BY sort_order
            """, (invoice_id,))
            items = cur.fetchall()

            result = dict(inv)
            result["items"] = [dict(i) for i in items]
            return result