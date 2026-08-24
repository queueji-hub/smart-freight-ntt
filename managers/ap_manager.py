from __future__ import annotations

from typing import List, Dict, Any, Optional
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime, date
from database.connection import get_connection
from managers.tenant_context import get_current_tenant_id
from managers.document_numbering_service import generate_document_number
from core.audit import log_action


def _r(val: Any) -> float:
    try:
        return float(Decimal(str(val or 0)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
    except Exception:
        return 0.0


def calculate_ap_summary(items: List[Dict[str, Any]], less_vat_diff: float = 0.0, plus_wht_diff: float = 0.0, diff_amount: float = 0.0) -> Dict[str, float]:
    """Calculates AP Payment Voucher figures matching PTS standard."""
    amount_no_vat = 0.0
    amount_vat = 0.0
    total_vat = 0.0
    total_wht = 0.0

    for item in items:
        amt = _r(item.get("amount", 0.0))
        vat_rate = float(item.get("vat_rate", 7.0) if item.get("has_tax", 1) else 0.0)
        wht_rate = float(item.get("wht_rate", 0.0) or 0.0)

        if vat_rate > 0:
            amount_vat += amt
            total_vat += amt * (vat_rate / 100.0)
        else:
            amount_no_vat += amt

        if wht_rate > 0:
            total_wht += amt * (wht_rate / 100.0)

    subtotal = amount_no_vat + amount_vat
    total_vat = _r(total_vat) - _r(less_vat_diff)
    total_wht = _r(total_wht) + _r(plus_wht_diff)
    total_amount = subtotal + total_vat + _r(diff_amount)
    net_payable = total_amount - total_wht

    return {
        "amount_no_vat": _r(amount_no_vat),
        "amount_vat": _r(amount_vat),
        "subtotal": _r(subtotal),
        "tax": _r(total_vat),
        "wht_total": _r(total_wht),
        "less_vat_diff": _r(less_vat_diff),
        "plus_wht_diff": _r(plus_wht_diff),
        "diff_amount": _r(diff_amount),
        "total": _r(total_amount),
        "net_payable": _r(net_payable),
    }


def get_ap_vouchers() -> List[Dict[str, Any]]:
    tenant_id = get_current_tenant_id()
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT ap.*, 
                       COALESCE(v.legal_name, ap.supplier_name, ap.payee_name, '—') as vendor_name,
                       COALESCE(v.tax_id, ap.supplier_tax_id, ap.payee_tax_id, '—') as vendor_tax_id
                FROM ap_vouchers ap
                LEFT JOIN vendors v ON ap.vendor_id = v.id
                WHERE ap.tenant_id = %s 
                ORDER BY ap.id DESC
            """, (tenant_id,))
            rows = cur.fetchall()
            return [dict(r) for r in rows] if rows else []


def get_ap_voucher(voucher_id: int) -> Optional[Dict[str, Any]]:
    tenant_id = get_current_tenant_id()
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT ap.*, 
                       COALESCE(v.legal_name, ap.supplier_name, ap.payee_name, '—') as vendor_name,
                       COALESCE(v.tax_id, ap.supplier_tax_id, ap.payee_tax_id, '—') as vendor_tax_id
                FROM ap_vouchers ap
                LEFT JOIN vendors v ON ap.vendor_id = v.id
                WHERE ap.id = %s AND ap.tenant_id = %s
            """, (voucher_id, tenant_id))
            row = cur.fetchone()
            if not row:
                return None
            voucher = dict(row)
            
            # Fetch line items
            cur.execute("""
                SELECT * FROM ap_voucher_items
                WHERE voucher_id = %s AND tenant_id = %s
                ORDER BY sort_order ASC, id ASC
            """, (voucher_id, tenant_id))
            items = cur.fetchall()
            voucher["items"] = [dict(i) for i in items] if items else []
            return voucher


def create_ap_voucher(data: Dict[str, Any], items: Optional[Any] = None, user: Optional[Dict[str, Any]] = None) -> int:
    tenant_id = get_current_tenant_id()
    if isinstance(items, dict):
        user = items
        items = []
    elif not isinstance(items, list):
        items = []

    if not items and float(data.get("subtotal") or data.get("total") or 0) > 0:
        items = [{
            "service_id": "EXP",
            "service_text": data.get("invoice_no") or data.get("remark") or "General AP Expense",
            "amount": float(data.get("subtotal") or data.get("total") or 0),
            "vat_rate": 7.0 if float(data.get("tax") or 0) > 0 else 0.0,
            "has_tax": 1 if float(data.get("tax") or 0) > 0 else 0,
            "wht_rate": 0.0,
            "pr_no": data.get("ref_purchase_no") or "",
            "master_job": data.get("ref_master_job_no") or data.get("job_no") or "",
        }]

    summary = calculate_ap_summary(
        items,
        less_vat_diff=float(data.get("less_vat_diff") or 0.0),
        plus_wht_diff=float(data.get("plus_wht_diff") or 0.0),
        diff_amount=float(data.get("diff_amount") or 0.0),
    )

    inv_date = data.get("invoice_date") or data.get("pv_date") or date.today().isoformat()
    voucher_no = data.get("voucher_no")
    if not voucher_no or str(voucher_no).strip() == "":
        try:
            voucher_no = generate_document_number("PV", inv_date, digits=4, separator="")
        except Exception:
            voucher_no = f"PV{datetime.now().strftime('%y%m%d%H%M')}"

    with get_connection() as conn:
        try:
            with conn.cursor() as cur:
                username = user.get("username", "system") if isinstance(user, dict) else (str(user) if user else "system")
                
                cur.execute("""
                    INSERT INTO ap_vouchers (
                        tenant_id, voucher_no, voucher_type, payment_type, service_type,
                        job_no, ref_master_job_no, ref_shipment_no, ref_purchase_no,
                        vendor_id, supplier_name, supplier_tax_id, payee_name, payee_tax_id,
                        vendor_invoice_refs, invoice_no, invoice_date, due_date, payment_date,
                        currency, exchange_rate, amount_no_vat, amount_vat, subtotal,
                        tax, wht_total, less_vat_diff, plus_wht_diff, diff_amount,
                        total, net_payable, paid_by, paid_amount, chq_no, chq_date,
                        bank_name, branch_name, supplier_tax_inv_no, supplier_tax_inv_date,
                        supplier_tax_inv_branch, supplier_tax_inv_base, supplier_tax_inv_vat,
                        wht_cert_no, wht_cert_date, wht_pnd_type, wht_base_amount,
                        wht_tax_amount, wht_payer_tax_id, wht_payer_name, status, remark, created_by
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                    ) RETURNING id
                """, (
                    tenant_id,
                    voucher_no,
                    data.get("voucher_type", "PAYMENT_VOUCHER"),
                    data.get("payment_type", "General Payment"),
                    data.get("service_type", "SE"),
                    data.get("job_no"),
                    data.get("ref_master_job_no") or data.get("job_no"),
                    data.get("ref_shipment_no"),
                    data.get("ref_purchase_no"),
                    data.get("vendor_id"),
                    data.get("supplier_name"),
                    data.get("supplier_tax_id"),
                    data.get("payee_name") or data.get("supplier_name"),
                    data.get("payee_tax_id") or data.get("supplier_tax_id"),
                    data.get("vendor_invoice_refs") or data.get("invoice_no"),
                    data.get("invoice_no"),
                    inv_date,
                    data.get("due_date") or inv_date,
                    data.get("payment_date"),
                    data.get("currency", "THB"),
                    float(data.get("exchange_rate") or 1.0),
                    summary["amount_no_vat"],
                    summary["amount_vat"],
                    summary["subtotal"],
                    summary["tax"],
                    summary["wht_total"],
                    summary["less_vat_diff"],
                    summary["plus_wht_diff"],
                    summary["diff_amount"],
                    summary["total"],
                    summary["net_payable"],
                    data.get("paid_by", "Bank Transfer"),
                    float(data.get("paid_amount") or summary["net_payable"]),
                    data.get("chq_no"),
                    data.get("chq_date"),
                    data.get("bank_name"),
                    data.get("branch_name"),
                    data.get("supplier_tax_inv_no"),
                    data.get("supplier_tax_inv_date"),
                    data.get("supplier_tax_inv_branch", "00000"),
                    float(data.get("supplier_tax_inv_base") or summary["amount_vat"]),
                    float(data.get("supplier_tax_inv_vat") or summary["tax"]),
                    data.get("wht_cert_no"),
                    data.get("wht_cert_date"),
                    data.get("wht_pnd_type", "53"),
                    float(data.get("wht_base_amount") or (summary["amount_no_vat"] + summary["amount_vat"])),
                    float(data.get("wht_tax_amount") or summary["wht_total"]),
                    data.get("wht_payer_tax_id", "0735568004823"),
                    data.get("wht_payer_name", "บริษัท ณัฏฐยาราชย์ จำกัด"),
                    data.get("status") or "DRAFT",
                    data.get("remark") or data.get("description"),
                    username,
                ))
                row = cur.fetchone()
                voucher_id = row["id"] if isinstance(row, dict) or hasattr(row, "keys") else row[0]

                # Insert line items
                for idx, it in enumerate(items):
                    cur.execute("""
                        INSERT INTO ap_voucher_items (
                            tenant_id, voucher_id, service_id, service_text, amount,
                            vat_rate, has_tax, wht_rate, pr_no, master_job, sort_order
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, (
                        tenant_id,
                        voucher_id,
                        it.get("service_id", "SVC"),
                        it.get("service_text") or it.get("description", "Service Charge"),
                        float(it.get("amount") or 0.0),
                        float(it.get("vat_rate") or 7.0),
                        1 if it.get("has_tax", 1) else 0,
                        float(it.get("wht_rate") or 0.0),
                        it.get("pr_no") or data.get("ref_purchase_no") or "",
                        it.get("master_job") or data.get("ref_master_job_no") or data.get("job_no") or "",
                        idx
                    ))

                conn.commit()
                if user:
                    user_id = user.get("id", 1) if isinstance(user, dict) else 1
                    log_action(user_id, tenant_id, "ap_voucher", str(voucher_id), "CREATED")
                return voucher_id
        except Exception as e:
            conn.rollback()
            raise RuntimeError(f"Failed to create AP voucher: {str(e)}")


def update_ap_voucher_status(voucher_id: int, new_status: str, user: Dict[str, Any] = None):
    tenant_id = get_current_tenant_id()
    with get_connection() as conn:
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE ap_vouchers SET status=%s, updated_at=CURRENT_TIMESTAMP
                    WHERE id=%s AND tenant_id=%s
                """, (new_status, voucher_id, tenant_id))
                
                if cur.rowcount == 0:
                    raise ValueError("AP voucher not found or unauthorized")
                conn.commit()
                if user:
                    user_id = user.get("id", 1) if isinstance(user, dict) else 1
                    log_action(user_id, tenant_id, "ap_voucher", str(voucher_id), f"STATUS_{new_status}")
        except Exception as e:
            conn.rollback()
            raise RuntimeError(f"Failed to update AP voucher status: {str(e)}")
