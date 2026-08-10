import os

PROFIT_MANAGER_CODE = """from managers.tenant_context import get_current_tenant_id
from datetime import datetime
from typing import List, Dict, Any, Optional
from database.connection import get_connection

AR_CATEGORIES = [
    "Ocean Freight Revenue",
    "Local Terminal Charges (AR)",
    "Customs Clearance Service",
    "Inland Trucking Revenue",
    "Warehousing",
    "Miscellaneous Revenue"
]

AP_CATEGORIES = [
    "Ocean Freight Cost",
    "Port Terminal Cost",
    "Customs Duty Paid",
    "Inland Carrier Expenses",
    "Agent Handling Fee",
    "Miscellaneous Cost"
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
    cost_status = data.get("cost_status") or "ESTIMATED"
    
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute('''
                INSERT INTO job_costs (shipment_id, cost_type, category, description, supplier, 
                                       quantity, unit_price, amount, currency, amount_thb, remark, created_by, cost_status)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id
            ''', (data["shipment_id"], data["cost_type"].upper(), data.get("category"), data.get("description"), 
                  data.get("supplier"), qty, unit_price, amount, currency, amount_thb, data.get("remark"), data.get("created_by"), cost_status))
            conn.commit()
            row = cur.fetchone()
            return row['id']

def update_cost_line(cost_id: int, data: Dict[str, Any]) -> bool:
    tenant_id = get_current_tenant_id()
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT amount, currency FROM job_costs WHERE id=%s", (cost_id,))
            row = cur.fetchone()
            if not row:
                return False
            
            new_amt = float(data.get("amount", row['amount']))
            new_cur = data.get("currency", row['currency'])
            amount_thb = _convert_to_thb(new_amt, new_cur)
            cost_status = data.get("cost_status", "ESTIMATED")
            
            cur.execute('''
                UPDATE job_costs SET 
                category=%s, description=%s, supplier=%s, quantity=%s, unit_price=%s, 
                amount=%s, currency=%s, amount_thb=%s, remark=%s, cost_status=%s
                WHERE id=%s
            ''', (data.get("category"), data.get("description"), data.get("supplier"), data.get("quantity"), 
                  data.get("unit_price"), new_amt, new_cur, amount_thb, data.get("remark"), cost_status, cost_id))
            conn.commit()
            return True

def delete_cost_line(cost_id: int) -> bool:
    tenant_id = get_current_tenant_id()
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM job_costs WHERE id=%s", (cost_id,))
            conn.commit()
            return True

def get_cost_lines(shipment_id: int, cost_type: Optional[str] = None) -> List[Dict[str, Any]]:
    tenant_id = get_current_tenant_id()
    with get_connection() as conn:
        with conn.cursor() as cur:
            if cost_type:
                cur.execute("SELECT * FROM job_costs WHERE shipment_id=%s AND cost_type=%s ORDER BY id ASC", 
                            (shipment_id, cost_type.upper()))
            else:
                cur.execute("SELECT * FROM job_costs WHERE shipment_id=%s ORDER BY id ASC", (shipment_id,))
            rows = cur.fetchall()
            return [dict(r) for r in rows]

def get_profit_summary(shipment_id: int) -> Dict[str, Any]:
    tenant_id = get_current_tenant_id()
    with get_connection() as conn:
        with conn.cursor() as cur:
            # Aggregate buckets based on cost_status
            cur.execute('''
                SELECT 
                    cost_type, cost_status, COALESCE(SUM(amount_thb), 0) as total
                FROM job_costs WHERE shipment_id=%s
                GROUP BY cost_type, cost_status
            ''', (shipment_id,))
            rows = cur.fetchall()
            
            ar_estimated = 0.0
            ar_actual = 0.0
            ap_estimated = 0.0
            ap_accrued = 0.0
            ap_actual = 0.0
            ap_posted = 0.0

            for r in rows:
                c_type = r['cost_type'].upper()
                c_status = r['cost_status'].upper()
                tot = float(r['total'])
                
                if c_type == 'AR':
                    if c_status == 'ESTIMATED':
                        ar_estimated += tot
                    else:
                        ar_actual += tot
                elif c_type == 'AP':
                    if c_status == 'ESTIMATED':
                        ap_estimated += tot
                    elif c_status == 'ACCRUED':
                        ap_accrued += tot
                    elif c_status == 'ACTUAL':
                        ap_actual += tot
                    elif c_status == 'POSTED':
                        ap_posted += tot

            # Phase D63 & D76: Include Posted AP Vouchers for POSTED bucket
            cur.execute('''
                SELECT COALESCE(SUM(ap.total * ap.exchange_rate), 0) as total_ap_vouchers
                FROM ap_vouchers ap
                JOIN shipments s ON ap.job_no = s.job_no
                WHERE s.id = %s AND ap.tenant_id = %s AND ap.status IN ('POSTED', 'PARTIALLY_PAID', 'PAID')
            ''', (shipment_id, tenant_id))
            ap_row = cur.fetchone()
            if ap_row and ap_row['total_ap_vouchers']:
                ap_posted += float(ap_row['total_ap_vouchers'])

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
        "actual_net_profit": round(act_net, 2)
    }

def create_profit_sheet(shipment_id: int, prepared_by: str = "System Engine") -> Dict[str, Any]:
    tenant_id = get_current_tenant_id()
    summary = get_profit_summary(shipment_id)
    sheet_no = f"PS-{shipment_id}-{int(datetime.now().timestamp())}"
    
    # Minimal profit sheet logic for MVP D76
    net_profit = summary["actual_net_profit"]
    total_ar = summary["ar_actual"]
    total_ap = summary["ap_accrued"] + summary["ap_actual"] + summary["ap_posted"]
    margin = (net_profit / total_ar * 100) if total_ar > 0 else 0.0

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute('''
                INSERT INTO profit_sheets (shipment_id, sheet_no, total_ar, total_ap, net_profit, profit_margin, prepared_by)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING *
            ''', (shipment_id, sheet_no, total_ar, total_ap, net_profit, margin, prepared_by))
            row = cur.fetchone()
            conn.commit()
            return dict(row) if row else {}

def list_profit_sheets(shipment_id: int) -> List[Dict[str, Any]]:
    tenant_id = get_current_tenant_id()
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM profit_sheets WHERE shipment_id=%s ORDER BY id DESC", (shipment_id,))
            rows = cur.fetchall()
            return [dict(r) for r in rows]

def update_signoff(sheet_id: int, role: str, signer_name: str) -> bool:
    tenant_id = get_current_tenant_id()
    col = "reviewed" if role == "review" else "approved"
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(f"UPDATE profit_sheets SET {col}_by=%s, {col}_at=CURRENT_TIMESTAMP WHERE id=%s", 
                         (signer_name, sheet_id))
            conn.commit()
            return True
"""

with open("managers/profit_manager.py", "w", encoding="utf-8") as f:
    f.write(PROFIT_MANAGER_CODE)
print("Updated managers/profit_manager.py")
