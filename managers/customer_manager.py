from managers.tenant_context import get_current_tenant_id
from typing import List, Dict, Any, Optional
from database.connection import get_connection


def list_customers() -> List[Dict[str, Any]]:
    """List active tenant customers across boolean/integer legacy schemas."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT *
                FROM customers
                WHERE LOWER(COALESCE(is_active::text, '0')) IN ('1','true','t')
                  AND tenant_id = %s
                ORDER BY LOWER(company_name) ASC
            """, (get_current_tenant_id(),))
            return [dict(r) for r in cur.fetchall()]


def get_customer(customer_id: int) -> Optional[Dict[str, Any]]:
    if not customer_id:
        return None
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM customers WHERE id=%s AND tenant_id=%s", (customer_id, get_current_tenant_id()))
            row = cur.fetchone()
            return dict(row) if row else None


def get_customer_by_name(name: str) -> Optional[Dict[str, Any]]:
    if not name:
        return None
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT * FROM customers
                WHERE company_name ILIKE %s AND tenant_id=%s
                LIMIT 1
            """, (name.strip(), get_current_tenant_id()))
            row = cur.fetchone()
            return dict(row) if row else None


def search_customers(query: str) -> List[Dict[str, Any]]:
    if not query:
        return []
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT * FROM customers
                WHERE company_name ILIKE %s AND tenant_id=%s
                ORDER BY company_name
                LIMIT 10
            """, (f"%{query.strip()}%", get_current_tenant_id()))
            return [dict(r) for r in cur.fetchall()]


def create_customer(data: Dict[str, Any]) -> bool:
    if not data or not data.get("company_name"):
        return False
    tenant_id = get_current_tenant_id()
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO customers (
                    company_name, contact_person, tel, email,
                    address, tax_id, credit_terms_days, notes, is_active, tenant_id
                ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                RETURNING id
            """, (
                data.get("company_name"), data.get("contact_person"), data.get("tel"), data.get("email"),
                data.get("address"), data.get("tax_id"), data.get("credit_terms_days", 30), data.get("notes"),
                1 if data.get("is_active", True) else 0, tenant_id,
            ))
            customer_id = cur.fetchone()["id"]
            conn.commit()
            return customer_id


def update_customer(company_name: str, data: Dict[str, Any]) -> bool:
    if not company_name:
        return False
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE customers
                SET company_name=%s, contact_person=%s, tel=%s, email=%s,
                    address=%s, tax_id=%s, credit_terms_days=%s, notes=%s,
                    updated_at=CURRENT_TIMESTAMP
                WHERE company_name=%s AND tenant_id=%s
            """, (
                data.get("company_name"), data.get("contact_person"), data.get("tel"), data.get("email"),
                data.get("address"), data.get("tax_id"), data.get("credit_terms_days", 30), data.get("notes"),
                company_name, get_current_tenant_id(),
            ))
            conn.commit()
            return cur.rowcount > 0


def upsert_customer(company_name: str, contact_person: str = None, tel: str = None) -> bool:
    if not company_name:
        return False
    company_name = company_name.strip()
    tenant_id = get_current_tenant_id()
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM customers WHERE company_name=%s AND tenant_id=%s", (company_name, tenant_id))
            row = cur.fetchone()
            if row:
                cur.execute("""
                    UPDATE customers
                    SET contact_person=%s, tel=%s, updated_at=CURRENT_TIMESTAMP
                    WHERE company_name=%s AND tenant_id=%s
                """, (contact_person, tel, company_name, tenant_id))
            else:
                cur.execute("""
                    INSERT INTO customers(company_name,contact_person,tel,is_active,tenant_id)
                    VALUES(%s,%s,%s,TRUE,%s)
                """, (company_name, contact_person, tel, tenant_id))
            conn.commit()
            return True


def delete_customer(customer_id: int) -> bool:
    if not customer_id:
        return False
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM customers WHERE id=%s AND tenant_id=%s", (customer_id, get_current_tenant_id()))
            conn.commit()
            return cur.rowcount > 0
