"""Customer database CRUD."""
from typing import List, Dict, Any, Optional
from database.connection import get_connection

def _ensure_table():
    """Ensure customers table exists."""
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS customers (
                id SERIAL PRIMARY KEY,
                name TEXT UNIQUE NOT NULL,
                company_name TEXT,
                attention TEXT,
                tel TEXT,
                is_active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

def list_customers() -> List[Dict[str, Any]]:
    """Retrieve all active customers."""
    _ensure_table()
    with get_connection() as conn:
        sql = """
            SELECT * FROM customers 
            WHERE is_active=1 
            ORDER BY LOWER(company_name) ASC
        """
        rows = conn.execute(sql).fetchall()
        return [dict(r) for r in rows]

def get_customer_by_name(name: str) -> Optional[Dict[str, Any]]:
    """Get customer details by name."""
    _ensure_table()
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM customers WHERE name ILIKE %s", (name,)).fetchone()
        return dict(row) if row else None

def search_customers(query: str) -> List[Dict[str, Any]]:
    """Search customers by name."""
    _ensure_table()
    with get_connection() as conn:
        search_term = f"%{query}%"
        rows = conn.execute("SELECT * FROM customers WHERE name ILIKE %s LIMIT 10", (search_term,)).fetchall()
        return [dict(r) for r in rows]

def create_customer(data: Dict[str, Any]) -> None:
    """Create a new customer."""
    _ensure_table()
    with get_connection() as conn:
        conn.execute("""
            INSERT INTO customers (name, company_name, attention, tel)
            VALUES (%s, %s, %s, %s)
        """, (data["name"], data.get("company_name"), data.get("attention"), data.get("tel")))

def update_customer(name: str, data: Dict[str, Any]) -> bool:
    """Update existing customer details."""
    _ensure_table()
    with get_connection() as conn:
        cur = conn.execute("""
            UPDATE customers 
            SET company_name=%s, attention=%s, tel=%s 
            WHERE name=%s
        """, (data.get("company_name"), data.get("attention"), data.get("tel"), name))
        return cur.rowcount > 0

def upsert_customer(name: str, attention: str = None, tel: str = None) -> None:
    """Insert or update customer details by name."""
    _ensure_table()
    if not name: return
    
    with get_connection() as conn:
        conn.execute("""
            INSERT INTO customers (name, attention, tel)
            VALUES (%s, %s, %s)
            ON CONFLICT (name) 
            DO UPDATE SET 
                attention = EXCLUDED.attention,
                tel = EXCLUDED.tel
        """, (name, attention, tel))