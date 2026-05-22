"""Job Profitability & Approval Sheet management.

Each shipment has multiple cost lines (AR = Selling, AP = Cost) and can have
one or more profit sheets generated for sign-off. Status changes to 'Closed'
are blocked until at least one profit sheet exists.
"""
from datetime import datetime, date
from typing import List, Dict, Any, Optional
from database.connection import get_connection


# ===== Cost categories =====
AR_CATEGORIES = [
    "Ocean Freight (Sell)",
    "Local Charges (Sell)",
    "Trucking (Sell)",
    "Customs (Sell)",
    "DOC Fee",
    "Handling Fee",
    "Other Revenue",
]

AP_CATEGORIES = [
    "Ocean Freight (Liner)",
    "Co-loader Cost",
    "Overseas Agent",
    "Trucking Supplier",
    "Customs Broker",
    "Warehouse / CFS",
    "Documentation",
    "Other Cost",
]


def _ensure_tables():
    with get_connection() as conn:
        # Cost lines (AR or AP)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS job_costs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                shipment_id INTEGER NOT NULL,
                cost_type TEXT NOT NULL CHECK(cost_type IN ('AR','AP')),
                category TEXT,
                description TEXT,
                supplier TEXT,
                quantity REAL DEFAULT 1,
                unit_price REAL DEFAULT 0,
                amount REAL DEFAULT 0,
                currency TEXT DEFAULT 'THB',
                amount_thb REAL DEFAULT 0,
                remark TEXT,
                created_by TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_jc_shipment "
                     "ON job_costs(shipment_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_jc_type "
                     "ON job_costs(cost_type)")
        
        # Profit sheets (generated for sign-off)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS profit_sheets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                shipment_id INTEGER NOT NULL,
                job_no TEXT NOT NULL,
                sheet_no TEXT UNIQUE NOT NULL,
                total_ar REAL DEFAULT 0,
                total_ap REAL DEFAULT 0,
                net_profit REAL DEFAULT 0,
                profit_margin REAL DEFAULT 0,
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
        conn.execute("CREATE INDEX IF NOT EXISTS idx_ps_shipment "
                     "ON profit_sheets(shipment_id)")


def _convert_to_thb(amount: float, currency: str, on_date=None) -> float:
    """Convert amount to THB using FX rate."""
    if not currency or currency.upper() == "THB":
        return amount
    try:
        from managers.fx_manager import convert
        return convert(amount, currency, "THB", on_date)
    except Exception:
        return amount


def add_cost_line(data: Dict[str, Any]) -> int:
    """Add a new cost line (AR or AP)."""
    _ensure_tables()
    qty = float(data.get("quantity", 1) or 1)
    unit_price = float(data.get("unit_price", 0) or 0)
    amount = float(data.get("amount", qty * unit_price) or 0)
    currency = data.get("currency", "THB")
    amount_thb = _convert_to_thb(amount, currency)
    
    with get_connection() as conn:
        cur = conn.execute("""
            INSERT INTO job_costs (
                shipment_id, cost_type, category, description, supplier,
                quantity, unit_price, amount, currency, amount_thb,
                remark, created_by
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            data["shipment_id"], data["cost_type"],
            data.get("category"), data.get("description"),
            data.get("supplier"), qty, unit_price, amount,
            currency, amount_thb,
            data.get("remark"), data.get("created_by"),
        ))
    return cur.lastrowid


def update_cost_line(cost_id: int, data: Dict[str, Any]) -> bool:
    """Update existing cost line."""
    _ensure_tables()
    fields = ["category", "description", "supplier", "quantity",
              "unit_price", "amount", "currency", "remark"]
    sets, params = [], []
    for f in fields:
        if f in data:
            sets.append(f"{f}=?"); params.append(data[f])
    
    # Recalc amount_thb if currency or amount changed
    if "amount" in data or "currency" in data:
        with get_connection() as conn:
            row = conn.execute("SELECT amount, currency FROM job_costs WHERE id=?",
                                (cost_id,)).fetchone()
        if row:
            new_amt = data.get("amount", row["amount"])
            new_cur = data.get("currency", row["currency"])
            sets.append("amount_thb=?")
            params.append(_convert_to_thb(new_amt or 0, new_cur or "THB"))
    
    if not sets:
        return False
    params.append(cost_id)
    with get_connection() as conn:
        conn.execute(f"UPDATE job_costs SET {', '.join(sets)} WHERE id=?", params)
    return True


def delete_cost_line(cost_id: int) -> bool:
    _ensure_tables()
    with get_connection() as conn:
        cur = conn.execute("DELETE FROM job_costs WHERE id=?", (cost_id,))
    return cur.rowcount > 0


def get_cost_lines(shipment_id: int,
                    cost_type: Optional[str] = None) -> List[Dict[str, Any]]:
    _ensure_tables()
    sql = "SELECT * FROM job_costs WHERE shipment_id=?"
    params = [shipment_id]
    if cost_type:
        sql += " AND cost_type=?"
        params.append(cost_type)
    sql += " ORDER BY cost_type, id"
    with get_connection() as conn:
        rows = conn.execute(sql, params).fetchall()
    return [dict(r) for r in rows]


def get_profit_summary(shipment_id: int) -> Dict[str, Any]:
    """Calculate profit metrics for a shipment.
    Returns total_ar, total_ap, net_profit, profit_margin."""
    _ensure_tables()
    with get_connection() as conn:
        ar = conn.execute(
            "SELECT COALESCE(SUM(amount_thb), 0) FROM job_costs "
            "WHERE shipment_id=? AND cost_type='AR'", (shipment_id,)
        ).fetchone()[0]
        ap = conn.execute(
            "SELECT COALESCE(SUM(amount_thb), 0) FROM job_costs "
            "WHERE shipment_id=? AND cost_type='AP'", (shipment_id,)
        ).fetchone()[0]
    
    net = (ar or 0) - (ap or 0)
    margin = (net / ar * 100) if ar and ar > 0 else 0
    return {
        "total_ar": round(ar or 0, 2),
        "total_ap": round(ap or 0, 2),
        "net_profit": round(net, 2),
        "profit_margin": round(margin, 2),
    }


# ===== Profit Sheets =====

def generate_sheet_no(shipment_id: int) -> str:
    """Generate unique sheet number based on job_no + sequence."""
    with get_connection() as conn:
        row = conn.execute("SELECT job_no FROM shipments WHERE id=?",
                            (shipment_id,)).fetchone()
        if not row:
            return f"PS-{shipment_id}-1"
        job_no = row["job_no"]
        existing = conn.execute(
            "SELECT COUNT(*) FROM profit_sheets WHERE shipment_id=?",
            (shipment_id,)
        ).fetchone()[0]
    return f"PS-{job_no}-{existing + 1:02d}"


def create_profit_sheet(shipment_id: int, prepared_by: str = None,
                         pdf_path: str = None) -> Dict[str, Any]:
    """Create a profit sheet record + return summary."""
    _ensure_tables()
    summary = get_profit_summary(shipment_id)
    
    with get_connection() as conn:
        row = conn.execute("SELECT job_no FROM shipments WHERE id=?",
                            (shipment_id,)).fetchone()
        job_no = row["job_no"] if row else f"#{shipment_id}"
    
    sheet_no = generate_sheet_no(shipment_id)
    now = datetime.now().isoformat(timespec="seconds")
    
    with get_connection() as conn:
        cur = conn.execute("""
            INSERT INTO profit_sheets (
                shipment_id, job_no, sheet_no, total_ar, total_ap,
                net_profit, profit_margin, prepared_by, prepared_at,
                pdf_path, status
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?)
        """, (shipment_id, job_no, sheet_no,
               summary["total_ar"], summary["total_ap"],
               summary["net_profit"], summary["profit_margin"],
               prepared_by, now, pdf_path, "Generated"))
    
    return {**summary, "sheet_no": sheet_no, "id": cur.lastrowid,
            "job_no": job_no, "prepared_by": prepared_by,
            "prepared_at": now}


def list_profit_sheets(shipment_id: int = None) -> List[Dict[str, Any]]:
    _ensure_tables()
    sql = "SELECT * FROM profit_sheets"
    params = []
    if shipment_id:
        sql += " WHERE shipment_id=?"
        params.append(shipment_id)
    sql += " ORDER BY created_at DESC"
    with get_connection() as conn:
        rows = conn.execute(sql, params).fetchall()
    return [dict(r) for r in rows]


def has_profit_sheet(shipment_id: int) -> bool:
    """Check if shipment has at least one profit sheet generated."""
    _ensure_tables()
    with get_connection() as conn:
        row = conn.execute(
            "SELECT 1 FROM profit_sheets WHERE shipment_id=? LIMIT 1",
            (shipment_id,)
        ).fetchone()
    return bool(row)


def update_signoff(sheet_id: int, role: str, signer_name: str) -> bool:
    """Record sign-off (reviewed_by or approved_by)."""
    _ensure_tables()
    now = datetime.now().isoformat(timespec="seconds")
    field_map = {
        "review": ("reviewed_by", "reviewed_at"),
        "approve": ("approved_by", "approved_at"),
    }
    if role not in field_map:
        return False
    name_col, date_col = field_map[role]
    with get_connection() as conn:
        conn.execute(
            f"UPDATE profit_sheets SET {name_col}=?, {date_col}=? WHERE id=?",
            (signer_name, now, sheet_id)
        )
    return True
