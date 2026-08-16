"""Tenant-safe rate card CRUD for freight quotation and costing."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from database.connection import get_connection
from database.postgres_compat import ensure_phase30_master_data_schema
from managers.tenant_context import get_current_tenant_id


def _tenant(user: Optional[Dict[str, Any]] = None) -> str:
    return str((user or {}).get("tenant_id") or get_current_tenant_id() or "default")


def _ensure(conn) -> None:
    if type(conn).__name__ != "SQLiteConnAdapter":
        ensure_phase30_master_data_schema(conn)


def list_rate_cards(active_only: bool = True, user: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    tenant = _tenant(user)
    with get_connection() as conn:
        _ensure(conn)
        with conn.cursor() as cur:
            where = "WHERE tenant_id=%s"
            params: list[Any] = [tenant]
            if active_only:
                where += " AND status='ACTIVE'"
            cur.execute(f"SELECT * FROM rate_cards {where} ORDER BY rate_no", params)
            rows = [dict(r) for r in cur.fetchall()]
            for row in rows:
                cur.execute("SELECT * FROM rate_card_lines WHERE tenant_id=%s AND rate_card_id=%s ORDER BY id", (tenant, row["id"]))
                row["lines"] = [dict(x) for x in cur.fetchall()]
            return rows


def upsert_rate_card(data: Dict[str, Any], lines: List[Dict[str, Any]], user: Optional[Dict[str, Any]] = None) -> int:
    tenant = _tenant(user)
    rate_no = str(data.get("rate_no") or "").strip().upper()
    mode = str(data.get("mode") or "").strip().upper()
    if not rate_no or not mode:
        raise ValueError("Rate No. and Mode are required.")
    with get_connection() as conn, conn.cursor() as cur:
        if data.get("id"):
            rate_id = int(data["id"])
            cur.execute("""UPDATE rate_cards SET rate_no=%s, carrier_id=%s, origin_port_id=%s,
                destination_port_id=%s, mode=%s, service_type=%s, equipment_type=%s, currency=%s,
                valid_from=%s, valid_to=%s, status=%s WHERE id=%s AND tenant_id=%s""",
                (rate_no, data.get("carrier_id"), data.get("origin_port_id"), data.get("destination_port_id"), mode,
                 data.get("service_type"), data.get("equipment_type"), data.get("currency") or "USD",
                 data.get("valid_from"), data.get("valid_to"), data.get("status") or "ACTIVE", rate_id, tenant))
            cur.execute("DELETE FROM rate_card_lines WHERE tenant_id=%s AND rate_card_id=%s", (tenant, rate_id))
        else:
            cur.execute("""INSERT INTO rate_cards
                (tenant_id, rate_no, carrier_id, origin_port_id, destination_port_id, mode,
                 service_type, equipment_type, currency, valid_from, valid_to, status)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id""",
                (tenant, rate_no, data.get("carrier_id"), data.get("origin_port_id"), data.get("destination_port_id"), mode,
                 data.get("service_type"), data.get("equipment_type"), data.get("currency") or "USD",
                 data.get("valid_from"), data.get("valid_to"), data.get("status") or "ACTIVE"))
            rate_id = int(cur.fetchone()[0])
        for line in lines:
            charge_id = line.get("charge_id")
            rate = float(line.get("rate") or 0)
            if charge_id is None or rate < 0:
                continue
            cur.execute("""INSERT INTO rate_card_lines
                (tenant_id, rate_card_id, charge_id, basis, minimum, rate, currency)
                VALUES (%s,%s,%s,%s,%s,%s,%s)""",
                (tenant, rate_id, charge_id, line.get("basis"), float(line.get("minimum") or 0), rate, line.get("currency") or data.get("currency") or "USD"))
        conn.commit()
        return rate_id
