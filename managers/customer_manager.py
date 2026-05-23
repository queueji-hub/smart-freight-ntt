from typing import List, Dict, Any, Optional
from database.connection import get_connection

# =========================================================
# LIST CUSTOMERS
# =========================================================

def list_customers() -> List[Dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT *
            FROM customers
            WHERE is_active = 1
            ORDER BY LOWER(company_name) ASC
        """).fetchall()

        return [dict(r) for r in rows]

# =========================================================
# GET CUSTOMER BY ID (MAIN FUNCTION - FIXED)
# =========================================================

def get_customer(customer_id: int) -> Optional[Dict[str, Any]]:
    with get_connection() as conn:
        row = conn.execute("""
            SELECT *
            FROM customers
            WHERE id = %s
        """, (customer_id,)).fetchone()

        if not row:
            return None

        row = dict(row)

        # 🔥 normalize field (แก้ CRM error 'name')
        return {
            "id": row.get("id"),
            "name": row.get("company_name"),   # 👈 FIX: unify UI field
            "company_name": row.get("company_name"),
            "attention": row.get("attention"),
            "tel": row.get("tel"),
            "email": row.get("email", "")
        }

# =========================================================
# SEARCH
# =========================================================

def get_customer_by_name(name: str) -> Optional[Dict[str, Any]]:
    with get_connection() as conn:
        row = conn.execute("""
            SELECT *
            FROM customers
            WHERE company_name ILIKE %s
        """, (name,)).fetchone()

        return dict(row) if row else None


def search_customers(query: str) -> List[Dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT *
            FROM customers
            WHERE company_name ILIKE %s
            LIMIT 10
        """, (f"%{query}%",)).fetchall()

        return [dict(r) for r in rows]

# =========================================================
# CREATE
# =========================================================

def create_customer(data: Dict[str, Any]) -> None:
    with get_connection() as conn:
        conn.execute("""
            INSERT INTO customers (name, company_name, attention, tel)
            VALUES (%s, %s, %s, %s)
        """, (
            data.get("name"),
            data.get("company_name"),
            data.get("attention"),
            data.get("tel")
        ))
        conn.commit()

# =========================================================
# DELETE
# =========================================================

def delete_customer(customer_id: int) -> bool:
    with get_connection() as conn:
        conn.execute("""
            DELETE FROM customers
            WHERE id = %s
        """, (customer_id,))
        conn.commit()
        return True

# =========================================================
# UPDATE
# =========================================================

def update_customer(name: str, data: Dict[str, Any]) -> bool:
    with get_connection() as conn:
        cur = conn.execute("""
            UPDATE customers
            SET company_name=%s,
                attention=%s,
                tel=%s
            WHERE company_name=%s
        """, (
            data.get("company_name"),
            data.get("attention"),
            data.get("tel"),
            name
        ))
        conn.commit()
        return cur.rowcount > 0

# =========================================================
# UPSERT
# =========================================================

def upsert_customer(name: str, attention: str = None, tel: str = None) -> None:
    if not name:
        return

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