from typing import List, Dict, Any, Optional
from database.connection import get_connection
from managers.tenant_context import get_current_tenant_id
from core.audit import log_action

PAYABLE_ROLES = ["VENDOR", "CARRIER", "LINER", "TRANSPORTER", "AGENT", "CO_LOADER", "PORT_OPERATOR", "CUSTOMS_BROKER", "WAREHOUSE"]

def get_vendors() -> List[Dict[str, Any]]:
    """Retrieve all payable parties (Vendors, Carriers, Transporters, Terminals, Agents) from SSoT."""
    tenant_id = get_current_tenant_id()
    with get_connection() as conn:
        with conn.cursor() as cur:
            # 1. Pull from business_parties with payable roles
            try:
                cur.execute("""
                    SELECT p.*, 
                           pf.credit_limit, pf.credit_currency, pf.credit_days, pf.payment_term_code,
                           pf.bank_name, pf.bank_account_name, pf.bank_account_no, pf.swift_code
                    FROM business_parties p
                    LEFT JOIN party_finance_profiles pf ON pf.party_id = p.id AND pf.tenant_id = p.tenant_id
                    WHERE p.tenant_id = %s AND p.is_active = TRUE
                    ORDER BY p.party_code, p.legal_name ASC
                """, (tenant_id,))
                bp_rows = [dict(r) for r in cur.fetchall()]
                
                # Fetch roles for each party
                for bp in bp_rows:
                    pid = bp.get("id")
                    cur.execute("SELECT role_type FROM party_roles WHERE party_id = %s AND tenant_id = %s AND is_active = TRUE", (pid, tenant_id))
                    bp["roles"] = [r["role_type"] if isinstance(r, dict) or hasattr(r, "keys") else r[0] for r in cur.fetchall()]

                # Filter parties that have at least one payable role
                payable_parties = [
                    p for p in bp_rows
                    if any(r in PAYABLE_ROLES for r in p.get("roles", []))
                ]
            except Exception:
                payable_parties = []

            # 2. Pull from vendors table (legacy fallback)
            cur.execute("""
                SELECT * FROM vendors 
                WHERE tenant_id = %s 
                ORDER BY legal_name ASC
            """, (tenant_id,))
            v_rows = [dict(r) for r in cur.fetchall()]

            # Build unified list
            unified: Dict[str, Dict[str, Any]] = {}
            for p in payable_parties:
                code = str(p.get("party_code") or "").upper()
                name = str(p.get("legal_name") or p.get("display_name") or "").strip()
                key = code if code else name.lower()
                unified[key] = {
                    "id": p.get("id"),
                    "party_id": p.get("id"),
                    "vendor_code": code,
                    "party_code": code,
                    "legal_name": p.get("legal_name") or name,
                    "display_name": p.get("display_name") or name,
                    "tax_id": p.get("tax_id") or "",
                    "branch_no": p.get("branch_no") or "00000",
                    "billing_address": p.get("billing_address") or "",
                    "address": p.get("billing_address") or "",
                    "country": p.get("country_code") or "TH",
                    "currency": p.get("credit_currency") or "THB",
                    "status": "Active" if p.get("is_active") else "Inactive",
                    "roles": p.get("roles", ["VENDOR"]),
                    "bank_name": p.get("bank_name") or "",
                    "bank_account_name": p.get("bank_account_name") or "",
                    "bank_account_no": p.get("bank_account_no") or "",
                    "swift_code": p.get("swift_code") or "",
                    "payment_term_code": p.get("payment_term_code") or "Net 30",
                    "credit_days": p.get("credit_days") or 30,
                }

            for v in v_rows:
                code = str(v.get("vendor_code") or "").upper()
                name = str(v.get("legal_name") or "").strip()
                key = code if code else name.lower()
                if key not in unified:
                    unified[key] = {
                        "id": v.get("id"),
                        "vendor_code": code,
                        "party_code": code,
                        "legal_name": name,
                        "display_name": name,
                        "tax_id": v.get("tax_id") or "",
                        "branch_no": "00000",
                        "billing_address": "",
                        "address": "",
                        "country": v.get("country") or "TH",
                        "currency": v.get("currency") or "THB",
                        "status": v.get("status") or "Active",
                        "roles": ["VENDOR"],
                        "bank_name": "",
                        "bank_account_name": "",
                        "bank_account_no": "",
                        "swift_code": "",
                        "payment_term_code": "Net 30",
                        "credit_days": 30,
                    }

            return sorted(list(unified.values()), key=lambda x: str(x.get("legal_name", "")).lower())

def get_vendor(vendor_id: int) -> Optional[Dict[str, Any]]:
    tenant_id = get_current_tenant_id()
    with get_connection() as conn:
        with conn.cursor() as cur:
            # Check business_parties first
            try:
                cur.execute("""
                    SELECT p.*, pf.bank_name, pf.bank_account_name, pf.bank_account_no, pf.swift_code, pf.payment_term_code, pf.credit_days
                    FROM business_parties p
                    LEFT JOIN party_finance_profiles pf ON pf.party_id = p.id AND pf.tenant_id = p.tenant_id
                    WHERE p.id = %s AND p.tenant_id = %s
                """, (vendor_id, tenant_id))
                row = cur.fetchone()
                if row:
                    r = dict(row)
                    r["vendor_code"] = r.get("party_code")
                    return r
            except Exception:
                pass

            cur.execute("""
                SELECT * FROM vendors 
                WHERE id = %s AND tenant_id = %s
            """, (vendor_id, tenant_id))
            row = cur.fetchone()
            return dict(row) if row else None

def create_vendor(data: Dict[str, Any], user: Dict[str, Any]) -> int:
    tenant_id = get_current_tenant_id()
    with get_connection() as conn:
        try:
            with conn.cursor() as cur:
                v_code = data.get('vendor_code') or ""
                v_name = data.get('legal_name') or ""
                v_tax = data.get('tax_id') or ""
                v_country = data.get('country') or "TH"
                v_currency = data.get('currency', 'THB')
                username = user.get("username", "system") if isinstance(user, dict) else (str(user) if user else 'system')

                # 1. Insert into vendors
                cur.execute("""
                    INSERT INTO vendors (
                        tenant_id, vendor_code, legal_name, tax_id, country, currency, created_by
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id
                """, (tenant_id, v_code, v_name, v_tax, v_country, v_currency, username))
                row = cur.fetchone()
                try:
                    vendor_id = row["id"] if isinstance(row, dict) or hasattr(row, "keys") else row[0]
                except Exception:
                    vendor_id = row[0]

                # 2. Mirror into business_parties & party_roles (VENDOR)
                try:
                    cur.execute("""
                        INSERT INTO business_parties (
                            tenant_id, party_code, legal_name, display_name, tax_id, country_code, is_active
                        ) VALUES (%s, %s, %s, %s, %s, %s, TRUE)
                        ON CONFLICT (tenant_id, party_code) DO UPDATE SET
                            legal_name = EXCLUDED.legal_name,
                            tax_id = COALESCE(EXCLUDED.tax_id, business_parties.tax_id),
                            country_code = EXCLUDED.country_code,
                            is_active = TRUE
                        RETURNING id
                    """, (tenant_id, v_code, v_name, v_name, v_tax, v_country))
                    bp_row = cur.fetchone()
                    bp_id = bp_row["id"] if bp_row and (isinstance(bp_row, dict) or hasattr(bp_row, "keys")) else (bp_row[0] if bp_row else None)
                    if bp_id:
                        cur.execute("INSERT INTO party_roles (tenant_id, party_id, role_type, is_active) VALUES (%s, %s, 'VENDOR', TRUE) ON CONFLICT DO NOTHING", (tenant_id, bp_id))
                except Exception:
                    pass

                conn.commit()
                if user:
                    user_id = user.get("id", 1) if isinstance(user, dict) else 1
                    log_action(user_id, tenant_id, "vendor", str(vendor_id), "CREATED")
                return vendor_id
        except Exception as e:
            conn.rollback()
            raise RuntimeError(f"Failed to create vendor: {str(e)}")

def update_vendor(vendor_id: int, data: Dict[str, Any], user: Dict[str, Any] = None):
    tenant_id = get_current_tenant_id()
    with get_connection() as conn:
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE vendors SET
                        legal_name = %s,
                        tax_id = %s,
                        country = %s,
                        currency = %s,
                        status = %s,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s AND tenant_id = %s
                """, (
                    data.get('legal_name'),
                    data.get('tax_id'),
                    data.get('country'),
                    data.get('currency'),
                    data.get('status', 'Active'),
                    vendor_id,
                    tenant_id
                ))
                if cur.rowcount == 0:
                    # Also try updating in business_parties
                    cur.execute("""
                        UPDATE business_parties SET
                            legal_name = %s,
                            tax_id = %s,
                            country_code = %s,
                            is_active = %s,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE id = %s AND tenant_id = %s
                    """, (
                        data.get('legal_name'),
                        data.get('tax_id'),
                        data.get('country') or "TH",
                        True if str(data.get('status', 'Active')).lower() == 'active' else False,
                        vendor_id,
                        tenant_id
                    ))
                conn.commit()
                if user:
                    user_id = user.get("id", 1) if isinstance(user, dict) else 1
                    log_action(user_id, tenant_id, "vendor", str(vendor_id), "UPDATED")
        except Exception as e:
            conn.rollback()
            raise RuntimeError(f"Failed to update vendor: {str(e)}")
