"""Shipping Instruction (S/I) business logic and payload assembly service.

Handles:
- Direct B/L mode: Actual Shipper, Actual Consignee, Actual Notify Party from customer data.
- Agent B/L (HBL) mode:
  - Shipper: Official Nattayaarat Head Office entity:
      NATTAYAARAT CO., LTD.
      59/9 THE BALANZ ZIGMA VILLAGE. MOO4, SOI BANGKRATHUEK 3,
      BANGKRATHUEK SUBDISTRICT, SAMPHRAN DISTRICT, NAKHON
      PATHOM PROVINCE 73210
      TAX ID: 073-556-800-4823
  - Consignee: Destination Delivery Agent ("For Delivery of Goods Please Apply to :")
  - Notify Party: "SAME AS CONSIGNEE"
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Any, Dict, List, Optional

from database.connection import get_connection
from managers.tenant_context import get_current_tenant_id
from managers.shipment_manager import get_shipment, list_job_containers
from managers.bl_workflow_service import list_bls
from managers.document_numbering_service import generate_document_number

NATTAYAARAT_OFFICIAL_SHIPPER = (
    "NATTAYAARAT CO., LTD.\n"
    "59/9 THE BALANZ ZIGMA VILLAGE. MOO4, SOI BANGKRATHUEK 3,\n"
    "BANGKRATHUEK SUBDISTRICT, SAMPHRAN DISTRICT, NAKHON\n"
    "PATHOM PROVINCE 73210\n"
    "TAX ID: 073-556-800-4823"
)
NATTAYAARAT_OFFICIAL_CONSIGNEE = NATTAYAARAT_OFFICIAL_SHIPPER


def _s(val: Any, default: str = "") -> str:
    if val is None:
        return default
    text = str(val).strip()
    return default if text.lower() in {"", "none", "nan", "nat"} else text


def assemble_si_payload(
    job_no: str,
    si_mode: str = "direct",
    overrides: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Assemble the complete Shipping Instruction (S/I) payload.

    Args:
        job_no: Authoritative Job identifier
        si_mode: "direct" (Direct Master B/L) or "hbl" / "agent" (Agent B/L for HBL issuance)
        overrides: Optional UI overrides for any field

    Returns:
        Dict[str, Any] with all resolved S/I fields ready for PDF rendering.
    """
    overrides = overrides or {}
    job = get_shipment(job_no) or {}
    if not job:
        raise ValueError(f"Job '{job_no}' not found.")

    # Retrieve attached B/L if existing
    bl_records = list_bls(job_no=job_no) or []
    bl = bl_records[0] if bl_records else {}

    # Retrieve containers
    containers = list_job_containers(job_no) or []

    is_hbl_mode = str(si_mode).strip().lower() in {"hbl", "agent", "agent_bl"}
    mode_label = "AGENT B/L (HBL MODE)" if is_hbl_mode else "DIRECT B/L"

    # 1. Resolve Parties
    agent_info = _s(job.get("delivery_agent") or bl.get("delivery_agent") or "")
    
    if is_hbl_mode:
        # In HBL mode: Shipper on Ocean S/I is Nattayaarat, Consignee is the Destination Agent, Notify is SAME AS CONSIGNEE
        shipper = overrides.get("shipper") or NATTAYAARAT_OFFICIAL_SHIPPER
        consignee = overrides.get("consignee") or agent_info or "OVERSEAS AGENT / FORWARDER PARTNER"
        notify_party = overrides.get("notify_party") or "SAME AS CONSIGNEE"
    else:
        # In Direct mode: actual commercial customer data
        shipper = overrides.get("shipper") or _s(bl.get("shipper") or job.get("shipper"))
        consignee = overrides.get("consignee") or _s(bl.get("consignee") or job.get("consignee"))
        notify_party = overrides.get("notify_party") or _s(bl.get("notify_party") or job.get("notify_party") or "SAME AS CONSIGNEE")

    delivery_agent = overrides.get("delivery_agent") or agent_info

    # 2. Resolve S/I & Carrier References
    si_date = overrides.get("si_date") or date.today()
    carrier = overrides.get("carrier") or _s(job.get("carrier"))
    carrier_booking_no = overrides.get("carrier_booking_no") or _s(job.get("booking_no"))
    carrier_mbl_no = overrides.get("carrier_mbl_no") or _s(job.get("mbl_no"))
    hbl_no = overrides.get("hbl_no") or _s(job.get("hbl_no") or bl.get("bl_no"))

    # 3. Transport & Routing
    vessel = overrides.get("vessel") or _s(job.get("vessel") or bl.get("vessel"))
    voyage = overrides.get("voyage") or _s(job.get("voyage") or bl.get("voyage"))
    mother_vessel = overrides.get("mother_vessel") or _s(job.get("mother_vessel"))
    mother_voyage = overrides.get("mother_voyage") or _s(job.get("mother_voyage"))
    
    pol = overrides.get("pol") or _s(job.get("pol") or bl.get("port_of_loading"))
    pod = overrides.get("pod") or _s(job.get("pod") or bl.get("port_of_discharge"))
    transshipment = overrides.get("transshipment") or _s(job.get("transshipment_port"))
    place_of_receipt = overrides.get("place_of_receipt") or _s(job.get("place_of_receipt") or bl.get("place_of_receipt"))
    place_of_delivery = overrides.get("place_of_delivery") or _s(job.get("place_of_delivery") or bl.get("place_of_delivery") or pod)
    final_destination = overrides.get("final_destination") or _s(job.get("final_destination") or bl.get("final_destination"))
    
    etd = overrides.get("etd") or _s(job.get("etd"))
    eta = overrides.get("eta") or _s(job.get("eta"))
    
    # 4. Cargo & Terms
    freight_term = overrides.get("freight_term") or _s(job.get("freight_term") or bl.get("freight_term") or "PREPAID").upper()
    freight_payable_at = overrides.get("freight_payable_at") or _s(bl.get("freight_payable_at") or ("BANGKOK, THAILAND" if freight_term == "PREPAID" else pod))
    
    commodity = overrides.get("commodity") or _s(job.get("commodity") or bl.get("description_of_goods"))
    hs_code = overrides.get("hs_code") or _s(job.get("hs_code") or bl.get("hs_code"))
    package_qty = overrides.get("package_qty") or job.get("package_quantity") or bl.get("package_qty") or 0
    package_type = overrides.get("package_type") or _s(job.get("package_type") or bl.get("package_type") or "PACKAGES")
    gross_weight = overrides.get("gross_weight") or job.get("gross_weight") or bl.get("gross_weight") or 0.0
    net_weight = overrides.get("net_weight") or job.get("net_weight") or 0.0
    cbm = overrides.get("cbm") or job.get("cbm") or bl.get("measurement_cbm") or 0.0
    
    special_remarks = overrides.get("special_remarks") or _s(job.get("special_cargo_remarks") or job.get("remark") or bl.get("remarks"))

    payload = {
        "job_no": job_no,
        "si_mode": "hbl" if is_hbl_mode else "direct",
        "si_mode_label": mode_label,
        "si_date": si_date,
        "carrier": carrier,
        "carrier_booking_no": carrier_booking_no,
        "carrier_mbl_no": carrier_mbl_no,
        "hbl_no": hbl_no,
        "shipper": shipper,
        "consignee": consignee,
        "notify_party": notify_party,
        "delivery_agent": delivery_agent,
        "vessel": vessel,
        "voyage": voyage,
        "mother_vessel": mother_vessel,
        "mother_voyage": mother_voyage,
        "pol": pol,
        "pod": pod,
        "transshipment": transshipment,
        "place_of_receipt": place_of_receipt,
        "place_of_delivery": place_of_delivery,
        "final_destination": final_destination,
        "etd": etd,
        "eta": eta,
        "freight_term": freight_term,
        "freight_payable_at": freight_payable_at,
        "commodity": commodity,
        "hs_code": hs_code,
        "package_qty": package_qty,
        "package_type": package_type,
        "gross_weight": gross_weight,
        "net_weight": net_weight,
        "cbm": cbm,
        "special_remarks": special_remarks,
        "containers": containers,
        "prepared_by": overrides.get("prepared_by") or _s(job.get("operations_owner") or job.get("created_by") or "OPERATIONS"),
    }
    return payload
