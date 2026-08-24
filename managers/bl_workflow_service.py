"""Tenant-safe Bill of Lading workflow for the production-facing workspace."""
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


_bl_schema_ensured = False

def _ensure_bl_schema(conn) -> None:
    """Repair legacy PostgreSQL B/L schema before the first B/L query/write."""
    global _bl_schema_ensured
    if _bl_schema_ensured:
        return
    if type(conn).__name__ != "SQLiteConnAdapter":
        ensure_phase30_bl_schema(conn)
    _bl_schema_ensured = True


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

    # 1. Fetch linked Booking for fallback party & routing context
    booking_data: Dict[str, Any] = {}
    booking_no = job.get("booking_no")
    if booking_no:
        try:
            from managers.booking_manager import get_booking
            booking_data = get_booking(booking_no) or {}
        except Exception:
            booking_data = {}

    # 2. Fetch linked Containers for Marks & Numbers and accurate Cargo Metrics
    containers: List[Dict[str, Any]] = []
    with get_connection() as conn:
        with conn.cursor() as cur:
            try:
                cur.execute(
                    "SELECT * FROM containers WHERE (job_no = %s OR shipment_id = %s) AND tenant_id = %s ORDER BY container_no",
                    (job_no, job.get("id"), tenant)
                )
                containers = [dict(r) for r in cur.fetchall()]
            except Exception:
                try:
                    cur.execute(
                        "SELECT * FROM containers WHERE (job_no = %s OR shipment_id = %s) ORDER BY container_no",
                        (job_no, job.get("id"))
                    )
                    containers = [dict(r) for r in cur.fetchall()]
                except Exception:
                    containers = []

    # 3. Assemble Marks & Numbers from Container + Seal details
    if containers:
        marks_lines = ["CONTAINER(S) & SEAL(S):"]
        for c in containers:
            c_no = str(c.get("container_no") or "").strip()
            s_no = str(c.get("seal_no") or "NO SEAL").strip()
            c_sz = str(c.get("container_size") or "").strip()
            c_tp = str(c.get("container_type") or "").strip()
            marks_lines.append(f"{c_no} / SEAL: {s_no} ({c_sz} {c_tp})".strip())
        marks_numbers = "\n".join(marks_lines)
    else:
        marks_numbers = (
            job.get("container_summary")
            or booking_data.get("container_summary")
            or "N/M (NO MARKS)"
        )

    # 4. Resolve Cargo Metrics with Container Fallbacks
    container_gross = sum(float(c.get("gross_weight") or c.get("vgm_kg") or 0) for c in containers)
    container_cbm = sum(float(c.get("volume_cbm") or 0) for c in containers)

    gross_weight = float(job.get("gross_weight") or booking_data.get("gross_weight") or container_gross or 0)
    measurement_cbm = float(job.get("cbm") or booking_data.get("measurement_cbm") or container_cbm or 0)
    package_qty = int(job.get("package_quantity") or job.get("package_qty") or booking_data.get("package_qty") or len(containers) or 1)
    package_type = (
        job.get("package_type")
        or booking_data.get("package_unit")
        or ("CONTAINER(S)" if containers else "PACKAGES")
    )

    # 5. Resolve Routing and Transport
    pol = job.get("pol") or job.get("port_of_loading") or booking_data.get("pol")
    pod = job.get("pod") or job.get("port_of_discharge") or booking_data.get("pod")
    vessel = (
        job.get("mother_vessel")
        or job.get("vessel")
        or booking_data.get("mother_vessel")
        or booking_data.get("vessel")
        or job.get("carrier")
    )
    voyage = (
        job.get("mother_voyage")
        or job.get("voyage")
        or booking_data.get("mother_voyage")
        or booking_data.get("voyage")
        or ""
    )
    etd = _safe_date(job.get("etd") or booking_data.get("etd"))
    eta = _safe_date(job.get("eta") or booking_data.get("eta"))
    consol_seq = next_consol_sequence(job_no)

    # 6. Resolve Parties & Freight Terms
    shipper = job.get("shipper") or booking_data.get("shipper") or job.get("customer_name")
    consignee = job.get("consignee") or booking_data.get("consignee") or "TO ORDER OF SHIPPER"
    notify_party = job.get("notify_party") or booking_data.get("notify_party") or "SAME AS CONSIGNEE"
    delivery_agent = (
        job.get("delivery_agent")
        or booking_data.get("delivery_agent")
        or job.get("overseas_agent")
        or ""
    )
    freight_term = str(job.get("freight_term") or booking_data.get("freight_term") or "FREIGHT PREPAID").upper()
    freight_payable_at = job.get("freight_payable_at") or (pol if "PREPAID" in freight_term else pod) or "ORIGIN"

    data: Dict[str, Any] = {
        "job_no": job_no,
        "shipment_id": job.get("id"),
        "booking_no": booking_no,
        "bl_type": "BL",
        "status": "Draft",
        "approval_status": "Draft",
        "consol_no": job_no,
        "consol_seq": consol_seq,
        "shipper": shipper,
        "consignee": consignee,
        "notify_party": notify_party,
        "delivery_agent": delivery_agent,
        "pre_carriage_by": job.get("pre_carriage_by") or booking_data.get("pre_carriage_by"),
        "place_of_receipt": job.get("place_of_receipt") or job.get("por") or booking_data.get("por") or booking_data.get("cy_place") or pol,
        "port_of_loading": pol,
        "port_of_discharge": pod,
        "place_of_delivery": job.get("place_of_delivery") or job.get("final_destination") or booking_data.get("final_destination") or pod,
        "final_destination": job.get("final_destination") or job.get("place_of_delivery") or booking_data.get("final_destination") or pod,
        "vessel": vessel,
        "voyage": voyage,
        "etd": etd,
        "eta": eta,
        "freight_term": freight_term,
        "freight_payable_at": freight_payable_at,
        "place_of_issue": job.get("place_of_issue") or "THAILAND",
        "number_of_originals": job.get("number_of_originals") or 3,
        "marks_numbers": marks_numbers,
        "description_of_goods": job.get("commodity") or job.get("combine_commodity") or booking_data.get("commodity") or "SAID TO CONTAIN GENERAL MERCHANDISE",
        "hs_code": job.get("hs_code") or booking_data.get("hs_code"),
        "package_qty": package_qty,
        "package_type": package_type,
        "gross_weight": gross_weight,
        "measurement_cbm": measurement_cbm,
        "created_by": user.get("username", "system"),
        "tenant_id": tenant,
    }
    if overrides:
        data.update(overrides)

    if not data.get("bl_no"):
        data["bl_no"] = generate_company_bl_no(
            data.get("port_of_loading") or pol,
            data.get("port_of_discharge") or pod,
            data.get("etd") or etd,
        )

    allowed = {
        "tenant_id", "bl_no", "job_no", "shipment_id", "booking_no", "consol_no", "consol_seq",
        "shipper", "consignee", "notify_party", "delivery_agent", "pre_carriage_by", "place_of_receipt",
        "port_of_loading", "port_of_discharge", "place_of_delivery", "final_destination", "vessel", "voyage",
        "etd", "eta", "bl_date", "place_of_issue", "number_of_originals", "freight_term", "freight_payable_at",
        "marks_numbers", "package_qty", "package_type", "description_of_goods", "gross_weight", "measurement_cbm",
        "hs_code", "remarks", "special_instructions", "bl_type", "status", "approval_status", "created_by",
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
            bl_id = row["id"] if isinstance(row, dict) else row[0]

            # 7. Automatically associate containers into bl_containers junction
            for c in containers:
                c_id = c.get("id")
                if c_id:
                    try:
                        cur.execute(
                            "INSERT INTO bl_containers (bl_id, container_id) VALUES (%s, %s) ON CONFLICT DO NOTHING",
                            (bl_id, c_id)
                        )
                    except Exception:
                        pass

            conn.commit()
            return bl_id


def update_bl(bl_id: int, patch: Dict[str, Any]) -> bool:
    doc = get_bl(bl_id)
    if not doc:
        raise ValueError("B/L not found.")
    if doc.get("status") in {"Issued", "Surrendered", "Cancelled"}:
        raise ValueError(f"B/L is {doc.get('status')} and cannot be edited.")

    allowed = {
        "shipper", "consignee", "notify_party", "delivery_agent", "pre_carriage_by", "place_of_receipt",
        "port_of_loading", "port_of_discharge", "place_of_delivery", "final_destination", "vessel", "voyage",
        "etd", "eta", "bl_date", "place_of_issue", "number_of_originals", "freight_term", "freight_payable_at",
        "marks_numbers", "package_qty", "package_type", "description_of_goods", "gross_weight", "measurement_cbm",
        "hs_code", "remarks", "special_instructions",
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
