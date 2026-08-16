"""Tenant-safe Customer Master CRUD and credit-control helpers."""
from __future__ import annotations
from datetime import date
from typing import Any, Dict, List, Optional
from database.connection import get_connection
from managers.tenant_context import get_current_tenant_id


def _tenant(user: Optional[Dict[str, Any]] = None) -> str:
    return str((user or {}).get("tenant_id") or get_current_tenant_id() or "default")


def list_customers(active_only: bool = False, user: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    tenant = _tenant(user)
    where = "WHERE tenant_id=%s"
    params: list[Any] = [tenant]
    if active_only:
        where += " AND is_active=TRUE"
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(f"SELECT * FROM customers {where} ORDER BY customer_code, company_name", params)
        return [dict(r) for r in cur.fetchall()]


def save_customer(data: Dict[str, Any], user: Optional[Dict[str, Any]] = None) -> int:
    tenant = _tenant(user)
    code = str(data.get("customer_code") or "").strip().upper()
    company = str(data.get("company_name") or "").strip()
    if len(code) != 5:
        raise ValueError("Customer Code must be exactly 5 characters.")
    if not company:
        raise ValueError("Company Name is required.")
    with get_connection() as conn, conn.cursor() as cur:
        values = (
            code, company, data.get("display_name") or company, data.get("billing_name") or company,
            data.get("contact_person"), data.get("tel"), data.get("email"), data.get("address"),
            data.get("billing_address") or data.get("address"), data.get("billing_country_code"),
            data.get("tax_id"), float(data.get("credit_limit") or 0), data.get("credit_currency") or "THB",
            data.get("payment_term_code"), data.get("credit_status") or "NORMAL", bool(data.get("credit_hold")),
            bool(data.get("is_active", True)), data.get("updated_by") or (user or {}).get("username"),
        )
        if data.get("id"):
            customer_id = int(data["id"])
            cur.execute("""UPDATE customers SET customer_code=%s, company_name=%s, display_name=%s, billing_name=%s,
                contact_person=%s, tel=%s, email=%s, address=%s, billing_address=%s, billing_country_code=%s,
                tax_id=%s, credit_limit=%s, credit_currency=%s, payment_term_code=%s, credit_status=%s, credit_hold=%s,
                is_active=%s, updated_by=%s, updated_at=CURRENT_TIMESTAMP
                WHERE id=%s AND tenant_id=%s""", values + (customer_id, tenant))
        else:
            cur.execute("""INSERT INTO customers
                (tenant_id, customer_code, company_name, display_name, billing_name, contact_person, tel, email, address,
                 billing_address, billing_country_code, tax_id, credit_limit, credit_currency, payment_term_code,
                 credit_status, credit_hold, is_active, updated_by)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id""",
                (tenant,) + values)
            customer_id = int(cur.fetchone()[0])
        conn.commit()
        return customer_id


def get_credit_snapshot(customer_id: int, user: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    tenant = _tenant(user)
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute("SELECT credit_limit, credit_currency, credit_days, payment_term_code, credit_status, credit_hold FROM customers WHERE id=%s AND tenant_id=%s", (customer_id, tenant))
        row = cur.fetchone()
        if not row:
            raise ValueError("Customer not found in current tenant.")
        d = dict(row) if hasattr(row, "keys") else dict(zip(["credit_limit","credit_currency","credit_days","payment_term_code","credit_status","credit_hold"], row))
        cur.execute("SELECT COALESCE(SUM(outstanding),0) AS outstanding, COALESCE(SUM(CASE WHEN outstanding>0 AND due_date < CURRENT_DATE THEN outstanding ELSE 0 END),0) AS overdue FROM invoices WHERE tenant_id=%s AND customer_id=%s", (tenant, customer_id))
        ar = cur.fetchone()
        if hasattr(ar, "keys"):
            ar = dict(ar)
        else:
            ar = {"outstanding": ar[0], "overdue": ar[1]}
    limit = float(d.get("credit_limit") or 0)
    outstanding = float(ar.get("outstanding") or 0)
    available = limit - outstanding if limit > 0 else None
    overdue = float(ar.get("overdue") or 0)
    status = "CREDIT HOLD" if d.get("credit_hold") else ("OVER LIMIT" if available is not None and available < 0 else ("OVERDUE" if overdue > 0 else "NORMAL"))
    return {**d, "outstanding": outstanding, "overdue": overdue, "available_credit": available, "control_status": status, "checked_at": date.today().isoformat()}
