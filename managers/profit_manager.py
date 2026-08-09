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
    """Helper to convert currency to THB using fx_manager if available."""
    if not currency or currency.upper() == "THB":
        return float(amount)
    try:
        from managers.fx_manager import convert
        return convert(amount, currency, "THB")
    except Exception:
        return float(amount)


def add_cost_line(data: Dict[str, Any]) -> int:
    """Add a cost/revenue line to a shipment."""
    qty = float(data.get("quantity") or 1)
    unit_price = float(data.get("unit_price") or 0)
    amount = float(data.get("amount") or (qty * unit_price))
    currency = data.get("currency") or "THB"
    amount_thb = _convert_to_thb(amount, currency)
    
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO job_costs (shipment_id, cost_type, category, description, supplier, 
                                       quantity, unit_price, amount, currency, amount_thb, remark, created_by)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id
            """, (data["shipment_id"], data["cost_type"].upper(), data.get("category"), data.get("description"), 
                  data.get("supplier"), qty, unit_price, amount, currency, amount_thb, data.get("remark"), data.get("created_by")))
            conn.commit()
            row = cur.fetchone()
            return row['id']


def update_cost_line(cost_id: int, data: Dict[str, Any]) -> bool:
    """Update cost/revenue line with recalculation."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT amount, currency FROM job_costs WHERE id=%s", (cost_id,))
            row = cur.fetchone()
            if not row:
                return False
            
            new_amt = float(data.get("amount", row['amount']))
            new_cur = data.get("currency", row['currency'])
            amount_thb = _convert_to_thb(new_amt, new_cur)
            
            cur.execute("""
                UPDATE job_costs SET 
                category=%s, description=%s, supplier=%s, quantity=%s, unit_price=%s, 
                amount=%s, currency=%s, amount_thb=%s, remark=%s 
                WHERE id=%s
            """, (data.get("category"), data.get("description"), data.get("supplier"), data.get("quantity"), 
                  data.get("unit_price"), new_amt, new_cur, amount_thb, data.get("remark"), cost_id))
            conn.commit()
            return True


def delete_cost_line(cost_id: int) -> bool:
    """Delete a cost line item by ID."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM job_costs WHERE id=%s", (cost_id,))
            conn.commit()
            return True


def get_cost_lines(shipment_id: int, cost_type: Optional[str] = None) -> List[Dict[str, Any]]:
    """Retrieve cost/revenue lines for a shipment."""
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
    """Calculate AR/AP totals and profitability."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT 
                    COALESCE(SUM(amount_thb) FILTER (WHERE cost_type='AR'), 0) as ar,
                    COALESCE(SUM(amount_thb) FILTER (WHERE cost_type='AP'), 0) as ap
                FROM job_costs WHERE shipment_id=%s
            """, (shipment_id,))
            row = cur.fetchone()
    
    ar = float(row['ar']) if row and row['ar'] else 0.0
    ap = float(row['ap']) if row and row['ap'] else 0.0
    net = ar - ap
    margin = (net / ar * 100) if ar > 0 else 0.0
    return {"total_ar": round(ar, 2), "total_ap": round(ap, 2), "net_profit": round(net, 2), "profit_margin": round(margin, 2)}


def create_profit_sheet(shipment_id: int, prepared_by: str = "System Engine") -> Dict[str, Any]:
    """Generate or retrieve profit sheet snapshot for a shipment."""
    summary = get_profit_summary(shipment_id)
    sheet_no = f"PS-{shipment_id}-{int(datetime.now().timestamp())}"
    
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO profit_sheets (shipment_id, sheet_no, total_ar, total_ap, net_profit, profit_margin, prepared_by)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING *
            """, (shipment_id, sheet_no, summary["total_ar"], summary["total_ap"], 
                  summary["net_profit"], summary["profit_margin"], prepared_by))
            row = cur.fetchone()
            conn.commit()
            return dict(row) if row else {}


def list_profit_sheets(shipment_id: int) -> List[Dict[str, Any]]:
    """List all historical profit sheets for a shipment."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM profit_sheets WHERE shipment_id=%s ORDER BY id DESC", (shipment_id,))
            rows = cur.fetchall()
            return [dict(r) for r in rows]


def update_signoff(sheet_id: int, role: str, signer_name: str) -> bool:
    """Update review or approve status on a profit sheet."""
    col = "reviewed" if role == "review" else "approved"
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(f"UPDATE profit_sheets SET {col}_by=%s, {col}_at=CURRENT_TIMESTAMP WHERE id=%s", 
                         (signer_name, sheet_id))
            conn.commit()
            return True