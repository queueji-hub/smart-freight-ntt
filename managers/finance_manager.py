from typing import List, Dict, Any, Optional
from database.connection import get_connection
from managers.doc_number import generate_doc_number
from contracts.invoice_contract import validate_invoice_summary
from core.audit import log_action


# =========================================================
# TAX CONFIG (stable for SaaS)
# =========================================================

TAX_RATES = {
    "VAT 7%": 0.07,
    "NON_VAT": 0.0,
    "ADVANCE": 0.0
}

WHT_RATES = {
    "NONE": 0.0,
    "WHT_1": 0.01,
    "WHT_3": 0.03
}


# =========================================================
# INVOICE CALC ENGINE (IMMUTABLE SAFE)
# =========================================================

def calculate_summary(items: List[Dict[str, Any]]) -> Dict[str, float]:

    subtotal = 0.0
    vat_total = 0.0
    wht_total = 0.0
    advance_total = 0.0

    for item in items:

        amount = float(item.get("amount", 0))
        tax_type = item.get("tax_type", "VAT 7%")
        wht_type = item.get("wht_type", "NONE")

        subtotal += amount

        vat_total += amount * TAX_RATES.get(tax_type, 0)

        if tax_type == "ADVANCE":
            advance_total += amount

        wht_total += amount * WHT_RATES.get(wht_type, 0)

    grand_total = subtotal + vat_total - wht_total

    result = {
        "subtotal": subtotal,
        "vat_total": vat_total,
        "wht_total": wht_total,
        "advance_total": advance_total,
        "grand_total": grand_total
    }

    return validate_invoice_summary(result)


# =========================================================
# CREATE INVOICE (AR CORE)
# =========================================================

def create_invoice(
    tenant_id: str,
    data: Dict[str, Any],
    items: List[Dict[str, Any]],
    user: Dict[str, Any]
) -> str:

    doc_no = generate_doc_number("INV", data.get("issue_date"), tenant_id)
    summary = calculate_summary(items)

    with get_connection() as conn:

        cur = conn.execute("""
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
            summary["subtotal"],
            summary["vat_total"],
            summary["wht_total"],
            summary["grand_total"],
            summary["grand_total"],
            user["id"]
        ))

        invoice_id = cur.fetchone()["id"]

        # items
        for idx, item in enumerate(items):

            conn.execute("""
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

    return doc_no


# =========================================================
# LIST INVOICES (SaaS FILTERED)
# =========================================================

def list_invoices(tenant_id: str, status: str = None) -> List[Dict[str, Any]]:

    sql = "SELECT * FROM invoices WHERE tenant_id=%s"
    params = [tenant_id]

    if status:
        sql += " AND status=%s"
        params.append(status)

    sql += " ORDER BY id DESC"

    with get_connection() as conn:
        rows = conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]


# =========================================================
# PAYMENT ENGINE (SAFE AR UPDATE)
# =========================================================

def record_payment(
    tenant_id: str,
    invoice_id: int,
    amount: float,
    user: Dict[str, Any]
) -> bool:

    with get_connection() as conn:

        row = conn.execute("""
            SELECT outstanding
            FROM invoices
            WHERE id=%s AND tenant_id=%s
        """, (invoice_id, tenant_id)).fetchone()

        if not row:
            return False

        new_outstanding = float(row["outstanding"]) - float(amount)

        new_status = "PAID" if new_outstanding <= 0 else "PARTIAL"

        conn.execute("""
            UPDATE invoices
            SET outstanding=%s,
                status=%s,
                updated_at=CURRENT_TIMESTAMP
            WHERE id=%s AND tenant_id=%s
        """, (
            max(new_outstanding, 0),
            new_status,
            invoice_id,
            tenant_id
        ))

        conn.commit()

        log_action(user["id"], tenant_id, "invoice", str(invoice_id), "PAYMENT")

        return True


# =========================================================
# OUTSTANDING SUMMARY (AR DASHBOARD)
# =========================================================

def get_outstanding_summary(tenant_id: str) -> Dict[str, Any]:

    with get_connection() as conn:

        row = conn.execute("""
            SELECT
                COALESCE(SUM(total_amount),0) as billed,
                COALESCE(SUM(outstanding),0) as outstanding
            FROM invoices
            WHERE tenant_id=%s
        """, (tenant_id,)).fetchone()

        return {
            "billed": float(row["billed"]),
            "outstanding": float(row["outstanding"])
        }


# =========================================================
# GET INVOICE DETAIL
# =========================================================

def get_invoice(invoice_id: int, tenant_id: str) -> Optional[Dict[str, Any]]:

    with get_connection() as conn:

        inv = conn.execute("""
            SELECT *
            FROM invoices
            WHERE id=%s AND tenant_id=%s
        """, (invoice_id, tenant_id)).fetchone()

        if not inv:
            return None

        items = conn.execute("""
            SELECT *
            FROM invoice_items
            WHERE invoice_id=%s
            ORDER BY sort_order
        """, (invoice_id,)).fetchall()

        result = dict(inv)
        result["items"] = [dict(i) for i in items]

        return result