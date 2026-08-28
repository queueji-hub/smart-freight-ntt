"""Canonical Charge Master lookups used by quotation, billing and profitability."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from database.connection import get_connection
from database.postgres_compat import ensure_phase30_charge_master_schema
from managers.tenant_context import get_current_tenant_id


_charge_schema_ensured = False

def _ensure_schema(conn) -> None:
    global _charge_schema_ensured
    if _charge_schema_ensured:
        return
    try:
        if type(conn).__name__ != "SQLiteConnAdapter":
            ensure_phase30_charge_master_schema(conn)
        _charge_schema_ensured = True
    except Exception:
        pass


import time

_charges_cache: dict[tuple, tuple[float, list[dict]]] = {}
_CACHE_TTL = 30.0  # 30 seconds cache for rapid consecutive UI calls

def clear_charges_cache() -> None:
    global _charges_cache
    _charges_cache.clear()

def list_charges(active_only: bool = True) -> List[Dict[str, Any]]:
    tenant_id = get_current_tenant_id()
    cache_key = (tenant_id, active_only)
    now = time.time()
    if cache_key in _charges_cache:
        t_exp, data = _charges_cache[cache_key]
        if now < t_exp:
            return [dict(x) for x in data]

    with get_connection() as conn:
        _ensure_schema(conn)
        with conn.cursor() as cur:
            is_sqlite = type(conn).__name__ == "SQLiteConnAdapter" or "sqlite" in str(type(conn)).lower()
            where = "WHERE (tenant_id=%s OR tenant_id IS NULL OR tenant_id='default')" if not is_sqlite else "WHERE (tenant_id=? OR tenant_id IS NULL OR tenant_id='default')"
            params: list[Any] = [tenant_id]
            if active_only:
                where += " AND is_active = 1" if is_sqlite else " AND is_active = TRUE"
            try:
                cur.execute(
                    f"""
                    SELECT id, charge_code, description, category, default_basis,
                           default_unit, default_currency, default_tax_type, default_wht_type, is_active
                    FROM charge_master
                    {where}
                    ORDER BY charge_code
                    """,
                    params,
                )
                rows = cur.fetchall()
                if not rows:
                    res = []
                elif isinstance(rows[0], dict) or hasattr(rows[0], "keys"):
                    res = [dict(row) for row in rows]
                else:
                    cols = ["id", "charge_code", "description", "category", "default_basis", "default_unit", "default_currency", "default_tax_type", "default_wht_type", "is_active"]
                    res = [dict(zip(cols, row)) for row in rows]
                _charges_cache[cache_key] = (now + _CACHE_TTL, res)
                return [dict(x) for x in res]
            except Exception:
                return []


def list_charge_categories() -> List[str]:
    """Returns distinct active charge categories from Master Data."""
    charges = list_charges(active_only=True)
    cats = []
    seen = set()
    for c in charges:
        cat = str(c.get("category") or "").strip()
        if cat and cat not in seen:
            seen.add(cat)
            cats.append(cat)
    
    # Standard fallbacks if table was empty
    default_cats = [
        "Ocean Freight Cost (สายเรือ)",
        "Air Freight Cost (สายการบิน)",
        "Port Terminal Cost (THC / ท่าเรือ)",
        "Customs Brokerage Cost (พิธีการศุลกากร)",
        "Inland Transport / Trucking (รถหัวลาก/ขนส่ง)",
        "Port Storage / Demurrage / Detention",
        "Documentation / D/O Cost",
        "Advance Paid on Behalf (สำรองจ่าย)",
        "Cargo Handling / CFS",
        "Surcharge & Fuel",
        "Insurance & Other"
    ]
    for dc in default_cats:
        if dc not in seen:
            seen.add(dc)
            cats.append(dc)
    return cats


def get_charge(charge_code: str) -> Optional[Dict[str, Any]]:
    code = str(charge_code or "").strip().upper()
    if not code:
        return None
    tenant_id = get_current_tenant_id()
    with get_connection() as conn:
        _ensure_schema(conn)
        with conn.cursor() as cur:
            is_sqlite = type(conn).__name__ == "SQLiteConnAdapter" or "sqlite" in str(type(conn)).lower()
            try:
                if is_sqlite:
                    cur.execute(
                        """
                        SELECT id, charge_code, description, category, default_basis,
                               default_unit, default_currency, default_tax_type, default_wht_type, is_active
                        FROM charge_master
                        WHERE (tenant_id=? OR tenant_id IS NULL OR tenant_id='default') AND UPPER(charge_code)=?
                        LIMIT 1
                        """,
                        (tenant_id, code),
                    )
                else:
                    cur.execute(
                        """
                        SELECT id, charge_code, description, category, default_basis,
                               default_unit, default_currency, default_tax_type, default_wht_type, is_active
                        FROM charge_master
                        WHERE (tenant_id=%s OR tenant_id IS NULL OR tenant_id='default') AND UPPER(charge_code)=%s
                        LIMIT 1
                        """,
                        (tenant_id, code),
                    )
                row = cur.fetchone()
                if not row:
                    return None
                if isinstance(row, dict) or hasattr(row, "keys"):
                    return dict(row)
                cols = ["id", "charge_code", "description", "category", "default_basis", "default_unit", "default_currency", "default_tax_type", "default_wht_type", "is_active"]
                return dict(zip(cols, row))
            except Exception:
                return None


def upsert_charge(data: Dict[str, Any], user: Optional[Dict[str, Any]] = None) -> int:
    tenant_id = get_current_tenant_id()
    code = str(data.get("charge_code") or "").strip().upper()
    desc = str(data.get("description") or "").strip()
    if not code or not desc:
        raise ValueError("Charge code and description are required.")
    
    category = str(data.get("category") or "Ocean Freight Cost (สายเรือ)").strip()
    basis = str(data.get("default_basis") or "Container").strip()
    unit = str(data.get("default_unit") or "CTR").strip()
    curr = str(data.get("default_currency") or "THB").strip().upper()
    tax_type = str(data.get("default_tax_type") or "VAT 7%").strip()
    wht_type = str(data.get("default_wht_type") or "None").strip()
    active = bool(data.get("is_active", True))

    with get_connection() as conn:
        _ensure_schema(conn)
        with conn.cursor() as cur:
            is_sqlite = type(conn).__name__ == "SQLiteConnAdapter" or "sqlite" in str(type(conn)).lower()
            cid = data.get("id")
            if cid:
                if is_sqlite:
                    cur.execute("""
                        UPDATE charge_master SET charge_code=?, description=?, category=?, default_basis=?, default_unit=?, default_currency=?, default_tax_type=?, default_wht_type=?, is_active=?
                        WHERE id=? AND (tenant_id=? OR tenant_id IS NULL OR tenant_id='default')
                    """, (code, desc, category, basis, unit, curr, tax_type, wht_type, 1 if active else 0, int(cid), tenant_id))
                else:
                    cur.execute("""
                        UPDATE charge_master SET charge_code=%s, description=%s, category=%s, default_basis=%s, default_unit=%s, default_currency=%s, default_tax_type=%s, default_wht_type=%s, is_active=%s
                        WHERE id=%s AND (tenant_id=%s OR tenant_id IS NULL OR tenant_id='default')
                    """, (code, desc, category, basis, unit, curr, tax_type, wht_type, active, int(cid), tenant_id))
                conn.commit()
                clear_charges_cache()
                return int(cid)
            else:
                if is_sqlite:
                    cur.execute("""
                        INSERT INTO charge_master (tenant_id, charge_code, description, category, default_basis, default_unit, default_currency, default_tax_type, default_wht_type, is_active)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (tenant_id, code, desc, category, basis, unit, curr, tax_type, wht_type, 1 if active else 0))
                    cid = cur.lastrowid
                else:
                    cur.execute("""
                        INSERT INTO charge_master (tenant_id, charge_code, description, category, default_basis, default_unit, default_currency, default_tax_type, default_wht_type, is_active)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id
                    """, (tenant_id, code, desc, category, basis, unit, curr, tax_type, wht_type, active))
                    row = cur.fetchone()
                    cid = row["id"] if isinstance(row, dict) or hasattr(row, "keys") else row[0]
                conn.commit()
                clear_charges_cache()
                return int(cid)


def delete_charge(charge_id: int, user: Optional[Dict[str, Any]] = None) -> bool:
    tenant_id = get_current_tenant_id()
    if not charge_id:
        return False
    with get_connection() as conn:
        _ensure_schema(conn)
        with conn.cursor() as cur:
            is_sqlite = type(conn).__name__ == "SQLiteConnAdapter" or "sqlite" in str(type(conn)).lower()
            if is_sqlite:
                cur.execute("DELETE FROM charge_master WHERE id=? AND (tenant_id=? OR tenant_id IS NULL OR tenant_id='default')", (int(charge_id), tenant_id))
            else:
                cur.execute("DELETE FROM charge_master WHERE id=%s AND (tenant_id=%s OR tenant_id IS NULL OR tenant_id='default')", (int(charge_id), tenant_id))
            conn.commit()
            clear_charges_cache()
            return True
