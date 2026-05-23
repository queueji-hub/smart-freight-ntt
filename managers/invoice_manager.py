from typing import List, Dict, Any, Optional
from database.connection import get_connection
from managers.doc_number import generate_doc_number
from contracts.core_contract import enforce, INVOICE_SUMMARY_SCHEMA

# =========================================================
# CONFIG
# =========================================================

TAX_TYPES = ["VAT 7%", "Non-VAT", "Advance"]
WHT_TYPES = ["None", "WHT 1%", "WHT 3%"]

# ใช้ dynamic แทน hardcode
VAT_RATES = {
    "VAT 7%": 0.07,
    "Non-VAT": 0.0,
    "Advance": 0.0
}

# =========================================================
# CORE CALCULATION
# =========================================================

def calculate_summary(items: List[Dict[str, Any]]) -> Dict[str, float]:
    total_before_vat = 0.0
    total_vat = 0.0
    total_advance = 0.0

    wht_1_amount = 0.0
    wht_3_amount = 0.0

    for item in items:
        amount = float(item.get("amount", 0))

        tax_type = item.get("tax_type", "VAT 7%")
        wht_type = item.get("wht_type", "None")

        total_before_vat += amount

        # VAT dynamic
        vat_rate = VAT_RATES.get(tax_type, 0.0)
        total_vat += amount * vat_rate

        # Advance
        if tax_type == "Advance":
            total_advance += amount

        # WHT
        if wht_type == "WHT 1%":
            wht_1_amount += amount * 0.01

        elif wht_type == "WHT 3%":
            wht_3_amount += amount * 0.03

    wht_total = wht_1_amount + wht_3_amount

    grand_total = total_before_vat + total_vat - wht_total

    return {
    from contracts.invoice_contract import validate_invoice_summary

    }
    
result = {
    "billed": total_before_vat,
    "subtotal": total_before_vat,
    "vat": total_vat,
    "wht": wht_total,
    "grand_total": grand_total,
    "outstanding": grand_total
}

return enforce(INVOICE_SUMMARY_SCHEMA, result, "invoice_summary")


# =========================================================
# INVOICE CREATE
# =========================================================

def create_invoice(data: Dict[str, Any], items: List[Dict[str, Any]]) -> str:
    doc_type = data.get("doc_type", "INV")
    doc_no = generate_doc_number(doc_type, data.get("issue_date"))

    summary = calculate_summary(items)

    with get_connection() as conn:
        cur = conn.execute("""
            INSERT INTO invoices (
                doc_no, doc_type, shipment_id, job_no,
                customer_id, customer_name,
                issue_date, due_date,
                currency,
                subtotal, vat_rate, vat_amount,
                wht_amount, total_amount, outstanding,
                payment_status,
                ref_doc_no, remark, created_by,
                advance_amount,
                wht_1_amount, wht_3_amount
            )
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            RETURNING id
        """, (
            doc_no,
            doc_type,
            data.get("shipment_id"),
            data.get("job_no"),
            data.get("customer_id"),
            data.get("customer_name"),
            data.get("issue_date"),
            data.get("due_date"),
            data.get("currency", "THB"),

            summary["total_before_vat"],
            7.0,  # keep column legacy (optional)
            summary["total_vat"],

            summary["wht_total"],
            summary["grand_total"],
            summary["grand_total"],

            "Unpaid",
            data.get("ref_doc_no"),
            data.get("remark"),
            data.get("created_by"),

            summary["total_advance"],
            summary["wht_1_amount"],
            summary["wht_3_amount"]
        ))

        invoice_id = cur.fetchone()["id"]

        # items
        for idx, item in enumerate(items):
            conn.execute("""
                INSERT INTO invoice_items (
                    invoice_id, description,
                    quantity, unit_price, amount,
                    tax_type, wht_type, sort_order
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

# =========================================================
# READ FUNCTIONS
# =========================================================

def list_invoices() -> List[Dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT *
            FROM invoices
            ORDER BY created_at DESC
        """).fetchall()

        return [dict(r) for r in rows]


def get_invoice_by_no(doc_no: str) -> Optional[Dict[str, Any]]:
    with get_connection() as conn:
        invoice = conn.execute(
            "SELECT * FROM invoices WHERE doc_no=%s",
            (doc_no,)
        ).fetchone()

        if not invoice:
            return None

        items = conn.execute(
            "SELECT * FROM invoice_items WHERE invoice_id=%s ORDER BY sort_order",
            (invoice["id"],)
        ).fetchall()

        invoice = dict(invoice)
        invoice["items"] = [dict(i) for i in items]
        invoice["summary"] = calculate_summary(invoice["items"])

        return invoice

# =========================================================
# DASHBOARD SUMMARY
# =========================================================

def get_outstanding_summary():
    return {
        "total_outstanding": 0,
        "overdue": 0,
        "due_today": 0,
        "upcoming": 0
    }

def record_payment(invoice_id: int, amount: float, method: str, paid_date=None):
    with get_connection() as conn:
        conn.execute("""
            INSERT INTO invoice_payments (
                invoice_id,
                amount,
                method,
                paid_date
            )
            VALUES (%s, %s, %s, COALESCE(%s, CURRENT_DATE))
        """, (
            invoice_id,
            amount,
            method,
            paid_date
        ))

        conn.execute("""
            UPDATE invoices
            SET payment_status = 'Paid',
                outstanding = outstanding - %s
            WHERE id = %s
        """, (amount, invoice_id))

        conn.commit()