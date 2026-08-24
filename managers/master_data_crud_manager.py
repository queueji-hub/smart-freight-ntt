"""Canonical master-data CRUD for ports and business parties."""
from __future__ import annotations
from typing import Any, Dict, List, Optional
from database.connection import get_connection
from managers.tenant_context import get_current_tenant_id


def _tenant(user: Optional[Dict[str, Any]] = None) -> str:
    return str((user or {}).get("tenant_id") or get_current_tenant_id() or "default")


def _scalar(row: Any) -> Any:
    if not row:
        return None
    if isinstance(row, dict) or hasattr(row, "values"):
        vals = list(row.values())
        return vals[0] if vals else None
    if isinstance(row, (list, tuple)):
        return row[0]
    return row


def list_ports(active_only: bool = True) -> List[Dict[str, Any]]:
    tenant = _tenant()
    where = "WHERE tenant_id=%s"
    params: list[Any] = [tenant]
    if active_only:
        where += " AND is_active=TRUE"
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(f"SELECT * FROM ports {where} ORDER BY port_code", params)
        return [dict(r) for r in cur.fetchall()]


def upsert_port(data: Dict[str, Any], user: Optional[Dict[str, Any]] = None) -> int:
    tenant = _tenant(user)
    name = str(data.get("port_name") or "").strip()
    if not name:
        raise ValueError("Port name is required.")

    code = str(data.get("port_code") or "").strip().upper()
    with get_connection() as conn, conn.cursor() as cur:
        if not code or len(code) != 5:
            cur.execute("SELECT MAX(id) FROM ports WHERE tenant_id=%s", (tenant,))
            max_v = _scalar(cur.fetchone())
            max_id = (int(max_v) if max_v is not None else 0) + 1
            code = f"P{max_id:04d}"

        port_id = data.get("id")
        if not port_id:
            cur.execute("SELECT id FROM ports WHERE tenant_id=%s AND port_code=%s LIMIT 1", (tenant, code))
            existing = cur.fetchone()
            if existing:
                port_id = existing["id"] if isinstance(existing, dict) or hasattr(existing, "keys") else existing[0]

        if port_id:
            cur.execute("""UPDATE ports SET port_code=%s, unlocode=%s, port_name=%s, city=%s,
                country_code=%s, country_name=%s, timezone=%s, port_type=%s, is_active=%s, remarks=%s,
                updated_at=CURRENT_TIMESTAMP WHERE id=%s AND tenant_id=%s""",
                (code, data.get("unlocode") or code, name, data.get("city"), data.get("country_code"), data.get("country_name"),
                 data.get("timezone"), data.get("port_type") or "PORT", bool(data.get("is_active", True)), data.get("remarks"), port_id, tenant))
            port_id = int(port_id)
        else:
            cur.execute("""INSERT INTO ports
                (tenant_id, port_code, unlocode, port_name, city, country_code, country_name, timezone, port_type, is_active, remarks)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id""",
                (tenant, code, data.get("unlocode") or code, name, data.get("city"), data.get("country_code"), data.get("country_name"),
                 data.get("timezone"), data.get("port_type") or "PORT", bool(data.get("is_active", True)), data.get("remarks")))
            row = cur.fetchone()
            port_id = int(row["id"] if isinstance(row, dict) or hasattr(row, "keys") else row[0])
        conn.commit()
        return port_id


def list_parties(role_type: Optional[str] = None, active_only: bool = True) -> List[Dict[str, Any]]:
    tenant = _tenant()
    joins = ""
    where = "p.tenant_id=%s"
    params: list[Any] = [tenant]
    if role_type:
        joins = "JOIN party_roles pr ON pr.party_id=p.id AND pr.tenant_id=p.tenant_id"
        where += " AND pr.role_type=%s AND pr.is_active=TRUE"
        params.append(role_type)
    if active_only:
        where += " AND p.is_active=TRUE"
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(f"SELECT DISTINCT p.* FROM business_parties p {joins} WHERE {where} ORDER BY p.party_code", params)
        rows = [dict(r) for r in cur.fetchall()]
        for r in rows:
            pid = r.get("id")
            if pid:
                cur.execute("SELECT role_type FROM party_roles WHERE party_id=%s AND tenant_id=%s AND is_active=TRUE", (pid, tenant))
                r["roles"] = [x["role_type"] if isinstance(x, dict) or hasattr(x, "keys") else x[0] for x in cur.fetchall()]
                cur.execute("SELECT * FROM party_finance WHERE party_id=%s AND tenant_id=%s LIMIT 1", (pid, tenant))
                fin = cur.fetchone()
                if fin:
                    fdict = dict(fin)
                    r["credit_limit"] = fdict.get("credit_limit")
                    r["credit_currency"] = fdict.get("credit_currency")
                    r["credit_days"] = fdict.get("credit_days")
                    r["payment_term_code"] = fdict.get("payment_term_code")
                    r["bank_name"] = fdict.get("bank_name")
                    r["bank_account_name"] = fdict.get("bank_account_name")
                    r["bank_account_no"] = fdict.get("bank_account_no")
                    r["swift_code"] = fdict.get("swift_code")
        return rows


def upsert_party(data: Dict[str, Any], roles: List[str], finance: Optional[Dict[str, Any]] = None, user: Optional[Dict[str, Any]] = None) -> int:
    tenant = _tenant(user)
    legal_name = str(data.get("legal_name") or "").strip()
    if not legal_name:
        raise ValueError("Legal Name is required.")

    code = str(data.get("party_code") or "").strip().upper()
    with get_connection() as conn, conn.cursor() as cur:
        if not code or len(code) != 5:
            cur.execute("SELECT MAX(id) FROM business_parties WHERE tenant_id=%s", (tenant,))
            max_v = _scalar(cur.fetchone())
            max_id = (int(max_v) if max_v is not None else 0) + 1
            code = f"BP{max_id:03d}"

        party_id = data.get("id")
        if not party_id:
            cur.execute("SELECT id FROM business_parties WHERE tenant_id=%s AND party_code=%s LIMIT 1", (tenant, code))
            existing = cur.fetchone()
            if existing:
                party_id = existing["id"] if isinstance(existing, dict) or hasattr(existing, "keys") else existing[0]

        if party_id:
            party_id = int(party_id)
            cur.execute("""UPDATE business_parties SET party_code=%s, legal_name=%s, display_name=%s, short_name=%s,
                tax_id=%s, branch_no=%s, registration_no=%s, billing_address=%s, country_code=%s, phone=%s, email=%s, website=%s,
                is_active=%s, updated_at=CURRENT_TIMESTAMP WHERE id=%s AND tenant_id=%s""",
                (code, legal_name, data.get("display_name") or legal_name, data.get("short_name"), data.get("tax_id"), data.get("branch_no"),
                 data.get("registration_no"), data.get("billing_address"), data.get("country_code"), data.get("phone"), data.get("email"), data.get("website"),
                 bool(data.get("is_active", True)), party_id, tenant))
            cur.execute("DELETE FROM party_roles WHERE party_id=%s AND tenant_id=%s", (party_id, tenant))
        else:
            cur.execute("""INSERT INTO business_parties
                (tenant_id, party_code, legal_name, display_name, short_name, tax_id, branch_no, registration_no, billing_address, country_code, phone, email, website, is_active)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id""",
                (tenant, code, legal_name, data.get("display_name") or legal_name, data.get("short_name"), data.get("tax_id"), data.get("branch_no"),
                 data.get("registration_no"), data.get("billing_address"), data.get("country_code"), data.get("phone"), data.get("email"), data.get("website"),
                 bool(data.get("is_active", True))))
            row = cur.fetchone()
            party_id = int(row["id"] if isinstance(row, dict) or hasattr(row, "keys") else row[0])

        clean_roles = sorted({str(r).strip().upper() for r in roles if r})
        for role in clean_roles:
            cur.execute("INSERT INTO party_roles (tenant_id, party_id, role_type, is_active) VALUES (%s,%s,%s,TRUE) ON CONFLICT DO NOTHING", (tenant, party_id, role))
        
        # If CUSTOMER role is assigned, sync to customers table
        if "CUSTOMER" in clean_roles:
            try:
                cur.execute("SELECT id FROM customers WHERE tenant_id=%s AND customer_code=%s LIMIT 1", (tenant, code))
                c_row = cur.fetchone()
                cid = c_row["id"] if c_row and (isinstance(c_row, dict) or hasattr(c_row, "keys")) else (c_row[0] if c_row else None)
                if cid:
                    cur.execute("""
                        UPDATE customers SET company_name=%s, display_name=%s, billing_name=%s, tax_id=%s, tel=%s, email=%s, address=%s, billing_address=%s, is_active=%s, updated_at=CURRENT_TIMESTAMP
                        WHERE id=%s AND tenant_id=%s
                    """, (legal_name, data.get("display_name") or legal_name, legal_name, data.get("tax_id"), data.get("phone"), data.get("email"), data.get("billing_address"), data.get("billing_address"), 1 if data.get("is_active", True) else 0, cid, tenant))
                else:
                    cur.execute("""
                        INSERT INTO customers (tenant_id, customer_code, company_name, display_name, billing_name, tax_id, tel, email, address, billing_address, is_active)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, (tenant, code, legal_name, data.get("display_name") or legal_name, legal_name, data.get("tax_id"), data.get("phone"), data.get("email"), data.get("billing_address"), data.get("billing_address"), 1 if data.get("is_active", True) else 0))
            except Exception:
                pass
        if finance is not None:
            cur.execute("""INSERT INTO party_finance_profiles
                (tenant_id, party_id, credit_limit, credit_currency, credit_days, payment_term_code, tax_id, vat_registered, withholding_tax, bank_name, bank_account_name, bank_account_no, swift_code)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT (tenant_id, party_id) DO UPDATE SET credit_limit=EXCLUDED.credit_limit, credit_currency=EXCLUDED.credit_currency,
                credit_days=EXCLUDED.credit_days, payment_term_code=EXCLUDED.payment_term_code, tax_id=EXCLUDED.tax_id,
                vat_registered=EXCLUDED.vat_registered, withholding_tax=EXCLUDED.withholding_tax, bank_name=EXCLUDED.bank_name,
                bank_account_name=EXCLUDED.bank_account_name, bank_account_no=EXCLUDED.bank_account_no, swift_code=EXCLUDED.swift_code""",
                (tenant, party_id, float(finance.get("credit_limit") or 0), finance.get("credit_currency") or "THB", int(finance.get("credit_days") or 0),
                 finance.get("payment_term_code"), finance.get("tax_id") or data.get("tax_id"), bool(finance.get("vat_registered")), bool(finance.get("withholding_tax")),
                 finance.get("bank_name"), finance.get("bank_account_name"), finance.get("bank_account_no"), finance.get("swift_code")))
        conn.commit()
        return party_id


def delete_port(port_id: int, user: Optional[Dict[str, Any]] = None) -> bool:
    """Deletes a port record from ports table."""
    if not port_id:
        return False
    tenant = _tenant(user)
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute("DELETE FROM ports WHERE id=%s AND tenant_id=%s", (int(port_id), tenant))
        conn.commit()
        return True


def delete_party(party_id: int, user: Optional[Dict[str, Any]] = None) -> bool:
    """Deletes a business party record and associated roles/finance profiles."""
    if not party_id:
        return False
    tenant = _tenant(user)
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute("DELETE FROM party_roles WHERE party_id=%s AND tenant_id=%s", (int(party_id), tenant))
        cur.execute("DELETE FROM party_finance_profiles WHERE party_id=%s AND tenant_id=%s", (int(party_id), tenant))
        cur.execute("DELETE FROM business_parties WHERE id=%s AND tenant_id=%s", (int(party_id), tenant))
        conn.commit()
        return True

