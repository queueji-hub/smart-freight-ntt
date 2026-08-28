"""Job Profitability, Unified AP/AR Ledger, Batch Billing & Disbursement Manager.

Provides ERP-grade Single Source of Truth for:
- Unified Side-by-Side AP/AR Cost & Revenue Reconciliation
- Accrual P&L calculation (Advance / Service / VAT / WHT / Margin)
- Pull AP to AR with customizable markup and selling descriptions
- Batch AP Payment Voucher & Advance Request generation
- Batch AR Customer Invoice generation
- Full Document Audit Trail & Line Traceability
"""
from __future__ import annotations

from datetime import datetime, date
from typing import List, Dict, Any, Optional, Tuple

from database.connection import get_connection
from managers.tenant_context import get_current_tenant_id
from managers.document_numbering_service import generate_document_number

AR_CATEGORIES = [
    "Ocean Freight Revenue",
    "Air Freight Revenue",
    "Local Terminal Charges (AR)",
    "Customs Clearance Service",
    "Inland Trucking Revenue",
    "Warehousing & Storage",
    "Documentation & D/O Fee",
    "Port & Gate Charges",
    "Advance Disbursement (สำรองจ่าย)",
    "Miscellaneous Revenue",
]

AP_CATEGORIES = [
    "Ocean Freight Cost (สายเรือ)",
    "Air Freight Cost (สายการบิน)",
    "Port Terminal Cost (THC / ท่าเรือ)",
    "Customs Duty & Clearance (กรมศุลกากร)",
    "Inland Carrier & Trucking (รถบรรทุก)",
    "Warehouse / Storage / CFS Cost",
    "D/O & Line Documentation Fee",
    "Advance Paid on Behalf (สำรองจ่าย)",
    "Agent Handling Fee",
    "Miscellaneous Cost",
]

TAX_TYPES = ["VAT 7%", "Non-VAT", "Advance"]
WHT_TYPES = ["None", "WHT 1%", "WHT 3%", "WHT 0.75%", "WHT 5%"]

def _resolve_charge_domain(charge_code: str = "", category: str = "", description: str = "") -> str:
    """Resolve standard charge domain (ocean_freight, air_freight, terminal, customs, trucking, other)."""
    text = f"{charge_code} {category} {description}".lower()
    if any(k in text for k in ["custom", "duty", "clearance", "formalit", "import duty"]):
        return "customs"
    if any(k in text for k in ["ocean", "sea", "of", "freight cost", "freight revenue"]):
        return "ocean_freight"
    if any(k in text for k in ["air", "flight", "af"]):
        return "air_freight"
    if any(k in text for k in ["terminal", "thc", "port"]):
        return "terminal"
    if any(k in text for k in ["truck", "inland", "trailer", "carrier", "haulage", "delivery"]):
        return "trucking"
    return "other"


def _convert_to_thb(amount: float, currency: str, ex_rate: Optional[float] = None) -> float:
    if not currency or currency.upper() == "THB":
        return float(amount)
    if ex_rate and ex_rate > 0:
        return float(amount) * float(ex_rate)
    try:
        from managers.fx_manager import convert
        return convert(amount, currency, "THB")
    except Exception:
        return float(amount)


from decimal import Decimal, ROUND_HALF_UP


def _dec(val: Any) -> Decimal:
    try:
        return Decimal(str(val or 0))
    except Exception:
        return Decimal('0')


def _round_cur(d: Decimal) -> float:
    return float(d.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))


def compute_line_tax_and_net(
    qty: float,
    unit_price: float,
    tax_type: str = "VAT 7%",
    wht_type: str = "None",
    currency: str = "THB",
    exchange_rate: float = 1.0,
) -> Dict[str, float]:
    """Computes exact amount, VAT, WHT, net payable/receivable with Thai Revenue Dept ROUND_HALF_UP standard."""
    d_qty = _dec(qty)
    d_price = _dec(unit_price)
    d_amount = (d_qty * d_price).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

    d_ex = _dec(exchange_rate if str(currency).upper() != "THB" else 1.0)
    if d_ex <= 0:
        d_ex = Decimal('1.0')

    tax_t = str(tax_type or "VAT 7%").strip()
    wht_t = str(wht_type or "None").strip()

    # VAT computation (7% or 0%)
    if "7%" in tax_t or tax_t in ("VAT 7%", "07", "7%"):
        d_vat = (d_amount * Decimal('0.07')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    else:
        d_vat = Decimal('0.00')

    # WHT computation (Advance & Non-taxable exempt from WHT)
    if tax_t.lower() == "advance" or "ADV" in tax_t.upper():
        d_wht = Decimal('0.00')
    elif "1%" in wht_t or wht_t in ("1", "1%"):
        d_wht = (d_amount * Decimal('0.01')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    elif "3%" in wht_t or wht_t in ("3", "3%"):
        d_wht = (d_amount * Decimal('0.03')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    elif "0.75%" in wht_t:
        d_wht = (d_amount * Decimal('0.0075')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    elif "5%" in wht_t or wht_t in ("5", "5%"):
        d_wht = (d_amount * Decimal('0.05')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    else:
        d_wht = Decimal('0.00')

    # Strict mathematical identity: Net = Amount + VAT - WHT (zero 0.01 drift)
    d_net = d_amount + d_vat - d_wht
    d_amount_thb = (d_amount * d_ex).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    d_net_thb = (d_net * d_ex).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

    return {
        "amount": _round_cur(d_amount),
        "amount_thb": _round_cur(d_amount_thb),
        "vat_amount": _round_cur(d_vat),
        "wht_amount": _round_cur(d_wht),
        "net_amount": _round_cur(d_net),
        "net_thb": _round_cur(d_net_thb),
        "exchange_rate": float(d_ex),
    }



# =========================================================
# LINE-LEVEL CRUD
# =========================================================

def add_cost_line(data: Dict[str, Any]) -> int:
    tenant_id = get_current_tenant_id()
    qty = float(data.get("quantity") or 1)
    unit_price = float(data.get("unit_price") or 0)
    currency = data.get("currency") or "THB"
    ex_rate = float(data.get("exchange_rate") or 1.0)
    tax_type = data.get("tax_type") or "VAT 7%"
    wht_type = data.get("wht_type") or "None"

    calcs = compute_line_tax_and_net(qty, unit_price, tax_type, wht_type, currency, ex_rate)

    cost_type = str(data.get("cost_type") or "AP").upper()
    cost_status = str(data.get("cost_status") or "ESTIMATED").upper()
    payout_stat = str(data.get("payout_status") or "UNPAID").upper()
    billing_stat = str(data.get("billing_status") or "UNBILLED").upper()
    billable = bool(data.get("billable_to_customer", True) in (True, 1, "1", "true", "True"))

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO job_costs (
                    shipment_id, tenant_id, party_id, cost_type, category, description, supplier,
                    quantity, unit, unit_price, amount, currency, exchange_rate, amount_thb,
                    tax_type, vat_amount, wht_type, wht_amount, net_amount,
                    cost_status, payout_status, billing_status, billable_to_customer,
                    matched_charge_code, matched_ap_id, vendor_invoice_no, vendor_invoice_date,
                    voucher_no, invoice_no, remark, created_by
                )
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                RETURNING id
                """,
                (
                    data["shipment_id"], tenant_id, data.get("party_id"), cost_type,
                    data.get("category"), data.get("description"), data.get("supplier"),
                    qty, data.get("unit") or "UNIT", unit_price, calcs["amount"], currency, calcs["exchange_rate"], calcs["amount_thb"],
                    tax_type, calcs["vat_amount"], wht_type, calcs["wht_amount"], calcs["net_amount"],
                    cost_status, payout_stat, billing_stat, billable,
                    data.get("matched_charge_code"), data.get("matched_ap_id"),
                    data.get("vendor_invoice_no"), data.get("vendor_invoice_date"),
                    data.get("voucher_no"), data.get("invoice_no"),
                    data.get("remark"), data.get("created_by"),
                ),
            )
            row = cur.fetchone()
            conn.commit()
            return row["id"] if isinstance(row, dict) else row[0]


def get_cost_line(cost_id: int) -> Optional[Dict[str, Any]]:
    """Retrieves a single cost line by ID."""
    tenant_id = get_current_tenant_id()
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM job_costs WHERE id=%s AND tenant_id=%s",
                (cost_id, tenant_id),
            )
            row = cur.fetchone()
            return dict(row) if row else None


def update_cost_line(cost_id: int, data: Dict[str, Any]) -> bool:

    tenant_id = get_current_tenant_id()
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM job_costs WHERE id=%s AND tenant_id=%s",
                (cost_id, tenant_id),
            )
            existing = cur.fetchone()
            if not existing:
                return False

            ex_dict = dict(existing)
            qty = float(data.get("quantity", ex_dict.get("quantity", 1)))
            unit_price = float(data.get("unit_price", ex_dict.get("unit_price", 0)))
            currency = data.get("currency", ex_dict.get("currency", "THB"))
            ex_rate = float(data.get("exchange_rate", ex_dict.get("exchange_rate", 1.0)))
            tax_type = data.get("tax_type", ex_dict.get("tax_type", "VAT 7%"))
            wht_type = data.get("wht_type", ex_dict.get("wht_type", "None"))

            calcs = compute_line_tax_and_net(qty, unit_price, tax_type, wht_type, currency, ex_rate)

            cost_status = str(data.get("cost_status", ex_dict.get("cost_status", "ESTIMATED"))).upper()
            payout_stat = str(data.get("payout_status", ex_dict.get("payout_status", "UNPAID"))).upper()
            billing_stat = str(data.get("billing_status", ex_dict.get("billing_status", "UNBILLED"))).upper()
            billable = bool(data.get("billable_to_customer", ex_dict.get("billable_to_customer", True)) in (True, 1, "1", "true", "True"))

            cur.execute(
                """
                UPDATE job_costs SET
                    party_id=%s, category=%s, description=%s, supplier=%s, quantity=%s, unit=%s,
                    unit_price=%s, amount=%s, currency=%s, exchange_rate=%s, amount_thb=%s,
                    tax_type=%s, vat_amount=%s, wht_type=%s, wht_amount=%s, net_amount=%s,
                    cost_status=%s, payout_status=%s, billing_status=%s, billable_to_customer=%s,
                    matched_charge_code=%s, matched_ap_id=%s,
                    vendor_invoice_no=%s, vendor_invoice_date=%s,
                    voucher_no=%s, invoice_no=%s, remark=%s
                WHERE id=%s AND tenant_id=%s
                """,
                (
                    data.get("party_id", ex_dict.get("party_id")),
                    data.get("category", ex_dict.get("category")),
                    data.get("description", ex_dict.get("description")),
                    data.get("supplier", ex_dict.get("supplier")),
                    qty,
                    data.get("unit", ex_dict.get("unit", "UNIT")),
                    unit_price,
                    calcs["amount"],
                    currency,
                    calcs["exchange_rate"],
                    calcs["amount_thb"],
                    tax_type,
                    calcs["vat_amount"],
                    wht_type,
                    calcs["wht_amount"],
                    calcs["net_amount"],
                    cost_status,
                    payout_stat,
                    billing_stat,
                    billable,
                    data.get("matched_charge_code", ex_dict.get("matched_charge_code")),
                    data.get("matched_ap_id", ex_dict.get("matched_ap_id")),
                    data.get("vendor_invoice_no", ex_dict.get("vendor_invoice_no")),
                    data.get("vendor_invoice_date", ex_dict.get("vendor_invoice_date")),
                    data.get("voucher_no", ex_dict.get("voucher_no")),
                    data.get("invoice_no", ex_dict.get("invoice_no")),
                    data.get("remark", ex_dict.get("remark")),
                    cost_id,
                    tenant_id,
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


# =========================================================
# UNIFIED AP / AR MATRIX & ACCRUAL P&L LEDGER
# =========================================================

def get_unified_job_ledger(shipment_id: int) -> Dict[str, Any]:
    """
    Returns complete Unified AP/AR Financial Ledger with side-by-side pairing,
    accrual summaries, line margins, and disbursement/billing status tracking.
    """
    tenant_id = get_current_tenant_id()
    ap_lines = get_cost_lines(shipment_id, cost_type="AP")
    ar_lines = get_cost_lines(shipment_id, cost_type="AR")

    # Accrual P&L sums
    tot_ap_amount = 0.0
    tot_ap_advance = 0.0
    tot_ap_vat = 0.0
    tot_ap_wht = 0.0
    tot_ap_net = 0.0

    ap_unpaid = 0
    ap_requested = 0
    ap_paid = 0

    for ap in ap_lines:
        amt_thb = float(ap.get("amount_thb") or 0)
        ex = float(ap.get("exchange_rate") or 1.0)
        vat_thb = float(ap.get("vat_amount") or 0) * ex
        wht_thb = float(ap.get("wht_amount") or 0) * ex
        net_thb = float(ap.get("net_amount") or 0) * ex

        tot_ap_amount += amt_thb
        tot_ap_vat += vat_thb
        tot_ap_wht += wht_thb
        tot_ap_net += net_thb

        if str(ap.get("tax_type", "")).lower() == "advance":
            tot_ap_advance += amt_thb

        p_stat = str(ap.get("payout_status", "UNPAID")).upper()
        if p_stat == "PAID":
            ap_paid += 1
        elif p_stat == "REQUESTED":
            ap_requested += 1
        else:
            ap_unpaid += 1

    tot_ar_amount = 0.0
    tot_ar_advance = 0.0
    tot_ar_vat = 0.0
    tot_ar_wht = 0.0
    tot_ar_net = 0.0

    ar_unbilled = 0
    ar_invoiced = 0
    ar_collected = 0

    for ar in ar_lines:
        amt_thb = float(ar.get("amount_thb") or 0)
        ex = float(ar.get("exchange_rate") or 1.0)
        vat_thb = float(ar.get("vat_amount") or 0) * ex
        wht_thb = float(ar.get("wht_amount") or 0) * ex
        net_thb = float(ar.get("net_amount") or 0) * ex

        tot_ar_amount += amt_thb
        tot_ar_vat += vat_thb
        tot_ar_wht += wht_thb
        tot_ar_net += net_thb

        if str(ar.get("tax_type", "")).lower() == "advance":
            tot_ar_advance += amt_thb

        b_stat = str(ar.get("billing_status", "UNBILLED")).upper()
        if b_stat in ["COLLECTED", "PAID"]:
            ar_collected += 1
        elif b_stat in ["INVOICED", "BILLED"]:
            ar_invoiced += 1
        else:
            ar_unbilled += 1

    gross_profit = tot_ar_amount - tot_ap_amount
    margin_pct = (gross_profit / tot_ar_amount * 100) if tot_ar_amount > 0 else 0.0

    # Side-by-side pairing
    paired_rows = []
    matched_ar_ids = set()

    for idx, ap in enumerate(ap_lines, start=1):
        # Look for explicitly matched AR first via matched_ap_id
        matched_ar = next((ar for ar in ar_lines if ar.get("matched_ap_id") == ap["id"]), None)
        
        # Fallback to description or charge code matching if not explicitly linked
        if not matched_ar:
            ap_desc = (ap.get("description") or "").strip().lower()
            ap_code = (ap.get("matched_charge_code") or "").strip().lower()
            for ar in ar_lines:
                if ar["id"] in matched_ar_ids:
                    continue
                ar_desc = (ar.get("description") or "").strip().lower()
                ar_code = (ar.get("matched_charge_code") or "").strip().lower()
                if (ap_code and ar_code and ap_code == ar_code) or (ap_desc and ar_desc and (ap_desc in ar_desc or ar_desc in ap_desc)):
                    matched_ar = ar
                    break

        if matched_ar:
            matched_ar_ids.add(matched_ar["id"])

        ap_thb = float(ap.get("amount_thb") or 0)
        ar_thb = float(matched_ar.get("amount_thb") or 0) if matched_ar else 0.0
        line_profit = ar_thb - ap_thb
        line_margin = (line_profit / ar_thb * 100) if ar_thb > 0 else 0.0

        paired_rows.append({
            "line_no": idx,
            "ap_id": ap["id"],
            "ap_party_id": ap.get("party_id"),
            "ap_category": ap.get("category"),
            "ap_description": ap.get("description"),
            "ap_supplier": ap.get("supplier") or "—",
            "ap_currency": ap.get("currency", "THB"),
            "ap_exchange_rate": float(ap.get("exchange_rate") or 1.0),
            "ap_unit_price": float(ap.get("unit_price") or 0),
            "ap_quantity": float(ap.get("quantity") or 1),
            "ap_unit": ap.get("unit") or "UNIT",
            "ap_amount": float(ap.get("amount") or 0),
            "ap_amount_thb": ap_thb,
            "ap_tax_type": ap.get("tax_type", "VAT 7%"),
            "ap_vat_amount": float(ap.get("vat_amount") or 0),
            "ap_wht_type": ap.get("wht_type", "None"),
            "ap_wht_amount": float(ap.get("wht_amount") or 0),
            "ap_net_amount": float(ap.get("net_amount") or 0),
            "ap_payout_status": ap.get("payout_status", "UNPAID"),
            "ap_voucher_no": ap.get("voucher_no") or "—",
            "ap_vendor_inv": ap.get("vendor_invoice_no") or "—",
            "ap_vendor_inv_date": ap.get("vendor_invoice_date") or "—",
            # AR side
            "ar_id": matched_ar["id"] if matched_ar else None,
            "ar_party_id": matched_ar.get("party_id") if matched_ar else None,
            "ar_category": matched_ar.get("category") if matched_ar else "—",
            "ar_description": matched_ar.get("description") if matched_ar else "— (Unbilled)",
            "ar_customer": matched_ar.get("supplier") if matched_ar else "—",
            "ar_currency": matched_ar.get("currency", "THB") if matched_ar else "THB",
            "ar_exchange_rate": float(matched_ar.get("exchange_rate") or 1.0) if matched_ar else 1.0,
            "ar_unit_price": float(matched_ar.get("unit_price") or 0) if matched_ar else 0.0,
            "ar_quantity": float(matched_ar.get("quantity") or 1) if matched_ar else 0.0,
            "ar_unit": matched_ar.get("unit") if matched_ar else "UNIT",
            "ar_amount": float(matched_ar.get("amount") or 0) if matched_ar else 0.0,
            "ar_amount_thb": ar_thb,
            "ar_tax_type": matched_ar.get("tax_type", "VAT 7%") if matched_ar else "VAT 7%",
            "ar_vat_amount": float(matched_ar.get("vat_amount") or 0) if matched_ar else 0.0,
            "ar_wht_type": matched_ar.get("wht_type", "None") if matched_ar else "None",
            "ar_wht_amount": float(matched_ar.get("wht_amount") or 0) if matched_ar else 0.0,
            "ar_net_amount": float(matched_ar.get("net_amount") or 0) if matched_ar else 0.0,
            "ar_billing_status": matched_ar.get("billing_status", "UNBILLED") if matched_ar else "UNBILLED",
            "ar_invoice_no": matched_ar.get("invoice_no") if matched_ar else "—",
            # Profit
            "line_profit_thb": round(line_profit, 2),
            "line_margin_pct": round(line_margin, 1),
            "is_matched": bool(matched_ar),
        })

    # Unmatched standalone AR lines (Pure revenue)
    standalone_idx = len(paired_rows) + 1
    for ar in ar_lines:
        if ar["id"] not in matched_ar_ids:
            ar_thb = float(ar.get("amount_thb") or 0)
            paired_rows.append({
                "line_no": standalone_idx,
                "ap_id": None,
                "ap_category": "—",
                "ap_description": "— (Direct Service Fee)",
                "ap_supplier": "—",
                "ap_currency": "THB",
                "ap_exchange_rate": 1.0,
                "ap_unit_price": 0.0,
                "ap_quantity": 0.0,
                "ap_unit": "UNIT",
                "ap_amount": 0.0,
                "ap_amount_thb": 0.0,
                "ap_tax_type": "—",
                "ap_vat_amount": 0.0,
                "ap_wht_type": "—",
                "ap_wht_amount": 0.0,
                "ap_net_amount": 0.0,
                "ap_payout_status": "—",
                "ap_voucher_no": "—",
                "ap_vendor_inv": "—",
                # AR side
                "ar_id": ar["id"],
                "ar_category": ar.get("category"),
                "ar_description": ar.get("description"),
                "ar_customer": ar.get("supplier") or "—",
                "ar_currency": ar.get("currency", "THB"),
                "ar_exchange_rate": float(ar.get("exchange_rate") or 1.0),
                "ar_unit_price": float(ar.get("unit_price") or 0),
                "ar_quantity": float(ar.get("quantity") or 1),
                "ar_unit": ar.get("unit") or "UNIT",
                "ar_amount": float(ar.get("amount") or 0),
                "ar_amount_thb": ar_thb,
                "ar_tax_type": ar.get("tax_type", "VAT 7%"),
                "ar_vat_amount": float(ar.get("vat_amount") or 0),
                "ar_wht_type": ar.get("wht_type", "None"),
                "ar_wht_amount": float(ar.get("wht_amount") or 0),
                "ar_net_amount": float(ar.get("net_amount") or 0),
                "ar_billing_status": ar.get("billing_status", "UNBILLED"),
                "ar_invoice_no": ar.get("invoice_no") or "—",
                # Profit
                "line_profit_thb": round(ar_thb, 2),
                "line_margin_pct": 100.0,
                "is_matched": False,
            })
            standalone_idx += 1

    return {
        "shipment_id": shipment_id,
        "ap_lines": ap_lines,
        "ar_lines": ar_lines,
        "matrix_rows": paired_rows,
        "summary": {
            "total_ap_amount": round(tot_ap_amount, 2),
            "total_ap_advance": round(tot_ap_advance, 2),
            "total_ap_vat": round(tot_ap_vat, 2),
            "total_ap_wht": round(tot_ap_wht, 2),
            "total_ap_net": round(tot_ap_net, 2),
            "total_ar_amount": round(tot_ar_amount, 2),
            "total_ar_advance": round(tot_ar_advance, 2),
            "total_ar_vat": round(tot_ar_vat, 2),
            "total_ar_wht": round(tot_ar_wht, 2),
            "total_ar_net": round(tot_ar_net, 2),
            "gross_profit": round(gross_profit, 2),
            "margin_pct": round(margin_pct, 1),
            "ap_counts": {"unpaid": ap_unpaid, "requested": ap_requested, "paid": ap_paid},
            "ar_counts": {"unbilled": ar_unbilled, "invoiced": ar_invoiced, "collected": ar_collected},
        },
    }


# =========================================================
# PULL AP ➔ AR WITH CUSTOM MARKUP & DESCRIPTION
# =========================================================

def pull_ap_to_ar(
    shipment_id: int,
    ap_line_ids: List[int],
    markup_pct: float = 0.0,
    target_customer: Optional[str] = None,
    target_currency: Optional[str] = "ORIGINAL",
    custom_desc_map: Optional[Dict[int, str]] = None,
    custom_rates_map: Optional[Dict[int, float]] = None,
    user: Optional[Dict[str, Any]] = None,
) -> List[int]:
    """Pulls selected AP lines to create corresponding AR lines with optional currency conversion."""
    user = user or {"username": "operation"}
    tenant_id = get_current_tenant_id()
    created_ar_ids = []
    custom_desc_map = custom_desc_map or {}
    custom_rates_map = custom_rates_map or {}

    with get_connection() as conn:
        with conn.cursor() as cur:
            for ap_id in ap_line_ids:
                # Check if this AP line has already been pulled to AR
                cur.execute("SELECT id FROM job_costs WHERE matched_ap_id=%s AND tenant_id=%s LIMIT 1", (ap_id, tenant_id))
                existing_ar = cur.fetchone()
                if existing_ar:
                    raise ValueError(f"AP line #{ap_id} has already been pulled to AR (AR #{existing_ar['id'] if isinstance(existing_ar, dict) else existing_ar[0]}).")

                cur.execute("SELECT * FROM job_costs WHERE id=%s AND tenant_id=%s", (ap_id, tenant_id))
                ap = cur.fetchone()
                if not ap:
                    continue
                ap_dict = dict(ap)

                # Description: check custom or default
                desc = custom_desc_map.get(ap_id) or ap_dict.get("description")
                
                ap_curr = ap_dict.get("currency") or "THB"
                ap_ex = float(ap_dict.get("exchange_rate") or 1.0)
                orig_rate = float(ap_dict.get("unit_price") or 0)
                
                # Check if converting to THB or keeping original currency
                if target_currency == "THB" and ap_curr != "THB":
                    base_rate = orig_rate * ap_ex
                    curr = "THB"
                    ex_rate = 1.0
                else:
                    base_rate = orig_rate
                    curr = ap_curr
                    ex_rate = ap_ex

                # Pricing: check custom rate or apply markup %
                if ap_id in custom_rates_map:
                    selling_rate = float(custom_rates_map[ap_id])
                else:
                    selling_rate = base_rate * (1.0 + float(markup_pct or 0) / 100.0)

                qty = float(ap_dict.get("quantity") or 1)
                tax_type = ap_dict.get("tax_type") or "VAT 7%"
                wht_type = ap_dict.get("wht_type") or "None"

                ar_payload = {
                    "shipment_id": shipment_id,
                    "cost_type": "AR",
                    "category": ap_dict.get("category"),
                    "description": desc,
                    "supplier": target_customer or ap_dict.get("supplier"),
                    "quantity": qty,
                    "unit": ap_dict.get("unit") or "UNIT",
                    "unit_price": round(selling_rate, 2),
                    "currency": curr,
                    "exchange_rate": ex_rate,
                    "tax_type": tax_type,
                    "wht_type": wht_type,
                    "matched_charge_code": ap_dict.get("matched_charge_code"),
                    "matched_ap_id": ap_id,
                    "created_by": user.get("username", "operation"),
                    "cost_status": "ESTIMATED",
                    "billing_status": "UNBILLED",
                }
                ar_id = add_cost_line(ar_payload)
                created_ar_ids.append(ar_id)

    return created_ar_ids



# =========================================================
# BATCH AP PAYMENT VOUCHER / ADVANCE GENERATION
# =========================================================

def create_batch_payment_voucher(
    shipment_id: int,
    ap_line_ids: List[int],
    payee_name: Optional[str] = None,
    voucher_type: str = "PAYMENT_VOUCHER",
    due_date: Optional[str] = None,
    user: Optional[Dict[str, Any]] = None,
) -> str:

    """Groups selected AP lines into an AP Payment Voucher or Advance Request."""
    user = user or {"username": "system", "id": 1}
    tenant_id = get_current_tenant_id()
    if not ap_line_ids:
        raise ValueError("Please select at least one AP line to generate a Payment Voucher.")

    # Determine prefix
    prefix = "ADV" if "ADVANCE" in voucher_type.upper() else "PV"
    voucher_no = generate_document_number(prefix)

    with get_connection() as conn:
        with conn.cursor() as cur:
            # 1. Fetch Shipment job_no
            cur.execute("SELECT job_no FROM shipments WHERE id=%s AND tenant_id=%s", (shipment_id, tenant_id))
            s_row = cur.fetchone()
            job_no = s_row["job_no"] if s_row else f"JOB-{shipment_id}"

            # 2. Fetch and validate selected AP lines
            cur.execute(
                f"SELECT * FROM job_costs WHERE id IN ({','.join(['%s']*len(ap_line_ids))}) AND tenant_id=%s",
                (*ap_line_ids, tenant_id)
            )
            selected_lines = [dict(r) for r in cur.fetchall()]
            for l in selected_lines:
                if l.get("voucher_no") and str(l.get("voucher_no")).strip() not in ("—", "None", ""):
                    raise ValueError(f"AP line #{l.get('id')} ({l.get('description')}) is already attached to Voucher {l.get('voucher_no')}.")

            # Auto-inherit payee from selected AP line if not passed or generic
            if not payee_name or str(payee_name).strip() in ("", "— Custom / Freeform —", "—", "None"):
                payee_name = selected_lines[0].get("supplier") or "General Vendor"

            d_subtotal = sum(_dec(l.get("amount")) for l in selected_lines).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            d_vat = sum(_dec(l.get("vat_amount")) for l in selected_lines).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            d_wht = sum(_dec(l.get("wht_amount")) for l in selected_lines).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            d_total = (d_subtotal + d_vat).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            d_net = (d_total - d_wht).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

            subtotal = float(d_subtotal)
            vat_total = float(d_vat)
            wht_total = float(d_wht)
            total = float(d_total)
            net_payable = float(d_net)
            currency = selected_lines[0].get("currency", "THB") if selected_lines else "THB"
            ex_rate = float(selected_lines[0].get("exchange_rate") or 1.0) if selected_lines else 1.0

            # Resolve vendor_id & party_id
            vendor_id = None
            party_id = selected_lines[0].get("party_id") if selected_lines else None
            payee_tax_id = None

            # Look up in business_parties first
            if party_id:
                cur.execute("SELECT id, tax_id, legal_name FROM business_parties WHERE id=%s AND tenant_id=%s", (party_id, tenant_id))
                bp_row = cur.fetchone()
                if bp_row:
                    payee_tax_id = bp_row.get("tax_id") if isinstance(bp_row, dict) else bp_row[1]
            if not payee_tax_id and payee_name:
                cur.execute("SELECT id, tax_id FROM business_parties WHERE (legal_name=%s OR display_name=%s) AND tenant_id=%s LIMIT 1", (payee_name, payee_name, tenant_id))
                bp_row = cur.fetchone()
                if bp_row:
                    party_id = party_id or (bp_row.get("id") if isinstance(bp_row, dict) else bp_row[0])
                    payee_tax_id = bp_row.get("tax_id") if isinstance(bp_row, dict) else bp_row[1]

            # Look up or create in vendors
            if payee_name:
                cur.execute("SELECT id, tax_id FROM vendors WHERE (legal_name = %s OR vendor_code = %s) AND tenant_id = %s LIMIT 1", (payee_name, payee_name, tenant_id))
                v_row = cur.fetchone()
                if v_row:
                    vendor_id = v_row["id"] if isinstance(v_row, dict) else v_row[0]
                    if not payee_tax_id:
                        payee_tax_id = v_row.get("tax_id") if isinstance(v_row, dict) else v_row[1]
            if not vendor_id:
                cur.execute("SELECT id FROM vendors WHERE tenant_id = %s LIMIT 1", (tenant_id,))
                v_row = cur.fetchone()
                if v_row:
                    vendor_id = v_row["id"] if isinstance(v_row, dict) else v_row[0]
                else:
                    v_code = f"V-{(payee_name or 'GEN')[:8].upper().replace(' ', '')}"
                    cur.execute(
                        "INSERT INTO vendors (tenant_id, vendor_code, legal_name, tax_id, status) VALUES (%s, %s, %s, %s, 'Active') RETURNING id",
                        (tenant_id, v_code, payee_name or "General Vendor", payee_tax_id)
                    )
                    v_row = cur.fetchone()
                    vendor_id = v_row["id"] if isinstance(v_row, dict) else v_row[0]

            # Collect and deduplicate vendor invoice numbers
            v_invoices = [str(l.get("vendor_invoice_no")).strip() for l in selected_lines if l.get("vendor_invoice_no") and str(l.get("vendor_invoice_no")).strip() not in ("None", "—", "")]
            vendor_invoice_refs = ", ".join(dict.fromkeys(v_invoices)) if v_invoices else None
            inv_no_val = voucher_no

            # 3. Insert into ap_vouchers
            cur.execute(
                """
                INSERT INTO ap_vouchers (
                    tenant_id, party_id, voucher_no, voucher_type, job_no, vendor_id, payee_name,
                    payee_tax_id, vendor_invoice_refs, invoice_no, invoice_date, due_date,
                    currency, exchange_rate, subtotal, tax, wht_total, total, net_payable, status, created_by
                )
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s, CURRENT_DATE, %s, %s,%s,%s,%s,%s,%s,%s,'REQUESTED',%s)
                RETURNING id
                """,
                (
                    tenant_id, party_id, voucher_no, voucher_type, job_no, vendor_id, payee_name,
                    payee_tax_id, vendor_invoice_refs, inv_no_val, due_date or date.today().isoformat(),
                    currency, ex_rate, subtotal, vat_total, wht_total, total, net_payable, user.get("username", "accountant")
                )
            )
            v_row = cur.fetchone()
            v_id = v_row["id"] if isinstance(v_row, dict) else v_row[0]

            # Insert line items into ap_voucher_items
            for s_idx, it_line in enumerate(selected_lines, start=1):
                cur.execute(
                    """
                    INSERT INTO ap_voucher_items (tenant_id, voucher_id, service_id, service_text, amount, vat_rate, has_tax, wht_rate, pr_no, master_job, sort_order)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        tenant_id, v_id, it_line.get("matched_charge_code") or "EXP",
                        it_line.get("description") or "Operation Cost",
                        float(it_line.get("amount") or 0),
                        7.0 if "7%" in str(it_line.get("tax_type", "")) else 0.0,
                        1 if "7%" in str(it_line.get("tax_type", "")) else 0,
                        1.0 if "1%" in str(it_line.get("wht_type", "")) else (3.0 if "3%" in str(it_line.get("wht_type", "")) else (5.0 if "5%" in str(it_line.get("wht_type", "")) else 0.0)),
                        it_line.get("vendor_invoice_no") or f"PR-{job_no}",
                        job_no,
                        s_idx
                    )
                )

            # 4. Update linked AP cost lines with voucher_no and status
            cur.execute(
                f"UPDATE job_costs SET payout_status='REQUESTED', voucher_no=%s WHERE id IN ({','.join(['%s']*len(ap_line_ids))}) AND tenant_id=%s",
                (voucher_no, *ap_line_ids, tenant_id)
            )
            conn.commit()


    return voucher_no


# =========================================================
# BATCH AR INVOICE GENERATION
# =========================================================

def create_batch_invoice_from_ar(
    shipment_id: int,
    ar_line_ids: List[int],
    customer_id: Optional[int] = None,
    billing_currency: Optional[str] = None,
    exchange_rate: Optional[float] = None,
    user: Optional[Dict[str, Any]] = None,
) -> str:
    """Groups selected AR lines into an official Customer Invoice / Billing Note."""
    user = user or {"username": "system", "id": 1}
    tenant_id = get_current_tenant_id()
    if not ar_line_ids:
        raise ValueError("Please select at least one AR line to generate an Invoice.")

    with get_connection() as conn:
        with conn.cursor() as cur:
            # 1. Fetch Shipment & Customer Info
            cur.execute("SELECT * FROM shipments WHERE id=%s AND tenant_id=%s", (shipment_id, tenant_id))
            ship = cur.fetchone()
            if not ship:
                raise ValueError("Shipment not found.")
            ship_dict = dict(ship)

            cust_id = customer_id or ship_dict.get("customer_id") or 1
            cust_name = ship_dict.get("customer_name") or "Valued Customer"

            # 2. Fetch and validate selected AR lines
            cur.execute(
                f"SELECT * FROM job_costs WHERE id IN ({','.join(['%s']*len(ar_line_ids))}) AND tenant_id=%s",
                (*ar_line_ids, tenant_id)
            )
            selected_lines = [dict(r) for r in cur.fetchall()]
            for l in selected_lines:
                if l.get("invoice_no") and str(l.get("invoice_no")).strip() not in ("—", "None", ""):
                    raise ValueError(f"AR line #{l.get('id')} ({l.get('description')}) is already billed on Invoice {l.get('invoice_no')}.")

            # 3. Determine Billing Currency and Exchange Rate
            target_curr = str(billing_currency or selected_lines[0].get("currency") or "THB").upper()
            target_ex = float(exchange_rate or 1.0)
            if not exchange_rate or exchange_rate <= 0:
                if target_curr == "THB":
                    target_ex = 1.0
                elif selected_lines and selected_lines[0].get("currency") == target_curr:
                    target_ex = float(selected_lines[0].get("exchange_rate") or 1.0)
                elif target_curr == "USD":
                    target_ex = 35.5
                elif target_curr == "EUR":
                    target_ex = 38.5
                elif target_curr == "JPY":
                    target_ex = 0.24
                elif target_curr == "CNY":
                    target_ex = 4.9

            # 4. Build Invoice payload with currency conversion
            from managers.invoice_manager import create_invoice
            inv_items = []
            for l in selected_lines:
                qty = float(l.get("quantity") or 1)
                l_curr = str(l.get("currency") or "THB").upper()
                orig_rate = float(l.get("unit_price") or 0)
                amount_thb = float(l.get("amount_thb") or (orig_rate * qty))

                if l_curr == target_curr:
                    unit_price = orig_rate
                else:
                    unit_price = round((amount_thb / qty) / (target_ex if target_ex > 0 else 1.0), 2)

                inv_items.append({
                    "description": l.get("description") or "Freight Service",
                    "quantity": qty,
                    "unit_price": unit_price,
                    "tax_type": l.get("tax_type") or "VAT 7%",
                    "wht_type": l.get("wht_type") or "None",
                    "unit": l.get("unit") or "UNIT",
                })

            inv_data = {
                "customer_id": cust_id,
                "customer_name": cust_name,
                "job_no": ship_dict.get("job_no"),
                "booking_no": ship_dict.get("booking_no"),
                "mbl_no": ship_dict.get("mbl_no"),
                "hbl_no": ship_dict.get("hbl_no"),
                "vessel": ship_dict.get("vessel"),
                "voyage": ship_dict.get("voyage"),
                "pol": ship_dict.get("pol"),
                "pod": ship_dict.get("pod"),
                "etd": ship_dict.get("etd"),
                "eta": ship_dict.get("eta"),
                "container_no": ship_dict.get("container_summary"),
                "package_qty": ship_dict.get("package_quantity"),
                "gross_weight": ship_dict.get("gross_weight"),
                "measurement_cbm": ship_dict.get("cbm"),
                "currency": target_curr,
                "exchange_rate": target_ex,
                "created_by": user.get("username", "billing_specialist"),
            }

            doc_no = create_invoice(inv_data, inv_items)

            # 5. Update linked AR cost lines
            cur.execute(
                f"UPDATE job_costs SET billing_status='INVOICED', invoice_no=%s WHERE id IN ({','.join(['%s']*len(ar_line_ids))}) AND tenant_id=%s",
                (doc_no, *ar_line_ids, tenant_id)
            )
            conn.commit()

    return doc_no


# =========================================================
# DOCUMENT AUDIT & TRACEABILITY
# =========================================================

def get_job_document_audit(shipment_id: int) -> Dict[str, Any]:
    """
    Retrieves all Payment Vouchers, Advance Requests, and Invoices linked to the job,
    with an itemized breakdown of charges in each document.
    """
    tenant_id = get_current_tenant_id()
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT job_no FROM shipments WHERE id=%s AND tenant_id=%s", (shipment_id, tenant_id))
            s_row = cur.fetchone()
            job_no = s_row["job_no"] if s_row else ""

            # 1. Fetch Payment Vouchers
            vouchers = []
            if job_no:
                cur.execute(
                    "SELECT * FROM ap_vouchers WHERE (job_no=%s OR job_no LIKE %s) AND tenant_id=%s ORDER BY id DESC",
                    (job_no, f"%{job_no}%", tenant_id)
                )
                v_rows = [dict(r) for r in cur.fetchall()]
                for v in v_rows:
                    v_no = v.get("voucher_no")
                    # Fetch included AP lines
                    cur.execute(
                        "SELECT * FROM job_costs WHERE voucher_no=%s AND tenant_id=%s",
                        (v_no, tenant_id)
                    )
                    v["items"] = [dict(r) for r in cur.fetchall()]
                    vouchers.append(v)

            # 2. Fetch Invoices
            invoices = []
            if job_no:
                cur.execute(
                    "SELECT * FROM invoices WHERE (job_no=%s OR job_no LIKE %s) AND tenant_id=%s ORDER BY id DESC",
                    (job_no, f"%{job_no}%", tenant_id)
                )
                inv_rows = [dict(r) for r in cur.fetchall()]
                for inv in inv_rows:
                    doc_no = inv.get("doc_no")
                    cur.execute(
                        "SELECT * FROM job_costs WHERE invoice_no=%s AND tenant_id=%s",
                        (doc_no, tenant_id)
                    )
                    inv["items"] = [dict(r) for r in cur.fetchall()]
                    invoices.append(inv)

    return {
        "job_no": job_no,
        "payment_vouchers": vouchers,
        "invoices": invoices,
    }


def rollback_job_voucher(voucher_no: str, shipment_id: Optional[int] = None, user: Optional[Dict[str, Any]] = None) -> bool:
    """Cancels a Payment Voucher and releases linked AP cost lines back to UNPAID."""
    from managers.ap_manager import cancel_ap_voucher
    return cancel_ap_voucher(voucher_no, user=user)


def rollback_job_invoice(doc_no: str, shipment_id: Optional[int] = None, user: Optional[Dict[str, Any]] = None) -> bool:
    """Cancels a Customer Invoice and releases linked AR revenue lines back to UNBILLED."""
    from managers.invoice_manager import cancel_invoice_document
    return cancel_invoice_document(doc_no, user=user)


# =========================================================
# LEGACY COMPATIBILITY API
# =========================================================

def get_profit_summary(shipment_id: int) -> Dict[str, Any]:
    ledger = get_unified_job_ledger(shipment_id)
    summary = ledger["summary"]
    return {
        "total_ar": summary["total_ar_amount"],
        "total_ap": summary["total_ap_amount"],
        "net_profit": summary["gross_profit"],
        "profit_margin": summary["margin_pct"],
        "ar_actual": summary["total_ar_amount"],
        "ap_actual": summary["total_ap_amount"],
        "actual_net_profit": summary["gross_profit"],
        "estimated_net_profit": summary["gross_profit"],
        "ap_accrued": 0.0,
        "ap_posted": 0.0,
    }


def create_profit_sheet(shipment_id: int, prepared_by: str = "System Engine") -> Dict[str, Any]:
    tenant_id = get_current_tenant_id()
    summary = get_profit_summary(shipment_id)
    sheet_no = f"PS-{shipment_id}-{int(datetime.now().timestamp())}"

    net_profit = summary["actual_net_profit"]
    total_ar = summary["ar_actual"]
    total_ap = summary["ap_actual"]
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


def get_cost_sell_audit_matrix(shipment_id: int) -> Dict[str, Any]:
    ledger = get_unified_job_ledger(shipment_id)
    return {
        "shipment_id": shipment_id,
        "total_cost_thb": ledger["summary"]["total_ap_amount"],
        "total_sell_thb": ledger["summary"]["total_ar_amount"],
        "gross_profit": ledger["summary"]["gross_profit"],
        "margin_pct": ledger["summary"]["margin_pct"],
        "matrix_rows": ledger["matrix_rows"],
    }


def lock_job_financials(shipment_id: int, user: Dict[str, Any]) -> bool:
    uname = user.get("username", "operation")
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE shipments SET financial_locked = TRUE, handover_to_accounting_at = CURRENT_TIMESTAMP, handover_by = %s WHERE id = %s",
                (uname, shipment_id),
            )
            conn.commit()
            return cur.rowcount > 0


def unlock_job_financials(shipment_id: int, user: Dict[str, Any]) -> bool:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE shipments SET financial_locked = FALSE WHERE id = %s",
                (shipment_id,),
            )
            conn.commit()
            return cur.rowcount > 0
