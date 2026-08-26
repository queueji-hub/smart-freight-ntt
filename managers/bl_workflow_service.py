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


def detect_transport_mode(
    job: Optional[Dict[str, Any]] = None,
    booking: Optional[Dict[str, Any]] = None,
    bl: Optional[Dict[str, Any]] = None,
) -> tuple[str, str, str]:
    """Detect (transport_mode, doc_type, doc_title) from job, booking, or B/L data."""
    job_d = job or {}
    bk_d = booking or {}
    bl_d = bl or {}

    raw_candidates = [
        bl_d.get("transport_mode"),
        bl_d.get("doc_title"),
        bl_d.get("doc_type"),
        bl_d.get("job_type"),
        bl_d.get("mode"),
        job_d.get("job_type"),
        job_d.get("mode"),
        job_d.get("cargo_type"),
        job_d.get("service_type"),
        job_d.get("transport"),
        bk_d.get("job_type"),
        bk_d.get("mode"),
        bk_d.get("cargo_type"),
        bk_d.get("service_type"),
    ]
    tokens = [str(x).strip().upper() for x in raw_candidates if x is not None and str(x).strip()]
    scope = " ".join(tokens + [
        str(bl_d.get("bl_no") or "").upper(),
        str(job_d.get("job_no") or "").upper(),
        str(bk_d.get("booking_no") or "").upper(),
        str(bk_d.get("truck_plate") or "").upper(),
        str(bk_d.get("flight_no") or "").upper(),
    ])

    # 1. Check explicit fields
    if bk_d.get("flight_no") or bl_d.get("flight_no") or job_d.get("flight_no") or bl_d.get("mawb_no") or bk_d.get("mawb_no") or bl_d.get("hawb_no") or bk_d.get("hawb_no"):
        return "AIR", "AIR_WAYBILL", "AIR WAYBILL"

    if bk_d.get("truck_plate") or bl_d.get("truck_plate") or job_d.get("truck_plate") or bk_d.get("driver_name") or bl_d.get("driver_name"):
        return "TRUCK", "TRUCK_WAYBILL", "TRUCK WAYBILL"

    # 2. Check AIR
    air_codes = {"AE", "AI", "AIR", "AIR_EXP", "AIR_IMP", "AIRCRAFT", "AIRWAY", "HAWB", "AWB"}
    if any(t in air_codes for t in tokens) or any(k in scope for k in ["AIR", "FLIGHT", "เครื่องบิน", "AERO", "AWB", "HAWB"]):
        return "AIR", "AIR_WAYBILL", "AIR WAYBILL"

    # 3. Check TRUCK / ROAD / LAND
    truck_codes = {"TE", "TI", "TRUCK", "TRK", "ROAD", "LAND", "TRK_EXP", "TRK_IMP", "CROSSBORDER", "CROSS_BORDER", "CROSS BORDER", "TRUCKING", "TWB"}
    if any(t in truck_codes for t in tokens) or any(k in scope for k in ["TRUCK", "ROAD", "LAND", "รถ", "CROSSBORDER", "CROSS BORDER", "TRK", "TWB"]):
        return "TRUCK", "TRUCK_WAYBILL", "TRUCK WAYBILL"

    # 4. Default to SEA
    return "SEA", "OCEAN_BL", "OCEAN BILL OF LADING"


def _normalize_bl_dict(d: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not d:
        return d
    row = dict(d)
    if not row.get("transport_mode") or not row.get("doc_title"):
        t_mode, d_type, d_title = detect_transport_mode(bl=row)
        row["transport_mode"] = t_mode
        row["doc_type"] = d_type
        row["doc_title"] = d_title
    return row



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
            return [_normalize_bl_dict(dict(row)) for row in cur.fetchall()]


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
            return _normalize_bl_dict(dict(row)) if row else None


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

    # 2. Detect Transport Mode & Document Type
    transport_mode, doc_type, doc_title = detect_transport_mode(job=job, booking=booking_data, bl=overrides)
    if overrides and overrides.get("doc_title"):
        doc_title = overrides["doc_title"]
        if "AIR" in doc_title:
            transport_mode, doc_type = "AIR", "AIR_WAYBILL"
        elif "TRUCK" in doc_title:
            transport_mode, doc_type = "TRUCK", "TRUCK_WAYBILL"
        else:
            transport_mode, doc_type = "SEA", "OCEAN_BL"

    # 3. Fetch linked Containers for Marks & Numbers and accurate Cargo Metrics
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

    # 4. Assemble Marks & Numbers from Container + Seal details
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

    # 5. Resolve Cargo Metrics with Container Fallbacks
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

    # 6. Resolve Routing and Transport
    pol = job.get("pol") or job.get("port_of_loading") or booking_data.get("pol") or "BANGKOK, THAILAND"
    pod = job.get("pod") or job.get("port_of_discharge") or booking_data.get("pod") or "SINGAPORE"
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

    # 7. Resolve Parties & Freight Terms
    shipper = job.get("shipper") or booking_data.get("shipper") or job.get("customer_name") or ""
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

    # 8. Resolve Mode-Specific Parameters
    flight_no = job.get("flight_no") or booking_data.get("flight_no") or ""
    flight_date = _safe_date(job.get("flight_date") or booking_data.get("flight_date") or etd)
    mawb_no = job.get("mawb_no") or booking_data.get("mawb_no") or ""
    hawb_no = job.get("hawb_no") or booking_data.get("hawb_no") or ""
    airport_dep = pol
    airport_dest = pod
    first_carrier = job.get("carrier") or booking_data.get("carrier") or "THAI AIRWAYS"
    chargeable_wt = float(booking_data.get("chargeable_weight") or max(gross_weight, measurement_cbm * 166.67 if measurement_cbm else gross_weight) or gross_weight)
    cargo_term = str(job.get("cargo_type") or booking_data.get("cargo_type") or "").upper()
    truck_type = booking_data.get("truck_type") or job.get("truck_type") or ("Full Truck Load (FTL)" if "FCL" in cargo_term or "FTL" in cargo_term else "Less Truck Load (LTL)")
    truck_plate = booking_data.get("truck_plate") or job.get("truck_plate") or ""
    driver_name = booking_data.get("driver_name") or job.get("driver_name") or ""
    driver_phone = booking_data.get("driver_phone") or job.get("driver_phone") or ""
    volumetric_wt = float(booking_data.get("volumetric_weight") or (measurement_cbm * 333.33 if measurement_cbm else gross_weight) or 0)
    customer_ref = job.get("customer_reference") or booking_no or job_no

    data: Dict[str, Any] = {
        "job_no": job_no,
        "shipment_id": job.get("id"),
        "booking_no": booking_no,
        "bl_type": "BL",
        "transport_mode": transport_mode,
        "doc_type": doc_type,
        "doc_title": doc_title,
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
        # Air fields
        "flight_no": flight_no,
        "flight_date": flight_date,
        "airport_departure": airport_dep,
        "airport_destination": airport_dest,
        "first_carrier": first_carrier,
        "to_carrier_1": pod[:3].upper() if pod else "",
        "by_carrier_1": first_carrier[:2].upper() if first_carrier else "TG",
        "iata_code": "33-4-7890/0014",
        "agent_account_no": "BKK-0988",
        "exporter_account_no": "",
        "consignee_account_no": "",
        "accounting_info": "FREIGHT PREPAID / ISSUED AS PER AGREEMENT",
        "declared_value_carriage": "NVD",
        "declared_value_customs": "NCV",
        "amount_of_insurance": "XXX",
        "handling_info": "NO SPECIAL HANDLING REQUIRED / GENERAL CARGO",
        "sci": "TH-EXP",
        "chargeable_weight": chargeable_wt,
        "rate_class": "Q",
        "commodity_item_no": job.get("hs_code") or "",
        "rate_charge": 0.0,
        "total_charge": 0.0,
        "weight_charge_ppd": 0.0,
        "weight_charge_coll": 0.0,
        "valuation_charge_ppd": 0.0,
        "valuation_charge_coll": 0.0,
        "tax_ppd": 0.0,
        "tax_coll": 0.0,
        "other_charges_agent_ppd": 0.0,
        "other_charges_agent_coll": 0.0,
        "other_charges_carrier_ppd": 0.0,
        "other_charges_carrier_coll": 0.0,
        "other_charges_desc": "",
        "total_prepaid": 0.0,
        "total_collect": 0.0,
        "currency": job.get("currency") or "USD",
        "chgs_code": "PP" if "PREPAID" in freight_term else "CC",
        "wt_val_ppd": "P" if "PREPAID" in freight_term else "",
        "wt_val_coll": "C" if "COLLECT" in freight_term else "",
        "other_ppd": "P" if "PREPAID" in freight_term else "",
        "other_coll": "C" if "COLLECT" in freight_term else "",
        # Truck fields
        "truck_waybill_no": "",
        "truck_type": truck_type,
        "truck_plate": truck_plate,
        "driver_name": driver_name,
        "driver_phone": driver_phone,
        "booking_party": job.get("customer_name") or shipper,
        "origin": pol,
        "destination": pod,
        "volumetric_weight": volumetric_wt,
        "dimension": booking_data.get("dimension") or "AS PER PACKING LIST",
        "invoice_details": job.get("invoice_no") or booking_data.get("quotation_no") or "INV-COMMERCIAL",
        "customer_ref_no": customer_ref,
        "move_type": truck_type,
        "freight_charges": 0.0,
        "duty_other_charges": 0.0,
        "origin_charges": 0.0,
        "destination_charges": 0.0,
        "created_by": user.get("username", "system"),
        "tenant_id": tenant,
    }
    if overrides:
        data.update(overrides)

    if not data.get("bl_no"):
        if transport_mode == "AIR":
            from managers.bl_consolidation_service import generate_air_waybill_no
            data["bl_no"] = generate_air_waybill_no(pol, pod, data.get("etd") or etd)
        elif transport_mode == "TRUCK":
            from managers.bl_consolidation_service import generate_truck_waybill_no
            data["bl_no"] = generate_truck_waybill_no(pol, pod, data.get("etd") or etd)
        else:
            data["bl_no"] = generate_company_bl_no(
                data.get("port_of_loading") or pol,
                data.get("port_of_discharge") or pod,
                data.get("etd") or etd,
            )

    if transport_mode == "TRUCK" and not data.get("truck_waybill_no"):
        data["truck_waybill_no"] = data["bl_no"]

    allowed = {
        "tenant_id", "bl_no", "job_no", "shipment_id", "booking_no", "consol_no", "consol_seq",
        "shipper", "consignee", "notify_party", "delivery_agent", "pre_carriage_by", "place_of_receipt",
        "port_of_loading", "port_of_discharge", "place_of_delivery", "final_destination", "vessel", "voyage",
        "etd", "eta", "bl_date", "place_of_issue", "number_of_originals", "freight_term", "freight_payable_at",
        "marks_numbers", "package_qty", "package_type", "description_of_goods", "gross_weight", "measurement_cbm",
        "hs_code", "remarks", "special_instructions", "bl_type", "status", "approval_status", "created_by",
        "transport_mode", "doc_type", "doc_title",
        "flight_no", "flight_date", "airport_departure", "airport_destination", "first_carrier",
        "to_carrier_1", "by_carrier_1", "to_carrier_2", "by_carrier_2", "iata_code", "agent_account_no",
        "exporter_account_no", "consignee_account_no", "accounting_info", "declared_value_carriage",
        "declared_value_customs", "amount_of_insurance", "handling_info", "sci", "chargeable_weight",
        "rate_class", "commodity_item_no", "rate_charge", "total_charge", "weight_charge_ppd",
        "weight_charge_coll", "valuation_charge_ppd", "valuation_charge_coll", "tax_ppd", "tax_coll",
        "other_charges_agent_ppd", "other_charges_agent_coll", "other_charges_carrier_ppd",
        "other_charges_carrier_coll", "other_charges_desc", "total_prepaid", "total_collect", "currency",
        "chgs_code", "wt_val_ppd", "wt_val_coll", "other_ppd", "other_coll",
        "truck_waybill_no", "truck_type", "truck_plate", "driver_name", "driver_phone", "booking_party",
        "origin", "destination", "volumetric_weight", "dimension", "invoice_details", "customer_ref_no",
        "move_type", "freight_charges", "duty_other_charges", "origin_charges", "destination_charges",
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

            # Associate containers into bl_containers junction
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
        "hs_code", "remarks", "special_instructions", "transport_mode", "doc_type", "doc_title",
        "flight_no", "flight_date", "airport_departure", "airport_destination", "first_carrier",
        "to_carrier_1", "by_carrier_1", "to_carrier_2", "by_carrier_2", "iata_code", "agent_account_no",
        "exporter_account_no", "consignee_account_no", "accounting_info", "declared_value_carriage",
        "declared_value_customs", "amount_of_insurance", "handling_info", "sci", "chargeable_weight",
        "rate_class", "commodity_item_no", "rate_charge", "total_charge", "weight_charge_ppd",
        "weight_charge_coll", "valuation_charge_ppd", "valuation_charge_coll", "tax_ppd", "tax_coll",
        "other_charges_agent_ppd", "other_charges_agent_coll", "other_charges_carrier_ppd",
        "other_charges_carrier_coll", "other_charges_desc", "total_prepaid", "total_collect", "currency",
        "chgs_code", "wt_val_ppd", "wt_val_coll", "other_ppd", "other_coll",
        "truck_waybill_no", "truck_type", "truck_plate", "driver_name", "driver_phone", "booking_party",
        "origin", "destination", "volumetric_weight", "dimension", "invoice_details", "customer_ref_no",
        "move_type", "freight_charges", "duty_other_charges", "origin_charges", "destination_charges",
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
