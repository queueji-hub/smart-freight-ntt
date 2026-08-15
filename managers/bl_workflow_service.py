"""Tenant-safe Bill of Lading workflow for the production-facing workspace.

One Shipment/Job is the consolidation parent. Multiple company-issued B/L
records may exist under the same Shipment, each with its own shipper,
consignee and cargo details. Legacy HBL/MBL storage is retained only for
historical compatibility; the new UI/workflow uses one BILL OF LADING concept.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Any, Dict, List, Optional

from database.connection import get_connection
from database.postgres_compat import ensure_phase30_bl_schema
from managers.bl_consolidation_service import generate_company_bl_no, next_consol_sequence
from managers.tenant_context import get_current_tenant_id

BL_TYPES = ("BL",)
APPROVAL_STATES = ("Draft", "Pending Approval", "Approved")


def _s(value: Any, default: str = "") -> str:
    if value is None:
        return default
    text = str(value).strip()
    return default if text.lower() in {"", "none", "nan", "nat"} else text


def _safe_date(value: Any) -> Optional[date]:
    if not value:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    try:
        return datetime.strptime(str(value)[:10], "%Y-%m-%d").date()
    except Exception:
        return None


def _ensure_bl_schema(conn) -> None:
    if type(conn).__name__ != "SQLiteConnAdapter":
        ensure_phase30_bl_schema(conn)


def list_bls(job_no: Optional[str] = None) -> List[Dict[str, Any]]:
    tenant = get_current_tenant_id()
    with get_connection() as conn:
        _ensure_bl_schema(conn)
        sql = "SELECT * FROM bills_of_lading WHERE tenant_id=%s"
        params: list[Any] = [tenant]
        if job_no:
            sql += " AND job_no=%s"
            params.append(job_no)
        sql += " ORDER BY job_no, consol_seq NULLS FIRST, created_at DESC, id DESC"
        with conn.cursor() as cur:
            cur.execute(sql, tuple(params))
            return [dict(row) for row in cur.fetchall()]


def list_job_bls(job_no: str) -> List[Dict[str, Any]]:
    return list_bls(job_no=job_no)


def get_bl(bl_id: int) -> Optional[Dict[str, Any]]:
    tenant = get_current_tenant_id()
    with get_connection() as conn:
        _ensure_bl_schema(conn)
        with conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM bills_of_lading WHERE id=%s AND tenant_id=%s LIMIT 1",
                (bl_id, tenant),
            )
            row = cur.fetchone()
            return dict(row) if row else None


def create_bl_from_job(job_no: str, user: Dict[str, Any], overrides: Optional[Dict[str, Any]] = None) -> int:
    tenant = get_current_tenant_id()
    from managers.shipment_manager import get_shipment
    job = get_shipment(job_no)
    if not job:
        raise ValueError(f"Job '{job_no}' not found.")

    etd = _safe_date(job.get("etd"))
    consol_seq = next_consol_sequence(job_no)

    data: Dict[str, Any] = {
        "job_no": job_no,
        "shipment_id": job.get("id"),
        "booking_no": job.get("booking_no"),
        "bl_type": "BL",
        "status": "Draft",
        "approval_status": "Draft",
        "consol_no": job_no,
        "consol_seq": consol_seq,
        "shipper": job.get("shipper"),
        "consignee": job.get("consignee"),
        "notify_party": job.get("notify_party"),
        "place_of_receipt": job.get("place_of_receipt"),
        "port_of_loading": job.get("pol"),
        "port_of_discharge": job.get("pod"),
        "place_of_delivery": job.get("place_of_delivery"),
        "final_destination": job.get("final_destination"),
        "vessel": job.get("mother_vessel") or job.get("vessel"),
        "voyage": job.get("voyage"),
        "etd": job.get("etd"),
        "eta": job.get("eta"),
        "freight_term": job.get("freight_term"),
        "description_of_goods": job.get("commodity"),
        "hs_code": job.get("hs_code"),
        "package_qty": job.get("package_quantity") or 0,
        "package_type": job.get("package_type"),
        "gross_weight": job.get("gross_weight") or 0,
        "measurement_cbm": job.get("cbm") or 0,
        "created_by": user.get("username", "system"),
        "tenant_id": tenant,
    }
    if overrides:
        data.update(overrides)

    if not data.get("bl_no"):
        data["bl_no"] = generate_company_bl_no(
            data.get("port_of_loading") or job.get("pol"),
            data.get("port_of_discharge") or job.get("pod"),
            data.get("etd") or etd,
        )

    allowed = {
        "tenant_id", "bl_no", "job_no", "shipment_id", "booking_no", "consol_no", "consol_seq",
        "shipper", "consignee", "notify_party", "place_of_receipt", "port_of_loading",
        "port_of_discharge", "place_of_delivery", "final_destination", "vessel", "voyage",
        "etd", "eta", "bl_date", "place_of_issue", "number_of_originals", "freight_term",
        "freight_payable_at", "marks_numbers", "package_qty", "package_type", "description_of_goods",
        "gross_weight", "measurement_cbm", "hs_code", "remarks", "special_instructions",
        "bl_type", "status", "approval_status", "created_by",
    }
    data = {k: v for k, v in data.items() if k in allowed}
    cols = list(data)
    placeholders = ", ".join(["%s"] * len(cols))

    with get_connection() as conn:
        _ensure_bl_schema(conn)
        with conn.cursor() as cur:
            cur.execute(
                f"INSERT INTO bills_of_lading ({', '.join(cols)}) VALUES ({placeholders}) RETURNING id",
                tuple(data[c] for c in cols),
            )
            row = cur.fetchone()
            conn.commit()
            return row["id"] if isinstance(row, dict) else row[0]


def update_bl(bl_id: int, patch: Dict[str, Any]) -> bool:
    doc = get_bl(bl_id)
    if not doc:
        raise ValueError("B/L not found.")
    if doc.get("status") in {"Issued", "Surrendered", "Cancelled"}:
        raise ValueError(f"B/L is {doc.get('status')} and cannot be edited.")

    allowed = {
        "shipper", "consignee", "notify_party", "place_of_receipt", "port_of_loading",
        "port_of_discharge", "place_of_delivery", "final_destination", "vessel", "voyage",
        "etd", "eta", "bl_date", "place_of_issue", "number_of_originals", "freight_term",
        "freight_payable_at", "marks_numbers", "package_qty", "package_type",
        "description_of_goods", "gross_weight", "measurement_cbm", "hs_code", "remarks",
        "special_instructions",
    }
    values = {k: v for k, v in patch.items() if k in allowed}
    if not values:
        return False

    tenant = get_current_tenant_id()
    sets = ", ".join(f"{k}=%s" for k in values)
    params = list(values.values()) + [bl_id, tenant]
    with get_connection() as conn:
        _ensure_bl_schema(conn)
        with conn.cursor() as cur:
            cur.execute(
                f"UPDATE bills_of_lading SET {sets}, updated_at=CURRENT_TIMESTAMP WHERE id=%s AND tenant_id=%s",
                tuple(params),
            )
            conn.commit()
            return cur.rowcount > 0


def submit_for_approval(bl_id: int, user: Dict[str, Any]) -> str:
    doc = get_bl(bl_id)
    if not doc:
        raise ValueError("B/L not found.")
    if str(doc.get("approval_status") or "Draft") != "Draft":
        raise ValueError("Only Draft B/L documents can be submitted.")
    from managers.document_approval_manager import submit_for_approval as transition
    return transition("bl", doc["bl_no"], user)


def approve(bl_id: int, user: Dict[str, Any]) -> str:
    doc = get_bl(bl_id)
    if not doc:
        raise ValueError("B/L not found.")
    from managers.document_approval_manager import approve_document
    return approve_document("bl", doc["bl_no"], user)
