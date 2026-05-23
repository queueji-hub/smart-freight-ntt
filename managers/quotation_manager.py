"""Quotation management operations."""
from typing import List, Dict, Any, Optional
from database.connection import get_connection

def _ensure_table():
    """Ensure the quotations table exists."""
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS quotations (
                id SERIAL PRIMARY KEY,
                quotation_no TEXT UNIQUE NOT NULL,
                customer_id INTEGER,
                customer_name TEXT,
                issue_date DATE,
                valid_until DATE,
                subtotal NUMERIC(15,2),
                vat_amount NUMERIC(15,2),
                total_amount NUMERIC(15,2),
                status TEXT DEFAULT 'Draft',
                remark TEXT,
                created_by TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

def list_quotations(status: str = None, limit: int = 50) -> List[Dict[str, Any]]:
    """Retrieve list of quotations with optional status filter."""
    _ensure_table()
    sql = "SELECT * FROM quotations WHERE 1=1"
    params = []
    
    if status:
        sql += " AND status = %s"
        params.append(status)
        
    sql += " ORDER BY created_at DESC"
    if limit:
        sql += f" LIMIT {int(limit)}"
        
    with get_connection() as conn:
        rows = conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]

def get_quotation(quotation_no: str) -> Optional[Dict[str, Any]]:
    """Retrieve a single quotation by number."""
    _ensure_table()
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM quotations WHERE quotation_no=%s", (quotation_no,)).fetchone()
        return dict(row) if row else None

def create_quotation(data: Dict[str, Any]) -> str:
    """Create a new quotation record."""
    _ensure_table()
    # Logic สำหรับ gen เลขที่เอกสารจะถูกเรียกที่นี่หรือก่อนเรียกฟังก์ชันนี้
    quotation_no = data.get("quotation_no")
    with get_connection() as conn:
        conn.execute("""
            INSERT INTO quotations (quotation_no, customer_id, customer_name, issue_date, valid_until, subtotal, vat_amount, total_amount, status, remark, created_by)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            quotation_no, data.get("customer_id"), data.get("customer_name"),
            data.get("issue_date"), data.get("valid_until"), data.get("subtotal"),
            data.get("vat_amount"), data.get("total_amount"), data.get("status", "Draft"),
            data.get("remark"), data.get("created_by")
        ))
    return quotation_no