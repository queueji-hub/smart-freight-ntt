"""Tenant-safe Customer Master CRUD and credit-control helpers with Business Party unification."""
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
        where += " AND COALESCE(is_active, 1) = 1"
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(f"SELECT * FROM customers {where} ORDER BY customer_code, company_name", params)
        cust_rows = [dict(r) for r in cur.fetchall()]

        # Unify with business_parties where role is CUSTOMER
        try:
            cur.execute("""
                SELECT p.*, pf.credit_limit, pf.credit_currency, pf.credit_days, pf.payment_term_code
                FROM business_parties p
                JOIN party_roles pr ON pr.party_id=p.id AND pr.tenant_id=p.tenant_id
                LEFT JOIN party_finance_profiles pf ON pf.party_id=p.id AND pf.tenant_id=p.tenant_id
                WHERE p.tenant_id=%s AND pr.role_type='CUSTOMER' AND (p.is_active IS NOT FALSE)
            """, (tenant,))
            party_rows = [dict(r) for r in cur.fetchall()]
            existing_codes = {str(c.get("customer_code") or "").upper() for c in cust_rows}
            existing_names = {str(c.get("company_name") or "").lower() for c in cust_rows}

            for p in party_rows:
                p_code = str(p.get("party_code") or "").upper()
                p_name = str(p.get("legal_name") or p.get("display_name") or "").strip()
                if p_code not in existing_codes and p_name.lower() not in existing_names:
                    cust_rows.append({
                        "id": p.get("id"),
                        "tenant_id": tenant,
                        "customer_code": p_code,
                        "company_name": p_name,
                        "display_name": p.get("display_name") or p_name,
                        "billing_name": p_name,
                        "contact_person": "",
                        "tel": p.get("phone") or "",
                        "email": p.get("email") or "",
                        "address": p.get("billing_address") or "",
                        "billing_address": p.get("billing_address") or "",
                        "tax_id": p.get("tax_id") or "",
                        "credit_limit": p.get("credit_limit") or 0.0,
                        "credit_currency": p.get("credit_currency") or "THB",
                        "credit_days": p.get("credit_days") or 30,
                        "payment_term_code": p.get("payment_term_code") or "Net 30",
                        "credit_status": "NORMAL",
                        "credit_hold": False,
                        "is_active": bool(p.get("is_active", True)),
                    })
        except Exception:
            pass

        return cust_rows


def _scalar(row: Any) -> Any:
    if not row:
        return None
    if isinstance(row, dict) or hasattr(row, "values"):
        vals = list(row.values())
        return vals[0] if vals else None
    if isinstance(row, (list, tuple)):
        return row[0]
    return row


def save_customer(data: Dict[str, Any], user: Optional[Dict[str, Any]] = None) -> int:
    tenant = _tenant(user)
    company = str(data.get("company_name") or "").strip()
    if not company:
        raise ValueError("Company Name is required.")

    code = str(data.get("customer_code") or "").strip().upper()

    with get_connection() as conn, conn.cursor() as cur:
        # Auto-generate customer code if blank or invalid length
        if not code or len(code) != 5:
            cur.execute("SELECT MAX(id) FROM customers WHERE tenant_id=%s", (tenant,))
            max_v = _scalar(cur.fetchone())
            max_id = (int(max_v) if max_v is not None else 0) + 1
            code = f"C{max_id:04d}"

        values = (
            code, company, data.get("display_name") or company, data.get("billing_name") or company,
            data.get("contact_person"), data.get("tel"), data.get("email"), data.get("address"),
            data.get("billing_address") or data.get("address"), data.get("billing_country_code"),
            data.get("tax_id"), float(data.get("credit_limit") or 0), data.get("credit_currency") or "THB",
            data.get("payment_term_code"), data.get("credit_status") or "NORMAL",
            bool(data.get("credit_hold")),
            1 if data.get("is_active", True) else 0,
            data.get("updated_by") or (user or {}).get("username"),
        )

        customer_id = data.get("id")
        if not customer_id:
            cur.execute("SELECT id FROM customers WHERE tenant_id=%s AND customer_code=%s LIMIT 1", (tenant, code))
            existing = cur.fetchone()
            if existing:
                customer_id = existing["id"] if isinstance(existing, dict) or hasattr(existing, "keys") else existing[0]

        if customer_id:
            customer_id = int(customer_id)
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
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id""",
                (tenant,) + values)
            row = cur.fetchone()
            customer_id = int(row["id"] if isinstance(row, dict) or hasattr(row, "keys") else row[0])

        # Mirror/unify into business_parties with role 'CUSTOMER'
        try:
            cur.execute("SELECT id FROM business_parties WHERE tenant_id=%s AND party_code=%s LIMIT 1", (tenant, code))
            bp = cur.fetchone()
            bp_id = bp["id"] if bp and (isinstance(bp, dict) or hasattr(bp, "keys")) else (bp[0] if bp else None)
            if bp_id:
                cur.execute("""
                    UPDATE business_parties
                    SET legal_name=%s, display_name=%s, tax_id=%s, phone=%s, email=%s, billing_address=%s, is_active=%s, updated_at=CURRENT_TIMESTAMP
                    WHERE id=%s AND tenant_id=%s
                """, (company, data.get("display_name") or company, data.get("tax_id"), data.get("tel"), data.get("email"), data.get("billing_address") or data.get("address"), bool(data.get("is_active", True)), bp_id, tenant))
            else:
                cur.execute("""
                    INSERT INTO business_parties (tenant_id, party_code, legal_name, display_name, tax_id, phone, email, billing_address, is_active)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id
                """, (tenant, code, company, data.get("display_name") or company, data.get("tax_id"), data.get("tel"), data.get("email"), data.get("billing_address") or data.get("address"), bool(data.get("is_active", True))))
                bp_row = cur.fetchone()
                bp_id = bp_row["id"] if isinstance(bp_row, dict) or hasattr(bp_row, "keys") else bp_row[0]

            # Ensure role CUSTOMER
            cur.execute("INSERT INTO party_roles (tenant_id, party_id, role_type, is_active) VALUES (%s, %s, 'CUSTOMER', TRUE) ON CONFLICT DO NOTHING", (tenant, bp_id))
        except Exception:
            pass

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
