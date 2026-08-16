"""Canonical master-data CRUD for ports and business parties."""
from __future__ import annotations
from typing import Any, Dict, List, Optional
from database.connection import get_connection
from managers.tenant_context import get_current_tenant_id


def _tenant(user: Optional[Dict[str, Any]] = None) -> str:
    return str((user or {}).get("tenant_id") or get_current_tenant_id() or "default")


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
    code = str(data.get("port_code") or "").strip().upper()
    name = str(data.get("port_name") or "").strip()
    if len(code) != 5 or not name:
        raise ValueError("Port code must be exactly 5 characters and port name is required.")
    with get_connection() as conn, conn.cursor() as cur:
        if data.get("id"):
            cur.execute("""UPDATE ports SET port_code=%s, unlocode=%s, port_name=%s, city=%s,
                country_code=%s, country_name=%s, timezone=%s, port_type=%s, is_active=%s, remarks=%s,
                updated_at=CURRENT_TIMESTAMP WHERE id=%s AND tenant_id=%s""",
                (code, data.get("unlocode"), name, data.get("city"), data.get("country_code"), data.get("country_name"),
                 data.get("timezone"), data.get("port_type") or "PORT", bool(data.get("is_active", True)), data.get("remarks"), data["id"], tenant))
            port_id = int(data["id"])
        else:
            cur.execute("""INSERT INTO ports
                (tenant_id, port_code, unlocode, port_name, city, country_code, country_name, timezone, port_type, is_active, remarks)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id""",
                (tenant, code, data.get("unlocode") or code, name, data.get("city"), data.get("country_code"), data.get("country_name"),
                 data.get("timezone"), data.get("port_type") or "PORT", bool(data.get("is_active", True)), data.get("remarks")))
            port_id = int(cur.fetchone()[0])
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
        return [dict(r) for r in cur.fetchall()]


def upsert_party(data: Dict[str, Any], roles: List[str], finance: Optional[Dict[str, Any]] = None, user: Optional[Dict[str, Any]] = None) -> int:
    tenant = _tenant(user)
    code = str(data.get("party_code") or "").strip().upper()
    legal_name = str(data.get("legal_name") or "").strip()
    if len(code) != 5 or not legal_name:
        raise ValueError("Party code must be exactly 5 characters and legal name is required.")
    with get_connection() as conn, conn.cursor() as cur:
        if data.get("id"):
            party_id = int(data["id"])
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
            party_id = int(cur.fetchone()[0])
        for role in sorted({str(r).strip().upper() for r in roles if r}):
            cur.execute("INSERT INTO party_roles (tenant_id, party_id, role_type, is_active) VALUES (%s,%s,%s,TRUE) ON CONFLICT DO NOTHING", (tenant, party_id, role))
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
