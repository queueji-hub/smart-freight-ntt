"""Tenant-aware CRUD for the canonical Charge Master."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from database.connection import get_connection
from database.postgres_compat import ensure_phase30_charge_master_schema
from managers.tenant_context import get_current_tenant_id


def _tenant(user: Optional[Dict[str, Any]] = None) -> str:
    return str((user or {}).get("tenant_id") or get_current_tenant_id() or "default")


_charge_crud_schema_ensured = False

def _ensure(conn) -> None:
    global _charge_crud_schema_ensured
    if _charge_crud_schema_ensured:
        return
    if type(conn).__name__ != "SQLiteConnAdapter":
        ensure_phase30_charge_master_schema(conn)
    _charge_crud_schema_ensured = True


def list_charges(active_only: bool = False, user: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    tenant = _tenant(user)
    with get_connection() as conn:
        _ensure(conn)
        with conn.cursor() as cur:
            where = "WHERE tenant_id=%s"
            params: list[Any] = [tenant]
            if active_only:
                where += " AND is_active=TRUE"
            cur.execute(
                f"""SELECT id, charge_code, description, category, default_basis,
                           default_unit, default_currency, is_active
                    FROM charge_master {where}
                    ORDER BY charge_code""",
                params,
            )
            return [dict(row) for row in cur.fetchall()]


def upsert_charge(data: Dict[str, Any], user: Optional[Dict[str, Any]] = None) -> int:
    tenant = _tenant(user)
    code = str(data.get("charge_code") or "").strip().upper()
    description = str(data.get("description") or "").strip()
    if not code or not description:
        raise ValueError("Charge Code and Description are required.")
    with get_connection() as conn:
        _ensure(conn)
        with conn.cursor() as cur:
            params = (
                code,
                description,
                data.get("category"),
                data.get("default_basis"),
                data.get("default_unit"),
                data.get("default_currency") or "USD",
                bool(data.get("is_active", True)),
            )
            charge_id = data.get("id")
            if not charge_id:
                cur.execute("SELECT id FROM charge_master WHERE tenant_id=%s AND charge_code=%s LIMIT 1", (tenant, code))
                existing = cur.fetchone()
                if existing:
                    charge_id = existing["id"] if isinstance(existing, dict) or hasattr(existing, "keys") else existing[0]

            if charge_id:
                cur.execute(
                    """UPDATE charge_master
                       SET charge_code=%s, description=%s, category=%s,
                           default_basis=%s, default_unit=%s,
                           default_currency=%s, is_active=%s,
                           updated_at=CURRENT_TIMESTAMP
                       WHERE id=%s AND tenant_id=%s""",
                    (*params, int(charge_id), tenant),
                )
                charge_id = int(charge_id)
            else:
                cur.execute(
                    """INSERT INTO charge_master
                       (tenant_id, charge_code, description, category, default_basis,
                        default_unit, default_currency, is_active)
                       VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
                       RETURNING id""",
                    (tenant, *params),
                )
                row = cur.fetchone()
                charge_id = int(row["id"] if isinstance(row, dict) or hasattr(row, "keys") else row[0])
        conn.commit()
        return charge_id
