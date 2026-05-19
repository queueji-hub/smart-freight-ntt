"""Customer database — auto-collected from quotations."""
from typing import List, Dict, Any, Optional
from database.connection import get_connection


def upsert_customer(company_name: str, attention: str = None,
                    tel: str = None) -> Optional[int]:
    """Insert or update a customer based on company_name (case-insensitive).
    Returns the customer id."""
    if not company_name or not company_name.strip():
        return None
    
    company_name = company_name.strip()
    
    with get_connection() as conn:
        # Case-insensitive lookup
        existing = conn.execute(
            "SELECT id, contact_person, tel FROM customers "
            "WHERE LOWER(company_name) = LOWER(?)",
            (company_name,)
        ).fetchone()
        
        if existing:
            # Update only if new info is provided and old is empty
            updates = []
            params = []
            if attention and not existing["contact_person"]:
                updates.append("contact_person=?")
                params.append(attention)
            if tel and not existing["tel"]:
                updates.append("tel=?")
                params.append(tel)
            
            if updates:
                params.append(existing["id"])
                conn.execute(
                    f"UPDATE customers SET {', '.join(updates)} WHERE id=?",
                    params
                )
            return existing["id"]
        
        # Insert new
        cur = conn.execute(
            "INSERT INTO customers (company_name, contact_person, tel) "
            "VALUES (?, ?, ?)",
            (company_name, attention, tel)
        )
        return cur.lastrowid


def list_customers() -> List[Dict[str, Any]]:
    """Return all customers ordered alphabetically."""
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT id, company_name, contact_person, tel FROM customers "
            "ORDER BY company_name COLLATE NOCASE"
        ).fetchall()
        return [dict(r) for r in rows]


def search_customers(query: str) -> List[Dict[str, Any]]:
    """Search customers where company_name contains query (case-insensitive)."""
    if not query or not query.strip():
        return list_customers()
    
    pattern = f"%{query.strip()}%"
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT id, company_name, contact_person, tel FROM customers "
            "WHERE company_name LIKE ? COLLATE NOCASE "
            "ORDER BY company_name COLLATE NOCASE LIMIT 20",
            (pattern,)
        ).fetchall()
        return [dict(r) for r in rows]


def get_customer_by_name(name: str) -> Optional[Dict[str, Any]]:
    """Get a customer by exact (case-insensitive) company_name."""
    if not name:
        return None
    with get_connection() as conn:
        row = conn.execute(
            "SELECT id, company_name, contact_person, tel FROM customers "
            "WHERE LOWER(company_name) = LOWER(?)",
            (name.strip(),)
        ).fetchone()
        return dict(row) if row else None


def backfill_from_quotations() -> int:
    """One-time: extract customer info from existing quotations."""
    inserted = 0
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT DISTINCT customer_name, attention, tel FROM quotations "
            "WHERE customer_name IS NOT NULL AND customer_name != ''"
        ).fetchall()
    
    for row in rows:
        if upsert_customer(row["customer_name"], row["attention"], row["tel"]):
            inserted += 1
    return inserted
