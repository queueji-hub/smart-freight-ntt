from managers.tenant_context import get_current_tenant_id
from datetime import datetime
from typing import List, Dict, Any, Optional
from database.connection import get_connection

AR_CATEGORIES = [
    "Ocean Freight Revenue",
    "Local Terminal Charges (AR)",
    "Customs Clearance Service",
    "Inland Trucking Revenue",
    "Warehousing",
    "Miscellaneous Revenue",
]

AP_CATEGORIES = [
    "Ocean Freight Cost",
    "Port Terminal Cost",
    "Customs Duty Paid",
    "Inland Carrier Expenses",
    "Agent Handling Fee",
    "Miscellaneous Cost",
]


def _convert_to_thb(amount: float, currency: str) -> float:
    if not currency or currency.upper() == "THB":
        return float(amount)
    try:
        from managers.fx_manager import convert
        return convert(amount, currency, "THB")
    except Exception:
        return float(amount)


def add_cost_line(data: Dict[str, Any]) -> int:
    tenant_id = get_current_tenant_id()
    qty = float(data.get("quantity") or 1)
    unit_price = float(data.get("unit_price") or 0)
    amount = float(data.get("amount") or (qty * unit_price))
    currency = data.get("currency") or "THB"
    amount_thb = _convert_to_thb(amount, currency)
    cost_status = str(data.get("cost_status") or "ESTIMATED").upper()
    billable = bool(data.get("billable_to_customer", True) in (True, 1, "1", "true", "True"))
    matched_code = data.get("matched_charge_code")
    vendor_inv = data.get("vendor_invoice_no")
    payout_stat = str(data.get("payout_status") or "UNPAID").upper()

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO job_costs (
                    shipment_id, tenant_id, cost_type, category, description, supplier,
                    quantity, unit_price, amount, currency, amount_thb, remark,
                    created_by, cost_status, billable_to_customer, matched_charge_code,
                    vendor_invoice_no, payout_status
                )
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                RETURNING id
                """,
                (
                    data["shipment_id"], tenant_id, str(data["cost_type"]).upper(),
                    data.get("category"), data.get("description"), data.get("supplier"),
                    qty, unit_price, amount, currency, amount_thb,
                    data.get("remark"), data.get("created_by"), cost_status,
                    billable, matched_code, vendor_inv, payout_stat,
                ),
            )
            row = cur.fetchone()
            conn.commit()
            return row["id"] if isinstance(row, dict) else row[0]


def update_cost_line(cost_id: int, data: Dict[str, Any]) -> bool:
    tenant_id = get_current_tenant_id()
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT amount, currency FROM job_costs WHERE id=%s AND tenant_id=%s",
                (cost_id, tenant_id),
            )
            row = cur.fetchone()
            if not row:
                return False

            current_amount = row["amount"] if isinstance(row, dict) else row[0]
            current_currency = row["currency"] if isinstance(row, dict) else row[1]
            new_amt = float(data.get("amount", current_amount))
            new_cur = data.get("currency", current_currency)
            amount_thb = _convert_to_thb(new_amt, new_cur)
            cost_status = str(data.get("cost_status", "ESTIMATED")).upper()
            billable = bool(data.get("billable_to_customer", True) in (True, 1, "1", "true", "True"))
            matched_code = data.get("matched_charge_code")
            vendor_inv = data.get("vendor_invoice_no")
            payout_stat = str(data.get("payout_status", "UNPAID")).upper()

            cur.execute(
                """
                UPDATE job_costs SET
                    category=%s, description=%s, supplier=%s, quantity=%s,
                    unit_price=%s, amount=%s, currency=%s, amount_thb=%s,
                    remark=%s, cost_status=%s, billable_to_customer=%s,
                    matched_charge_code=%s, vendor_invoice_no=%s, payout_status=%s
                WHERE id=%s AND tenant_id=%s
                """,
                (
                    data.get("category"), data.get("description"), data.get("supplier"),
                    data.get("quantity"), data.get("unit_price"), new_amt, new_cur,
                    amount_thb, data.get("remark"), cost_status, billable,
                    matched_code, vendor_inv, payout_stat, cost_id, tenant_id,
                ),
            )
            conn.commit()
            return cur.rowcount > 0


def delete_cost_line(cost_id: int) -> bool:
    tenant_id = get_current_tenant_id()
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM job_costs WHERE id=%s AND tenant_id=%s",
                (cost_id, tenant_id),
            )
            conn.commit()
            return cur.rowcount > 0


def get_cost_lines(shipment_id: int, cost_type: Optional[str] = None) -> List[Dict[str, Any]]:
    tenant_id = get_current_tenant_id()
    with get_connection() as conn:
        with conn.cursor() as cur:
            if cost_type:
                cur.execute(
                    "SELECT * FROM job_costs WHERE shipment_id=%s AND tenant_id=%s AND cost_type=%s ORDER BY id ASC",
                    (shipment_id, tenant_id, cost_type.upper()),
                )
            else:
                cur.execute(
                    "SELECT * FROM job_costs WHERE shipment_id=%s AND tenant_id=%s ORDER BY id ASC",
                    (shipment_id, tenant_id),
                )
            return [dict(r) for r in cur.fetchall()]


def get_profit_summary(shipment_id: int) -> Dict[str, Any]:
    tenant_id = get_current_tenant_id()
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT cost_type, cost_status, COALESCE(SUM(amount_thb), 0) AS total
                FROM job_costs
                WHERE shipment_id=%s AND tenant_id=%s
                GROUP BY cost_type, cost_status
                """,
                (shipment_id, tenant_id),
            )
            rows = cur.fetchall()

            ar_estimated = ar_actual = 0.0
            ap_estimated = ap_accrued = ap_actual = ap_posted = 0.0

            for row in rows:
                c_type = str(row["cost_type"] if isinstance(row, dict) else row[0]).upper()
                c_status = str(row["cost_status"] if isinstance(row, dict) else row[1]).upper()
                tot = float(row["total"] if isinstance(row, dict) else row[2])

                if c_type == "AR":
                    if c_status == "ESTIMATED":
                        ar_estimated += tot
                    else:
                        ar_actual += tot
                elif c_type == "AP":
                    if c_status == "ESTIMATED":
                        ap_estimated += tot
                    elif c_status == "ACCRUED":
                        ap_accrued += tot
                    elif c_status == "ACTUAL":
                        ap_actual += tot
                    elif c_status == "POSTED":
                        ap_posted += tot

            cur.execute(
                """
                SELECT COALESCE(SUM(ap.total * ap.exchange_rate), 0) AS total_ap_vouchers
                FROM ap_vouchers ap
                JOIN shipments s ON ap.job_no = s.job_no
                WHERE s.id=%s
                  AND ap.tenant_id=%s
                  AND ap.status IN ('POSTED','PARTIALLY_PAID','PAID')
                  AND s.tenant_id=%s
                """,
                (shipment_id, tenant_id, tenant_id),
            )
            ap_row = cur.fetchone()
            voucher_total = ap_row["total_ap_vouchers"] if isinstance(ap_row, dict) else (ap_row[0] if ap_row else 0)
            if voucher_total:
                ap_posted += float(voucher_total)

    est_net = ar_estimated - ap_estimated
    act_net = ar_actual - (ap_accrued + ap_actual + ap_posted)
    return {
        "ar_estimated": round(ar_estimated, 2),
        "ar_actual": round(ar_actual, 2),
        "ap_estimated": round(ap_estimated, 2),
        "ap_accrued": round(ap_accrued, 2),
        "ap_actual": round(ap_actual, 2),
        "ap_posted": round(ap_posted, 2),
        "estimated_net_profit": round(est_net, 2),
        "actual_net_profit": round(act_net, 2),
    }


def create_profit_sheet(shipment_id: int, prepared_by: str = "System Engine") -> Dict[str, Any]:
    tenant_id = get_current_tenant_id()
    summary = get_profit_summary(shipment_id)
    sheet_no = f"PS-{shipment_id}-{int(datetime.now().timestamp())}"

    net_profit = summary["actual_net_profit"]
    total_ar = summary["ar_actual"]
    total_ap = summary["ap_accrued"] + summary["ap_actual"] + summary["ap_posted"]
    margin = (net_profit / total_ar * 100) if total_ar > 0 else 0.0

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO profit_sheets (
                    shipment_id, tenant_id, sheet_no, total_ar, total_ap,
                    net_profit, profit_margin, prepared_by
                )
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
                RETURNING *
                """,
                (shipment_id, tenant_id, sheet_no, total_ar, total_ap, net_profit, margin, prepared_by),
            )
            row = cur.fetchone()
            conn.commit()
            return dict(row) if row else {}


def list_profit_sheets(shipment_id: int) -> List[Dict[str, Any]]:
    tenant_id = get_current_tenant_id()
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM profit_sheets WHERE shipment_id=%s AND tenant_id=%s ORDER BY id DESC",
                (shipment_id, tenant_id),
            )
            return [dict(r) for r in cur.fetchall()]


def update_signoff(sheet_id: int, role: str, signer_name: str) -> bool:
    tenant_id = get_current_tenant_id()
    col = "reviewed" if role == "review" else "approved"
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"UPDATE profit_sheets SET {col}_by=%s, {col}_at=CURRENT_TIMESTAMP WHERE id=%s AND tenant_id=%s",
                (signer_name, sheet_id, tenant_id),
            )
            conn.commit()
            return cur.rowcount > 0


# Functional domains for standard forwarding charges
CHARGE_DOMAIN_MAP = {
    # Ocean Freight
    "ocean freight cost": "ocean_freight",
    "ocean freight revenue": "ocean_freight",
    "ocean freight": "ocean_freight",
    "carrier sea freight": "ocean_freight",
    "freight revenue": "ocean_freight",
    "sea freight": "ocean_freight",
    "of": "ocean_freight",
    "oft": "ocean_freight",
    # Air Freight
    "air freight cost": "air_freight",
    "air freight revenue": "air_freight",
    "air freight": "air_freight",
    "air": "air_freight",
    "af": "air_freight",
    # Port / Terminal / THC
    "port terminal cost": "terminal",
    "local terminal charges (ar)": "terminal",
    "terminal handling charge": "terminal",
    "thc": "terminal",
    "port handling": "terminal",
    "wharfage": "terminal",
    # Customs
    "customs duty paid": "customs",
    "customs clearance service": "customs",
    "customs clearance": "customs",
    "customs duty": "customs",
    "cus": "customs",
    # Trucking
    "inland carrier expenses": "trucking",
    "inland trucking revenue": "trucking",
    "inland trucking": "trucking",
    "trucking": "trucking",
    "transportation": "trucking",
    "trk": "trucking",
    # Warehousing & Storage
    "warehousing": "warehousing",
    "storage": "warehousing",
    "demurrage": "warehousing",
    "detention": "warehousing",
    "cfs": "warehousing",
    "cfs handling": "warehousing",
    # Documentation
    "documentation": "documentation",
    "documentation fee": "documentation",
    "doc": "documentation",
    "bl fee": "documentation",
    "bill of lading fee": "documentation",
    # Handling / Agency / Misc
    "agent handling fee": "handling",
    "handling fee": "handling",
    "miscellaneous cost": "miscellaneous",
    "miscellaneous revenue": "miscellaneous",
    "insurance": "insurance",
    "ins": "insurance",
}

KEYWORD_GROUPS = [
    ("ocean_freight", ["ocean", "sea", "freight", "oft", "vessel", "liner", "shipping line"]),
    ("air_freight", ["air", "flight", "airline", "awb", "a/f"]),
    ("terminal", ["terminal", "thc", "port", "wharfage", "gate", "lift"]),
    ("trucking", ["truck", "transport", "inland", "delivery", "haulage", "trailer", "drop"]),
    ("customs", ["customs", "duty", "clearance", "tax", "entry", "permit", "form"]),
    ("documentation", ["doc", "documentation", "bl", "b/l", "waybill", "surrender", "amendment"]),
    ("warehousing", ["warehous", "storage", "demurrage", "detention", "dem", "det", "cfs"]),
    ("handling", ["handling", "service", "admin", "agent", "agency", "operation"]),
    ("insurance", ["insurance", "insur", "survey", "claim"]),
]


def _resolve_charge_domain(code: str, category: str, description: str) -> str:
    code_k = (code or "").strip().lower()
    cat_k = (category or "").strip().lower()
    desc_k = (description or "").strip().lower()

    for k in (code_k, cat_k, desc_k):
        if k and k in CHARGE_DOMAIN_MAP:
            return CHARGE_DOMAIN_MAP[k]

    combined = f"{code_k} {cat_k} {desc_k}"
    for domain, kws in KEYWORD_GROUPS:
        if any(kw in combined for kw in kws):
            return domain

    return cat_k or desc_k or "other"


def get_cost_sell_audit_matrix(shipment_id: int) -> Dict[str, Any]:
    """
    Reconciles Cost (AP) vs. Sell (AR) charges line-by-line for Operation review.
    Detects matched customer billings, unbilled/unmatched vendor costs, and pure service revenues.
    """
    tenant_id = get_current_tenant_id()
    ap_lines = get_cost_lines(shipment_id, cost_type="AP")
    ar_lines = get_cost_lines(shipment_id, cost_type="AR")

    total_cost_thb = sum(float(x.get("amount_thb") or 0) for x in ap_lines)
    total_sell_thb = sum(float(x.get("amount_thb") or 0) for x in ar_lines)
    gross_profit = total_sell_thb - total_cost_thb
    margin_pct = (gross_profit / total_sell_thb * 100) if total_sell_thb > 0 else 0.0

    # Build comparison rows with smart domain & keyword matching
    matrix_rows = []
    matched_ar_ids = set()
    unbilled_cost_count = 0
    unbilled_cost_amount = 0.0

    # Pre-calculate domain tags for all AR lines
    ar_domains = {
        ar["id"]: _resolve_charge_domain(
            ar.get("matched_charge_code", ""),
            ar.get("category", ""),
            ar.get("description", ""),
        )
        for ar in ar_lines
    }

    for ap in ap_lines:
        ap_desc = (ap.get("description") or ap.get("category") or "").strip().lower()
        ap_cat = (ap.get("category") or "").strip().lower()
        ap_code = (ap.get("matched_charge_code") or "").strip().lower()
        is_billable = ap.get("billable_to_customer", 1) in (1, True, "1", "true")
        ap_domain = _resolve_charge_domain(ap_code, ap_cat, ap_desc)

        # Score all available AR lines to find the best match
        best_ar = None
        best_score = 0

        for ar in ar_lines:
            if ar["id"] in matched_ar_ids:
                continue

            ar_desc = (ar.get("description") or ar.get("category") or "").strip().lower()
            ar_cat = (ar.get("category") or "").strip().lower()
            ar_code = (ar.get("matched_charge_code") or "").strip().lower()
            ar_domain = ar_domains.get(ar["id"], "")

            score = 0
            if ap_code and ar_code and ap_code == ar_code:
                score = 100
            elif ap_desc and ar_desc and ap_desc == ar_desc:
                score = 95
            elif ap_domain and ar_domain and ap_domain == ar_domain:
                score = 85
            elif (ap_desc and ar_desc) and (ap_desc in ar_desc or ar_desc in ap_desc):
                score = 80
            elif ap_cat and ar_cat and ap_cat == ar_cat:
                score = 75

            if score > best_score and score >= 75:
                best_score = score
                best_ar = ar

        if best_ar:
            matched_ar_ids.add(best_ar["id"])

        if not is_billable:
            status = "NON_BILLABLE"
            badge = "⚪ Non-Billable (Internal)"
        elif best_ar:
            status = "MATCHED"
            badge = "🟢 Matched & Billed"
        else:
            status = "UNBILLED_ALERT"
            badge = "🔴 Unbilled Cost Alert!"
            unbilled_cost_count += 1
            unbilled_cost_amount += float(ap.get("amount_thb") or 0)

        matrix_rows.append({
            "cost_id": ap.get("id"),
            "category": ap.get("category"),
            "description": ap.get("description"),
            "supplier": ap.get("supplier"),
            "cost_amount": float(ap.get("amount") or 0),
            "cost_currency": ap.get("currency", "THB"),
            "cost_thb": float(ap.get("amount_thb") or 0),
            "is_billable": is_billable,
            "sell_id": best_ar.get("id") if best_ar else None,
            "sell_description": best_ar.get("description") if best_ar else "—",
            "sell_amount": float(best_ar.get("amount") or 0) if best_ar else 0.0,
            "sell_currency": best_ar.get("currency", "THB") if best_ar else "THB",
            "sell_thb": float(best_ar.get("amount_thb") or 0) if best_ar else 0.0,
            "status": status,
            "badge": badge,
            "profit_thb": (float(best_ar.get("amount_thb") or 0) if best_ar else 0.0) - float(ap.get("amount_thb") or 0),
        })

    # Add standalone AR lines with no direct cost
    for ar in ar_lines:
        if ar["id"] not in matched_ar_ids:
            matrix_rows.append({
                "cost_id": None,
                "category": ar.get("category"),
                "description": ar.get("description"),
                "supplier": "—",
                "cost_amount": 0.0,
                "cost_currency": "THB",
                "cost_thb": 0.0,
                "is_billable": True,
                "sell_id": ar.get("id"),
                "sell_description": ar.get("description"),
                "sell_amount": float(ar.get("amount") or 0),
                "sell_currency": ar.get("currency", "THB"),
                "sell_thb": float(ar.get("amount_thb") or 0),
                "status": "PURE_REVENUE",
                "badge": "🔵 Service Revenue",
                "profit_thb": float(ar.get("amount_thb") or 0),
            })

    return {
        "shipment_id": shipment_id,
        "total_cost_thb": round(total_cost_thb, 2),
        "total_sell_thb": round(total_sell_thb, 2),
        "gross_profit": round(gross_profit, 2),
        "margin_pct": round(margin_pct, 2),
        "unbilled_cost_count": unbilled_cost_count,
        "unbilled_cost_amount": round(unbilled_cost_amount, 2),
        "matrix_rows": matrix_rows,
    }


def lock_job_financials(shipment_id: int, user: Dict[str, Any]) -> bool:
    """Lock Job Cost & Sell figures and handover to Accounting."""
    tenant_id = get_current_tenant_id()
    uname = user.get("username", "operation")
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE shipments
                SET financial_locked = TRUE,
                    handover_to_accounting_at = CURRENT_TIMESTAMP,
                    handover_by = %s
                WHERE id = %s
                """,
                (uname, shipment_id),
            )
            conn.commit()
            return cur.rowcount > 0


def unlock_job_financials(shipment_id: int, user: Dict[str, Any]) -> bool:
    """Unlock Job Cost & Sell figures for revision."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE shipments
                SET financial_locked = FALSE
                WHERE id = %s
                """,
                (shipment_id,),
            )
            conn.commit()
            return cur.rowcount > 0

