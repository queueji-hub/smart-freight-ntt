from typing import List, Dict, Any, Optional
from database.connection import get_connection

def list_customers() -> List[Dict[str, Any]]:
    """Retrieve all active customers."""
    with get_connection() as conn:
        return list(conn.execute("""
            SELECT * FROM customers 
            WHERE is_active=1 
            ORDER BY LOWER(company_name) ASC
        """).fetchall())

def get_customer_by_name(name: str) -> Optional[Dict[str, Any]]:
    """Get customer details by name."""
    with get_connection() as conn:
        return conn.execute("SELECT * FROM customers WHERE name ILIKE %s", (name,)).fetchone()

def search_customers(query: str) -> List[Dict[str, Any]]:
    """Search customers by name."""
    with get_connection() as conn:
        return list(conn.execute(
            "SELECT * FROM customers WHERE name ILIKE %s LIMIT 10", 
            (f"%{query}%",)
        ).fetchall())

def create_customer(data: Dict[str, Any]) -> None:
    """Create a new customer."""
    with get_connection() as conn:
        conn.execute("""
            INSERT INTO customers (name, company_name, attention, tel)
            VALUES (%s, %s, %s, %s)
        """, (data["name"], data.get("company_name"), data.get("attention"), data.get("tel")))
        conn.commit()

def delete_customer(customer_id: int) -> bool:
    """Delete a customer record by ID."""
    with get_connection() as conn:
        conn.execute("DELETE FROM customers WHERE id=%s", (customer_id,))
        conn.commit()
        return True

def update_customer(name: str, data: Dict[str, Any]) -> bool:
    """Update existing customer details."""
    with get_connection() as conn:
        cur = conn.execute("""
            UPDATE customers 
            SET company_name=%s, attention=%s, tel=%s 
            WHERE name=%s
        """, (data.get("company_name"), data.get("attention"), data.get("tel"), name))
        conn.commit()
        return cur.rowcount > 0

def upsert_customer(name: str, attention: str = None, tel: str = None) -> None:
    """Insert or update customer details by name."""
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
        conn.commit()

def get_customer(customer_id):
    """
    Get single customer by ID
    """

    with get_connection() as conn:

        result = conn.execute(
            """
            SELECT *
            FROM customers
            WHERE id = %s
            """,
            (customer_id,)
        ).fetchone()

        return dict(result) if result else None