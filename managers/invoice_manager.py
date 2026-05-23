from typing import List, Dict, Any, Optional
from database.connection import get_connection
from managers.doc_number import generate_doc_number
from contracts.invoice_contract import validate_invoice_summary

TAX_RATES = {
    "VAT 7%": 0.07,
    "Non-VAT": 0.0,
    "Advance": 0.0
}

WHT_RATES = {
    "None": 0.0,
    "WHT 1%": 0.01,
    "WHT 3%": 0.03
}

# =========================
# CORE CALCULATION
# =========================

def calculate_summary(items: List[Dict[str, Any]]) -> Dict[str, float]:
    subtotal = 0
    vat_total = 0
    advance = 0
    wht_1 = 0
    wht_3 = 0

    for i in items:
        amount = float(i.get("amount", 0))
        tax_type = i.get("tax_type", "VAT 7%")
        wht_type = i.get("wht_type", "None")

        subtotal += amount

        vat_total += amount * TAX_RATES.get(tax_type, 0)

        if tax_type == "Advance":
            advance += amount

        wht = amount * WHT_RATES.get(wht_type, 0)

        if wht_type == "WHT 1%":
            wht_1 += wht
        elif wht_type == "WHT 3%":
            wht_3 += wht

    wht_total = wht_1 + wht_3

    grand_total = subtotal + vat_total - wht_total

    return validate_invoice_summary({
        "total_before_vat": subtotal,
        "total_vat_7": vat_total,
        "total_advance": advance,
        "wht_1_amount": wht_1,
        "wht_3_amount": wht_3,
        "wht_total": wht_total,
        "grand_total": grand_total,
    })

# =========================
# INVOICE CRUD
# =========================

def create_invoice(data: Dict[str, Any], items: List[Dict[str, Any]]) -> str:
    doc_no = generate_doc_number("INV", data.get("issue_date"))
    summary = calculate_summary(items)

    with get_connection() as conn:
        cur = conn.execute("""
            INSERT INTO invoices (
                doc_no, doc_type, customer_name,
                issue_date, due_date,
                subtotal, vat_amount,
                wht_amount, total_amount,
                outstanding, payment_status
            )
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            RETURNING id
        """, (
            doc_no, "INV",
            data.get("customer_name"),
            data.get("issue_date"),
            data.get("due_date"),
            summary["total_before_vat"],
            summary["total_vat_7"],
            summary["wht_total"],
            summary["grand_total"],
            summary["grand_total"],
            "Unpaid"
        ))

        invoice_id = cur.fetchone()["id"]

        for idx, item in enumerate(items):
            conn.execute("""
                INSERT INTO invoice_items (
                    invoice_id, description,
                    quantity, unit_price,
                    amount, tax_type, wht_type, sort_order
                )
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
            """, (
                invoice_id,
                item.get("description"),
                item.get("quantity", 1),
                item.get("unit_price", 0),
                item.get("amount", 0),
                item.get("tax_type", "VAT 7%"),
                item.get("wht_type", "None"),
                idx
            ))

        conn.commit()

    return doc_no

# =========================
# REQUIRED STABLE FUNCTIONS
# =========================

def list_invoices():
    with get_connection() as conn:
        return [dict(r) for r in conn.execute("SELECT * FROM invoices ORDER BY id DESC").fetchall()]

def record_payment(invoice_id: int, amount: float):
    with get_connection() as conn:
        conn.execute("""
            UPDATE invoices
            SET outstanding = outstanding - %s,
                payment_status = CASE
                    WHEN outstanding - %s <= 0 THEN 'Paid'
                    ELSE 'Partial'
                END
            WHERE id = %s
        """, (amount, amount, invoice_id))
        conn.commit()

def get_outstanding_summary():
    with get_connection() as conn:
        row = conn.execute("""
            SELECT
                COALESCE(SUM(outstanding),0) as total_outstanding
            FROM invoices
        """).fetchone()

    return {
        "billed": 0,
        "subtotal": 0,
        "vat": 0,
        "wht": 0,
        "grand_total": 0,
        "outstanding": float(row["total_outstanding"])
    }