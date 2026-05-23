"""Customer management operations."""
from typing import List, Dict, Any, Optional
from database.connection import get_connection

def _ensure_table():
    """Ensure customers table exists."""
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS customers (
                id SERIAL PRIMARY KEY,
                name TEXT UNIQUE NOT NULL,
                attention TEXT,
                tel TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

def list_customers() -> List[Dict[str, Any]]:
    """Retrieve all customers."""
    _ensure_table()
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM customers ORDER BY name ASC").fetchall()
        return [dict(r) for r in rows]

def get_customer_by_name(name: str) -> Optional[Dict[str, Any]]:
    """Get customer details by name."""
    _ensure_table()
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM customers WHERE name = %s", (name,)).fetchone()
        return dict(row) if row else None

def search_customers(query: str) -> List[Dict[str, Any]]:
    """Search customers by name."""
    _ensure_table()
    with get_connection() as conn:
        search_term = f"%{query}%"
        rows = conn.execute("SELECT * FROM customers WHERE name ILIKE %s LIMIT 10", (search_term,)).fetchall()
        return [dict(r) for r in rows]

def upsert_customer(name: str, attention: str = None, tel: str = None) -> None:
    """Insert or update customer details."""
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