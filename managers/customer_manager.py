"""Customer database CRUD."""

from typing import List, Dict, Any, Optional

from database.connection import get_connection





def upsert_customer(company_name: str, attention: str = None,

                    tel: str = None, email: str = None, address: str = None,

                    tax_id: str = None, credit_terms_days: int = None) -> Optional[int]:

    """Insert or update a customer based on company_name (case-insensitive).

    Returns the customer id."""

    if not company_name or not company_name.strip():

        return None

   

    company_name = company_name.strip()

   

    with get_connection() as conn:

        existing = conn.execute(

            "SELECT id, contact_person, tel, email, address, tax_id, credit_terms_days "

            "FROM customers WHERE LOWER(company_name) = LOWER(?)",

            (company_name,)

        ).fetchone()

       

        if existing:

            updates = []

            params = []

            if attention and not existing["contact_person"]:

                updates.append("contact_person=?"); params.append(attention)

            if tel and not existing["tel"]:

                updates.append("tel=?"); params.append(tel)

            if email and not existing["email"]:

                updates.append("email=?"); params.append(email)

            if address and not existing["address"]:

                updates.append("address=?"); params.append(address)

            if tax_id and not existing["tax_id"]:

                updates.append("tax_id=?"); params.append(tax_id)

            if credit_terms_days is not None and not existing["credit_terms_days"]:

                updates.append("credit_terms_days=?"); params.append(credit_terms_days)

           

            if updates:

                updates.append("updated_at=CURRENT_TIMESTAMP")

                params.append(existing["id"])

                conn.execute(

                    f"UPDATE customers SET {', '.join(updates)} WHERE id=?",

                    params

                )

            return existing["id"]

       

        cur = conn.execute(

            "INSERT INTO customers (company_name, contact_person, tel, email, "

            "address, tax_id, credit_terms_days) VALUES (?,?,?,?,?,?,?)",

            (company_name, attention, tel, email, address, tax_id,

             credit_terms_days or 30)

        )

        return cur.lastrowid





def create_customer(data: Dict[str, Any]) -> int:

    """Create new customer."""

    with get_connection() as conn:

        cur = conn.execute(

            "INSERT INTO customers (company_name, contact_person, tel, email, "

            "address, tax_id, credit_terms_days, notes) VALUES (?,?,?,?,?,?,?,?)",

            (data.get("company_name"), data.get("contact_person"),

             data.get("tel"), data.get("email"), data.get("address"),

             data.get("tax_id"), data.get("credit_terms_days", 30),

             data.get("notes"))

        )

        return cur.lastrowid





def update_customer(customer_id: int, data: Dict[str, Any]) -> bool:

    fields = ["company_name", "contact_person", "tel", "email", "address",

              "tax_id", "credit_terms_days", "notes", "is_active"]

    sets, params = [], []

    for f in fields:

        if f in data:

            sets.append(f"{f}=?"); params.append(data[f])

    if not sets:

        return False

    sets.append("updated_at=CURRENT_TIMESTAMP")

    params.append(customer_id)

    with get_connection() as conn:

        conn.execute(f"UPDATE customers SET {', '.join(sets)} WHERE id=?", params)

    return True





def delete_customer(customer_id: int) -> bool:

    """Soft delete (set is_active=0)."""

    with get_connection() as conn:

        conn.execute("UPDATE customers SET is_active=0 WHERE id=?", (customer_id,))

    return True





def list_customers(active_only: bool = True) -> List[Dict[str, Any]]:

    sql = "SELECT * FROM customers"

    if active_only:

        sql += " WHERE is_active=1"

    sql += " ORDER BY company_name COLLATE NOCASE"

    with get_connection() as conn:

        rows = conn.execute(sql).fetchall()

        return [dict(r) for r in rows]





def search_customers(query: str, limit: int = 20) -> List[Dict[str, Any]]:

    """Case-insensitive partial match on company_name."""

    if not query or not query.strip():

        return list_customers()[:limit]

    pattern = f"%{query.strip()}%"

    with get_connection() as conn:

        rows = conn.execute(

            "SELECT * FROM customers WHERE company_name LIKE ? COLLATE NOCASE "

            "AND is_active=1 ORDER BY company_name COLLATE NOCASE LIMIT ?",

            (pattern, limit)

        ).fetchall()

        return [dict(r) for r in rows]





def get_customer(customer_id: int) -> Optional[Dict[str, Any]]:

    with get_connection() as conn:

        row = conn.execute("SELECT * FROM customers WHERE id=?",

                            (customer_id,)).fetchone()

        return dict(row) if row else None





def get_customer_by_name(name: str) -> Optional[Dict[str, Any]]:

    if not name:

        return None

    with get_connection() as conn:

        row = conn.execute(

            "SELECT * FROM customers WHERE LOWER(company_name)=LOWER(?) AND is_active=1",

            (name.strip(),)

        ).fetchone()

        return dict(row) if row else None 

