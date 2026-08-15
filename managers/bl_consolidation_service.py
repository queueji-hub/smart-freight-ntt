"""Company-issued B/L consolidation helpers.

A Shipment/Job is the operational parent. Multiple company-issued B/Ls may
belong to the same shipment without creating duplicate shipments.
"""
from __future__ import annotations

from datetime import date, datetime
import re
from typing import Any, Dict, Optional

from database.connection import get_connection
from managers.tenant_context import get_current_tenant_id


PORT_CODE_ALIASES = {
    "LAEM CHABANG": "LCH",
    "LAEM CHABANG, THAILAND": "LCH",
    "NAHA": "NAH",
    "NAHA, OKINAWA, JAPAN": "NAH",
    "BANGKOK": "BKK",
    "BANGKOK, THAILAND": "BKK",
    "SINGAPORE": "SIN",
    "SINGAPORE, SINGAPORE": "SIN",
    "ROTTERDAM": "RTM",
    "ROTTERDAM, NETHERLANDS": "RTM",
}


def _norm_place(value: Any) -> str:
    text = str(value or "").strip().upper()
    if not text:
        return "XXX"
    if text in PORT_CODE_ALIASES:
        return PORT_CODE_ALIASES[text]
    match = re.search(r"\(([A-Z]{3})\)", text)
    if match:
        return match.group(1)
    letters = "".join(ch for ch in text if ch.isalnum())
    return (letters[:3] or "XXX").upper()


def _resolve_date(value: Any) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if value:
        try:
            return datetime.strptime(str(value)[:10], "%Y-%m-%d").date()
        except ValueError:
            pass
    return date.today()


def generate_company_bl_no(pol: Any, pod: Any, ref_date: Any = None) -> str:
    """Generate NATTA-{POL3}{POD3}{YYMM}{SEQ3} for one tenant/route/month."""
    tenant = get_current_tenant_id()
    if not tenant:
        raise RuntimeError("tenant_id is required for B/L numbering")
    d = _resolve_date(ref_date)
    yymm = d.strftime("%y%m")
    route_key = f"NATTA-{_norm_place(pol)}{_norm_place(pod)}"

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO document_counters (tenant_id, doc_type, yymm, last_running)
                VALUES (%s, %s, %s, 1)
                ON CONFLICT (tenant_id, doc_type, yymm)
                DO UPDATE SET last_running = document_counters.last_running + 1
                RETURNING last_running
                """,
                (tenant, route_key, yymm),
            )
            row = cur.fetchone()
            if not row:
                raise RuntimeError("Unable to allocate B/L sequence")
            seq = row["last_running"] if isinstance(row, dict) or hasattr(row, "keys") else row[0]
            conn.commit()
    return f"{route_key}{yymm}{int(seq):03d}"


def next_consol_sequence(job_no: str) -> int:
    """Atomically allocate the next B/L sequence within one Shipment/Job."""
    tenant = get_current_tenant_id()
    if not tenant:
        raise RuntimeError("tenant_id is required for consolidation sequencing")
    counter_type = f"CONSOL-{job_no}"
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO document_counters (tenant_id, doc_type, yymm, last_running)
                VALUES (%s, %s, %s, 1)
                ON CONFLICT (tenant_id, doc_type, yymm)
                DO UPDATE SET last_running = document_counters.last_running + 1
                RETURNING last_running
                """,
                (tenant, counter_type, "0000"),
            )
            row = cur.fetchone()
            if not row:
                raise RuntimeError("Unable to allocate consolidation sequence")
            seq = row["last_running"] if isinstance(row, dict) or hasattr(row, "keys") else row[0]
            conn.commit()
            return int(seq)


def build_bl_document_payload(
    bl: Dict[str, Any],
    job: Dict[str, Any] | None = None,
    booking: Dict[str, Any] | None = None,
    containers: Optional[list[dict]] = None,
) -> Dict[str, Any]:
    """Build the pure document payload consumed by the PDF layer."""
    return {
        "bl": dict(bl),
        "job": dict(job or {}),
        "booking": dict(booking or {}),
        "containers": list(containers or []),
        "company": {"name": "NATTAYARAAT CO., LTD."},
    }


def assemble_bl_document_payload(bl_id: int) -> Dict[str, Any]:
    """Read and validate B/L context in the manager layer for PDF rendering."""
    from managers.bl_workflow_service import get_bl
    from managers.shipment_manager import get_shipment
    try:
        from managers.bl_manager import list_bl_containers
    except Exception:
        list_bl_containers = lambda _bl_id: []

    bl = get_bl(int(bl_id))
    if not bl:
        raise ValueError(f"B/L {bl_id} not found")
    job = get_shipment(bl.get("job_no")) if bl.get("job_no") else {}
    containers = list_bl_containers(int(bl_id)) or []
    return build_bl_document_payload(bl, job=job or {}, containers=containers)
