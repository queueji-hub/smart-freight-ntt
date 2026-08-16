"""Read-only rate selection for quotation; keeps rate ownership in Rate Master."""
from __future__ import annotations

from datetime import date
from typing import Any, Dict, List, Optional

from database.connection import get_connection
from managers.tenant_context import get_current_tenant_id


def _tenant() -> str:
    return str(get_current_tenant_id() or "default")


def find_applicable_rates(
    *,
    carrier_id: Optional[int] = None,
    origin_port_id: Optional[int] = None,
    destination_port_id: Optional[int] = None,
    mode: Optional[str] = None,
    equipment_type: Optional[str] = None,
    on_date: Optional[date] = None,
) -> List[Dict[str, Any]]:
    """Return active tenant rates matching the supplied commercial context."""
    tenant = _tenant()
    effective = on_date or date.today()
    clauses = [
        "r.tenant_id=%s",
        "r.status='ACTIVE'",
        "(r.valid_from IS NULL OR r.valid_from<=%s)",
        "(r.valid_to IS NULL OR r.valid_to>=%s)",
    ]
    params: list[Any] = [tenant, effective, effective]
    if carrier_id:
        clauses.append("r.carrier_id=%s")
        params.append(carrier_id)
    if origin_port_id:
        clauses.append("r.origin_port_id=%s")
        params.append(origin_port_id)
    if destination_port_id:
        clauses.append("r.destination_port_id=%s")
        params.append(destination_port_id)
    if mode:
        clauses.append("UPPER(r.mode)=UPPER(%s)")
        params.append(mode)
    if equipment_type:
        clauses.append("(r.equipment_type IS NULL OR UPPER(r.equipment_type)=UPPER(%s))")
        params.append(equipment_type)

    sql = f"""
        SELECT r.id, r.rate_no, r.mode, r.service_type, r.equipment_type, r.currency,
               r.valid_from, r.valid_to, r.carrier_id, r.origin_port_id, r.destination_port_id,
               l.id AS line_id, l.charge_id, cm.charge_code, cm.description AS charge_description,
               l.basis, l.minimum, l.rate, l.currency AS line_currency
        FROM rate_cards r
        LEFT JOIN rate_card_lines l
          ON l.rate_card_id=r.id AND l.tenant_id=r.tenant_id
        LEFT JOIN charge_master cm
          ON cm.id=l.charge_id AND cm.tenant_id=r.tenant_id
        WHERE {' AND '.join(clauses)}
        ORDER BY r.rate_no, l.id
    """
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(sql, params)
        return [dict(row) for row in cur.fetchall()]
