"""Canonical Charge Master lookups used by quotation, billing and profitability."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from database.connection import get_connection
from database.postgres_compat import ensure_phase30_charge_master_schema
from managers.tenant_context import get_current_tenant_id


def _ensure_schema(conn) -> None:
    if type(conn).__name__ != "SQLiteConnAdapter":
        ensure_phase30_charge_master_schema(conn)


def list_charges(active_only: bool = True) -> List[Dict[str, Any]]:
    tenant_id = get_current_tenant_id()
    with get_connection() as conn:
        _ensure_schema(conn)
        with conn.cursor() as cur:
            where = "WHERE tenant_id=%s"
            params: list[Any] = [tenant_id]
            if active_only:
                where += " AND is_active = TRUE"
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


def get_charge(charge_code: str) -> Optional[Dict[str, Any]]:
    code = str(charge_code or "").strip().upper()
    if not code:
        return None
    tenant_id = get_current_tenant_id()
    with get_connection() as conn:
        _ensure_schema(conn)
        with conn.cursor() as cur:
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
