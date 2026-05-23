from typing import List, Dict, Any, Optional
from database.connection import get_connection

def add_cost_line(data: Dict[str, Any]) -> int:
    """Add a cost/revenue line to a shipment."""
    qty = float(data.get("quantity") or 1)
    unit_price = float(data.get("unit_price") or 0)
    amount = float(data.get("amount") or (qty * unit_price))
    currency = data.get("currency") or "THB"
    amount_thb = _convert_to_thb(amount, currency)
    
    with get_connection() as conn:
        cur = conn.execute("""
            INSERT INTO job_costs (shipment_id, cost_type, category, description, supplier, 
                                   quantity, unit_price, amount, currency, amount_thb, remark, created_by)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id
        """, (data["shipment_id"], data["cost_type"], data.get("category"), data.get("description"), 
              data.get("supplier"), qty, unit_price, amount, currency, amount_thb, data.get("remark"), data.get("created_by")))
        conn.commit()
        return cur.fetchone()['id']

def update_cost_line(cost_id: int, data: Dict[str, Any]) -> bool:
    """Update cost/revenue line with recalculation."""
    with get_connection() as conn:
        # ดึงค่าเก่าเพื่อใช้คำนวณ
        row = conn.execute("SELECT amount, currency FROM job_costs WHERE id=%s", (cost_id,)).fetchone()
        if not row: return False
        
        # เตรียมค่าใหม่
        new_amt = float(data.get("amount", row['amount']))
        new_cur = data.get("currency", row['currency'])
        amount_thb = _convert_to_thb(new_amt, new_cur)
        
        # ปรับปรุงข้อมูล
        conn.execute("""
            UPDATE job_costs SET 
            category=%s, description=%s, supplier=%s, quantity=%s, unit_price=%s, 
            amount=%s, currency=%s, amount_thb=%s, remark=%s 
            WHERE id=%s
        """, (data.get("category"), data.get("description"), data.get("supplier"), data.get("quantity"), 
              data.get("unit_price"), new_amt, new_cur, amount_thb, data.get("remark"), cost_id))
        conn.commit()
        return True

def get_profit_summary(shipment_id: int) -> Dict[str, Any]:
    """Calculate AR/AP totals and profitability."""
    with get_connection() as conn:
        row = conn.execute("""
            SELECT 
                COALESCE(SUM(amount_thb) FILTER (WHERE cost_type='AR'), 0) as ar,
                COALESCE(SUM(amount_thb) FILTER (WHERE cost_type='AP'), 0) as ap
            FROM job_costs WHERE shipment_id=%s
        """, (shipment_id,)).fetchone()
    
    ar, ap = float(row['ar']), float(row['ap'])
    net = ar - ap
    margin = (net / ar * 100) if ar > 0 else 0
    return {"total_ar": round(ar, 2), "total_ap": round(ap, 2), "net_profit": round(net, 2), "profit_margin": round(margin, 2)}

def update_signoff(sheet_id: int, role: str, signer_name: str) -> bool:
    """Update approval/review status."""
    col = "reviewed" if role == "review" else "approved"
    with get_connection() as conn:
        conn.execute(f"UPDATE profit_sheets SET {col}_by=%s, {col}_at=CURRENT_TIMESTAMP WHERE id=%s", 
                     (signer_name, sheet_id))
        conn.commit()
    return True