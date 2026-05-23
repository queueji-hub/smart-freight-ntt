"""Customer database CRUD."""
from typing import List, Dict, Any, Optional
from database.connection import get_connection

def _ensure_table():
    """Ensure the customers table exists."""
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS customers (
                id SERIAL PRIMARY KEY,
                company_name TEXT UNIQUE NOT NULL,
                contact_person TEXT,
                tel TEXT,
                email TEXT,
                address TEXT,
                tax_id TEXT,
                credit_terms_days INTEGER DEFAULT 30,
                notes TEXT,
                is_active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

def upsert_customer(company_name: str, attention: str = None,
                    tel: str = None, email: str = None, address: str = None,
                    tax_id: str = None, credit_terms_days: int = None) -> Optional[int]:
    """Insert or update a customer based on company_name (case-insensitive)."""
    _ensure_table()
    if not company_name or not company_name.strip():
        return None
    
    company_name = company_name.strip()
    
    with get_connection() as conn:
        existing = conn.execute(
            "SELECT id, contact_person, tel, email, address, tax_id, credit_terms_days "
            "FROM customers WHERE LOWER(company_name) = LOWER(%s)",
            (company_name,)
        ).fetchone()
        
        if existing:
            updates = []
            params = []
            if attention and not existing["contact_person"]:
                updates.append("contact_person=%s"); params.append(attention)
            if tel and not existing["tel"]:
                updates.append("tel=%s"); params.append(tel)
            if email and not existing["email"]:
                updates.append("email=%s"); params.append(email)
            if address and not existing["address"]:
                updates.append("address=%s"); params.append(address)
            if tax_id and not existing["tax_id"]:
                updates.append("tax_id=%s"); params.append(tax_id)
            if credit_terms_days is not None and not existing["credit_terms_days"]:
                updates.append("credit_terms_days=%s"); params.append(credit_terms_days)
            
            if updates:
                updates.append("updated_at=CURRENT_TIMESTAMP")
                params.append(existing["id"])
                conn.execute(
                    f"UPDATE customers SET {', '.join(updates)} WHERE id=%s",
                    params
                )
            return existing["id"]
        
        cur = conn.execute(
            "INSERT INTO customers (company_name, contact_person, tel, email, "
            "address, tax_id, credit_terms_days) VALUES (%s,%s,%s,%s,%s,%s,%s) RETURNING id",
            (company_name, attention, tel, email, address, tax_id, credit_terms_days or 30)
        )
        row = cur.fetchone()
        return row[0] if row else None

def create_customer(data: Dict[str, Any]) -> int:
    _ensure_table()
    with get_connection() as conn:
        cur = conn.execute(
            "INSERT INTO customers (company_name, contact_person, tel, email, "
            "address, tax_id, credit_terms_days, notes) VALUES (%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id",
            (data.get("company_name"), data.get("contact_person"),
             data.get("tel"), data.get("email"), data.get("address"),
             data.get("tax_id"), data.get("credit_terms_days", 30),
             data.get("notes"))
        )
        row = cur.fetchone()
        return row[0] if row else None

def update_customer(customer_id: int, data: Dict[str, Any]) -> bool:
    _ensure_table()
    fields = ["company_name", "contact_person", "tel", "email", "address",
              "tax_id", "credit_terms_days", "notes", "is_active"]
    sets, params = [], []
    for f in fields:
        if f in data:
            sets.append(f"{f}=%s")
            params.append(data[f])
    if not sets:
        return False
    sets.append("updated_at=CURRENT_TIMESTAMP")
    params.append(customer_id)
    with get_connection() as conn:
        conn.execute(f"UPDATE customers SET {', '.join(sets)} WHERE id=%s", params)
    return True

def delete_customer(customer_id: int) -> bool:
    _ensure_table()
    with get_connection() as conn:
        conn.execute("UPDATE customers SET is_active=0 WHERE id=%s", (customer_id,))
    return True

def list_customers(active_only: bool = True) -> List[Dict[str, Any]]:
    _ensure_table()
    sql = "SELECT * FROM customers"
    if active_only:
        sql += " WHERE is_active=1"
    sql += " ORDER BY LOWER(company_name)"
    with get_connection() as conn:
        rows = conn.execute(sql).fetchall()
        return [dict(r) for r in rows]

def search_customers(query: str, limit: int = 20) -> List[Dict[str, Any]]:
    _ensure_table()
    if not query or not query.strip():
        return list_customers()[:limit]
    pattern = f"%{query.strip()}%"
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM customers WHERE company_name ILIKE %s "
            "AND is_active=1 ORDER BY LOWER(company_name) LIMIT %s",
            (pattern, limit)
        ).fetchall()
        return [dict(r) for r in rows]

def get_customer(customer_id: int) -> Optional[Dict[str, Any]]:
    _ensure_table()
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM customers WHERE id=%s", (customer_id,)).fetchone()
        return dict(row) if row else None