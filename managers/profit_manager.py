"""Job Profitability & Approval Sheet management."""
from datetime import datetime
from typing import List, Dict, Any, Optional
from database.connection import get_connection

def _ensure_tables():
    """Ensure job_costs and profit_sheets tables exist for PostgreSQL."""
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS job_costs (
                id SERIAL PRIMARY KEY,
                shipment_id INTEGER NOT NULL,
                cost_type TEXT NOT NULL CHECK(cost_type IN ('AR','AP')),
                category TEXT,
                description TEXT,
                supplier TEXT,
                quantity NUMERIC(15,2) DEFAULT 1,
                unit_price NUMERIC(15,2) DEFAULT 0,
                amount NUMERIC(15,2) DEFAULT 0,
                currency TEXT DEFAULT 'THB',
                amount_thb NUMERIC(15,2) DEFAULT 0,
                remark TEXT,
                created_by TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_jc_shipment ON job_costs(shipment_id)")
        
        conn.execute("""
            CREATE TABLE IF NOT EXISTS profit_sheets (
                id SERIAL PRIMARY KEY,
                shipment_id INTEGER NOT NULL,
                job_no TEXT NOT NULL,
                sheet_no TEXT UNIQUE NOT NULL,
                total_ar NUMERIC(15,2) DEFAULT 0,
                total_ap NUMERIC(15,2) DEFAULT 0,
                net_profit NUMERIC(15,2) DEFAULT 0,
                profit_margin NUMERIC(5,2) DEFAULT 0,
                prepared_by TEXT,
                prepared_at TIMESTAMP,
                reviewed_by TEXT,
                reviewed_at TIMESTAMP,
                approved_by TEXT,
                approved_at TIMESTAMP,
                pdf_path TEXT,
                status TEXT DEFAULT 'Generated',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

def _convert_to_thb(amount: float, currency: str) -> float:
    if not currency or currency.upper() == "THB": return amount
    try:
        from managers.fx_manager import convert
        return convert(amount, currency, "THB")
    except Exception: return amount

def add_cost_line(data: Dict[str, Any]) -> int:
    _ensure_tables()
    qty = float(data.get("quantity", 1) or 1)
    unit_price = float(data.get("unit_price", 0) or 0)
    amount = float(data.get("amount", qty * unit_price) or 0)
    currency = data.get("currency", "THB")
    amount_thb = _convert_to_thb(amount, currency)
    
    with get_connection() as conn:
        cur = conn.execute("""
            INSERT INTO job_costs (shipment_id, cost_type, category, description, supplier, 
                                   quantity, unit_price, amount, currency, amount_thb, remark, created_by)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id
        """, (data["shipment_id"], data["cost_type"], data.get("category"), data.get("description"), 
              data.get("supplier"), qty, unit_price, amount, currency, amount_thb, data.get("remark"), data.get("created_by")))
        return cur.fetchone()[0]

def get_profit_summary(shipment_id: int) -> Dict[str, Any]:
    _ensure_tables()
    with get_connection() as conn:
        ar = conn.execute("SELECT COALESCE(SUM(amount_thb), 0) FROM job_costs WHERE shipment_id=%s AND cost_type='AR'", (shipment_id,)).fetchone()[0]
        ap = conn.execute("SELECT COALESCE(SUM(amount_thb), 0) FROM job_costs WHERE shipment_id=%s AND cost_type='AP'", (shipment_id,)).fetchone()[0]
    
    net = float(ar) - float(ap)
    margin = (net / float(ar) * 100) if ar > 0 else 0
    return {"total_ar": round(float(ar), 2), "total_ap": round(float(ap), 2), "net_profit": round(net, 2), "profit_margin": round(margin, 2)}

def create_profit_sheet(shipment_id: int, prepared_by: str = None, pdf_path: str = None) -> Dict[str, Any]:
    _ensure_tables()
    summary = get_profit_summary(shipment_id)
    with get_connection() as conn:
        job_no = conn.execute("SELECT job_no FROM shipments WHERE id=%s", (shipment_id,)).fetchone()[0]
        count = conn.execute("SELECT COUNT(*) FROM profit_sheets WHERE shipment_id=%s", (shipment_id,)).fetchone()[0]
        sheet_no = f"PS-{job_no}-{count + 1:02d}"
        
        cur = conn.execute("""
            INSERT INTO profit_sheets (shipment_id, job_no, sheet_no, total_ar, total_ap, net_profit, profit_margin, prepared_by, prepared_at, pdf_path, status)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,CURRENT_TIMESTAMP,%s,'Generated') RETURNING id
        """, (shipment_id, job_no, sheet_no, summary["total_ar"], summary["total_ap"], summary["net_profit"], summary["profit_margin"], prepared_by, pdf_path))
        return {**summary, "sheet_no": sheet_no, "id": cur.fetchone()[0]}

def update_signoff(sheet_id: int, role: str, signer_name: str) -> bool:
    _ensure_tables()
    col = "reviewed" if role == "review" else "approved"
    with get_connection() as conn:
        conn.execute(f"UPDATE profit_sheets SET {col}_by=%s, {col}_at=CURRENT_TIMESTAMP WHERE id=%s", (signer_name, sheet_id))
    return True

def list_profit_sheets(shipment_id: int = None) -> List[Dict[str, Any]]:
    sql = "SELECT * FROM profit_sheets"
    params = []
    if shipment_id: sql += " WHERE shipment_id=%s"; params.append(shipment_id)
    with get_connection() as conn:
        return [dict(r) for r in conn.execute(sql + " ORDER BY created_at DESC", params).fetchall()]

def has_profit_sheet(shipment_id: int) -> bool:
    with get_connection() as conn:
        return bool(conn.execute("SELECT 1 FROM profit_sheets WHERE shipment_id=%s LIMIT 1", (shipment_id,)).fetchone())