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

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO job_costs (
                    shipment_id, tenant_id, cost_type, category, description, supplier,
                    quantity, unit_price, amount, currency, amount_thb, remark,
                    created_by, cost_status
                )
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                RETURNING id
                """,
                (
                    data["shipment_id"], tenant_id, str(data["cost_type"]).upper(),
                    data.get("category"), data.get("description"), data.get("supplier"),
                    qty, unit_price, amount, currency, amount_thb,
                    data.get("remark"), data.get("created_by"), cost_status,
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

            cur.execute(
                """
                UPDATE job_costs SET
                    category=%s, description=%s, supplier=%s, quantity=%s,
                    unit_price=%s, amount=%s, currency=%s, amount_thb=%s,
                    remark=%s, cost_status=%s
                WHERE id=%s AND tenant_id=%s
                """,
                (
                    data.get("category"), data.get("description"), data.get("supplier"),
                    data.get("quantity"), data.get("unit_price"), new_amt, new_cur,
                    amount_thb, data.get("remark"), cost_status, cost_id, tenant_id,
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
