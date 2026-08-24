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


def list_charges(active_only: bool = True) -> List[Dict[str, Any]]:
    tenant_id = get_current_tenant_id()
    with get_connection() as conn:
        _ensure_schema(conn)
        with conn.cursor() as cur:
            where = "WHERE tenant_id=%s"
            params: list[Any] = [tenant_id]
            if active_only:
                where += " AND is_active = TRUE"
            try:
                cur.execute(
                    f"""
                    SELECT id, charge_code, description, category, default_basis,
                           default_unit, default_currency, is_active
                    FROM charge_master
                    {where}
                    ORDER BY charge_code
                    """,
                    params,
                )
                return [dict(row) for row in cur.fetchall()]
            except Exception:
                return []


def get_charge(charge_code: str) -> Optional[Dict[str, Any]]:
    code = str(charge_code or "").strip().upper()
    if not code:
        return None
    tenant_id = get_current_tenant_id()
    with get_connection() as conn:
        _ensure_schema(conn)
        with conn.cursor() as cur:
            try:
                cur.execute(
                    """
                    SELECT id, charge_code, description, category, default_basis,
                           default_unit, default_currency, is_active
                    FROM charge_master
                    WHERE tenant_id=%s AND UPPER(charge_code)=%s
                    LIMIT 1
                    """,
                    (tenant_id, code),
                )
                row = cur.fetchone()
                return dict(row) if row else None
            except Exception:
                return None


def upsert_charge(data: Dict[str, Any], user: Optional[Dict[str, Any]] = None) -> int:
    tenant_id = get_current_tenant_id()
    code = str(data.get("charge_code") or "").strip().upper()
    desc = str(data.get("description") or "").strip()
    if not code or not desc:
        raise ValueError("Charge code and description are required.")
    
    category = str(data.get("category") or "FREIGHT").strip().upper()
    basis = str(data.get("default_basis") or "PER_SHIPMENT").strip()
    unit = str(data.get("default_unit") or "SHIPMENT").strip()
    curr = str(data.get("default_currency") or "USD").strip().upper()
    active = bool(data.get("is_active", True))

    with get_connection() as conn:
        _ensure_schema(conn)
        with conn.cursor() as cur:
            is_sqlite = type(conn).__name__ == "SQLiteConnAdapter" or "sqlite" in str(type(conn)).lower()
            cid = data.get("id")
            if cid:
                if is_sqlite:
                    cur.execute("""
                        UPDATE charge_master SET charge_code=?, description=?, category=?, default_basis=?, default_unit=?, default_currency=?, is_active=?
                        WHERE id=? AND (tenant_id=? OR tenant_id IS NULL OR tenant_id='default')
                    """, (code, desc, category, basis, unit, curr, 1 if active else 0, int(cid), tenant_id))
                else:
                    cur.execute("""
                        UPDATE charge_master SET charge_code=%s, description=%s, category=%s, default_basis=%s, default_unit=%s, default_currency=%s, is_active=%s
                        WHERE id=%s AND (tenant_id=%s OR tenant_id IS NULL OR tenant_id='default')
                    """, (code, desc, category, basis, unit, curr, active, int(cid), tenant_id))
                conn.commit()
                return int(cid)
            else:
                if is_sqlite:
                    cur.execute("""
                        INSERT INTO charge_master (tenant_id, charge_code, description, category, default_basis, default_unit, default_currency, is_active)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (tenant_id, code, desc, category, basis, unit, curr, 1 if active else 0))
                    cid = cur.lastrowid
                else:
                    cur.execute("""
                        INSERT INTO charge_master (tenant_id, charge_code, description, category, default_basis, default_unit, default_currency, is_active)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING id
                    """, (tenant_id, code, desc, category, basis, unit, curr, active))
                    row = cur.fetchone()
                    cid = row["id"] if isinstance(row, dict) or hasattr(row, "keys") else row[0]
                conn.commit()
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
            return True
