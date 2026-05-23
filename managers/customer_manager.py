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
# GET CUSTOMER BY ID
# =========================================================

def get_customer(customer_id: int) -> Optional[Dict[str, Any]]:
    with get_connection() as conn:
        row = conn.execute("""
            SELECT *
            FROM customers
            WHERE id = %s
        """, (customer_id,)).fetchone()

        return dict(row) if row else None


# =========================================================
# SEARCH BY NAME
# =========================================================

def get_customer_by_name(name: str) -> Optional[Dict[str, Any]]:
    with get_connection() as conn:
        row = conn.execute("""
            SELECT *
            FROM customers
            WHERE company_name ILIKE %s
            LIMIT 1
        """, (name,)).fetchone()

        return dict(row) if row else None


def search_customers(query: str) -> List[Dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT *
            FROM customers
            WHERE company_name ILIKE %s
            ORDER BY company_name
            LIMIT 10
        """, (f"%{query}%",)).fetchall()

        return [dict(r) for r in rows]


# =========================================================
# CREATE CUSTOMER
# =========================================================

def create_customer(data: Dict[str, Any]) -> None:
    with get_connection() as conn:
        conn.execute("""
            INSERT INTO customers (
                company_name,
                contact_person,
                tel,
                email,
                address,
                tax_id,
                credit_terms_days,
                notes,
                is_active
            )
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, (
            data.get("company_name"),
            data.get("contact_person"),
            data.get("tel"),
            data.get("email"),
            data.get("address"),
            data.get("tax_id"),
            data.get("credit_terms_days", 30),
            data.get("notes"),
            data.get("is_active", 1)
        ))
        conn.commit()


# =========================================================
# UPDATE CUSTOMER
# =========================================================

def update_customer(company_name: str, data: Dict[str, Any]) -> bool:
    with get_connection() as conn:
        cur = conn.execute("""
            UPDATE customers
            SET company_name=%s,
                contact_person=%s,
                tel=%s,
                email=%s,
                address=%s,
                tax_id=%s,
                credit_terms_days=%s,
                notes=%s,
                updated_at=CURRENT_TIMESTAMP
            WHERE company_name=%s
        """, (
            data.get("company_name"),
            data.get("contact_person"),
            data.get("tel"),
            data.get("email"),
            data.get("address"),
            data.get("tax_id"),
            data.get("credit_terms_days"),
            data.get("notes"),
            company_name
        ))

        conn.commit()
        return cur.rowcount > 0


# =========================================================
# UPSERT (FIXED - SAFE WITHOUT DB CONSTRAINT ERROR)
# =========================================================

def upsert_customer(company_name: str, contact_person: str = None, tel: str = None) -> None:
    if not company_name:
        return

    with get_connection() as conn:

        # STEP 1: check existing
        row = conn.execute("""
            SELECT id
            FROM customers
            WHERE company_name = %s
        """, (company_name,)).fetchone()

        if row:
            # UPDATE
            conn.execute("""
                UPDATE customers
                SET contact_person = %s,
                    tel = %s,
                    updated_at = CURRENT_TIMESTAMP
                WHERE company_name = %s
            """, (contact_person, tel, company_name))
        else:
            # INSERT
            conn.execute("""
                INSERT INTO customers (
                    company_name,
                    contact_person,
                    tel,
                    is_active
                )
                VALUES (%s, %s, %s, 1)
            """, (company_name, contact_person, tel))

        conn.commit()


# =========================================================
# DELETE CUSTOMER
# =========================================================

def delete_customer(customer_id: int) -> bool:
    with get_connection() as conn:
        conn.execute("""
            DELETE FROM customers
            WHERE id = %s
        """, (customer_id,))
        conn.commit()
        return True