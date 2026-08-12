from managers.tenant_context import get_current_tenant_id
from typing import List, Dict, Any, Optional
import json
from datetime import datetime, date
from database.connection import get_connection
from managers.document_numbering_service import generate_document_number, normalize_doc_no
from core.audit import log_action
from managers.shipment_manager import create_shipment


# =========================================================
# CREATE BOOKING (SAAS READY)
# =========================================================

def create_booking(data: Dict[str, Any], user: Dict[str, Any] = None) -> str:
    """
    Create booking from quotation
    SaaS version (tenant-safe + audit)
    """
    tenant_id = get_current_tenant_id()
    
    if user is None:
        user = {"id": 1}

    provided_bno = (data.get("booking_no") or "").strip()
    if provided_bno:
        booking_no = provided_bno
    else:
        booking_no = generate_document_number("BK", data.get("created_at"))

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO bookings (
                    tenant_id,
                    booking_no,
                    job_type,
                    customer_id,
                    customer_name,
                    shipper,
                    consignee,
                    notify_party,
                    pol,
                    por,
                    pod,
                    final_destination,
                    transhipment_port,
                    cy_date,
                    cy_place,
                    cfs_date,
                    cfs_place,
                    customer_return_date,
                    return_place,
                    etd,
                    eta,
                    carrier,
                    m_vessel,
                    feeder,
                    liner,
                    vessel,
                    voyage,
                    closing_time,
                    cargo_type,
                    container_summary,
                    gross_weight,
                    measurement_cbm,
                    package_qty,
                    quantity,
                    package_unit,
                    commodity,
                    freight_term,
                    remark,
                    quotation_id,
                    status,
                    created_by
                )
                VALUES (
                    %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,
                    %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,
                    %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,
                    %s,%s,%s,%s,%s,%s,%s,%s,%s,'DRAFT',%s
                )
            """, (
                tenant_id,
                booking_no,
                data.get("job_type"),
                data.get("customer_id"),
                data.get("customer_name"),
                data.get("shipper"),
                data.get("consignee"),
                data.get("notify_party"),
                data.get("pol"),
                data.get("por"),
                data.get("pod"),
                data.get("final_destination"),
                data.get("transhipment_port"),
                data.get("cy_date"),
                data.get("cy_place"),
                data.get("cfs_date"),
                data.get("cfs_place"),
                data.get("customer_return_date"),
                data.get("return_place"),
                data.get("etd"),
                data.get("eta"),
                data.get("carrier"),
                data.get("m_vessel"),
                data.get("feeder"),
                data.get("liner"),
                data.get("vessel"),
                data.get("voyage"),
                data.get("closing_time"),
                data.get("cargo_type"),
                data.get("container_summary"),
                data.get("gross_weight"),
                data.get("measurement_cbm"),
                data.get("package_qty"),
                data.get("quantity"),
                data.get("package_unit"),
                data.get("commodity"),
                data.get("freight_term"),
                data.get("remark"),
                data.get("quotation_id"),
                data.get("created_by")
            ))

            conn.commit()

        log_action(
            user.get("id", 1),
            tenant_id,
            "booking",
            booking_no,
            "CREATE"
        )

        return booking_no


# =========================================================
# GET BOOKING
# =========================================================

def get_booking(booking_no: str, tenant_id: str = None) -> Optional[Dict[str, Any]]:
    tenant_id = get_current_tenant_id()
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT *
                FROM bookings
                WHERE booking_no=%s AND tenant_id=%s
            """, (booking_no, tenant_id))
            row = cur.fetchone()
            return dict(row) if row else None


# =========================================================
# LIST BOOKINGS
# =========================================================

def list_bookings(
    tenant_id: str = None,
    status: str = None,
    job_type: str = None,
    customer_id: int = None,
    search_query: str = None,
    etd_start: Any = None,
    etd_end: Any = None,
    eta_start: Any = None,
    eta_end: Any = None,
    limit: int = 200
) -> List[Dict[str, Any]]:

    tenant_id = get_current_tenant_id()

    sql = """
        SELECT *
        FROM bookings
        WHERE tenant_id=%s
    """

    params = [tenant_id]

    if status and status != "All Statuses":
        sql += " AND status=%s"
        params.append(status)

    if job_type and job_type != "All Types":
        sql += " AND job_type=%s"
        params.append(job_type)

    if customer_id:
        sql += " AND customer_id=%s"
        params.append(customer_id)

    if etd_start:
        sql += " AND etd >= %s"
        params.append(str(etd_start))

    if etd_end:
        sql += " AND etd <= %s"
        params.append(str(etd_end))

    if eta_start:
        sql += " AND eta >= %s"
        params.append(str(eta_start))

    if eta_end:
        sql += " AND eta <= %s"
        params.append(str(eta_end))

    if search_query and search_query.strip():
        normalized_search = normalize_doc_no(search_query)
        q = f"%{search_query.strip().lower()}%"
        nq = f"%{normalized_search.lower()}%"
        sql += """ AND (
            REPLACE(REPLACE(UPPER(booking_no), '-', ''), ' ', '') LIKE %s OR
            LOWER(booking_no) LIKE %s OR 
            LOWER(COALESCE(job_no, '')) LIKE %s OR 
            LOWER(customer_name) LIKE %s OR 
            LOWER(pol) LIKE %s OR 
            LOWER(pod) LIKE %s OR 
            LOWER(shipper) LIKE %s OR 
            LOWER(consignee) LIKE %s OR 
            LOWER(vessel) LIKE %s OR 
            LOWER(voyage) LIKE %s
        )"""
        params.extend([f"%{normalized_search}%", q, q, q, q, q, q, q, q, q])

    sql += " ORDER BY created_at DESC LIMIT %s"
    params.append(limit)

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()
            return [dict(r) for r in rows]


# =========================================================
# UPDATE BOOKING (SAFE + AUDIT)
# =========================================================

def can_transition_booking_status(current_status: str, new_status: str) -> tuple[bool, str]:
    """
    Central validation function for status lifecycle.
    DRAFT -> SUBMITTED -> CONFIRMED -> CONVERTED
    DRAFT -> CANCELLED
    """
    c = current_status.upper() if current_status else "DRAFT"
    n = new_status.upper() if new_status else "DRAFT"
    
    if c == n:
        return True, "Same status."
        
    if c in ["CONVERTED", "CONVERTED TO JOB"]:
        return False, "Cannot change status of a converted Booking."
        
    if c == "CANCELLED":
        return False, "Cannot change status of a cancelled Booking."
        
    valid_transitions = {
        "DRAFT": ["SUBMITTED", "CANCELLED"],
        "SUBMITTED": ["DRAFT", "CONFIRMED", "CANCELLED"],
        "CONFIRMED": ["SUBMITTED", "CONVERTED", "CONVERTED TO JOB", "CANCELLED"]
    }
    
    allowed = valid_transitions.get(c, [])
    if n in allowed:
        return True, "Allowed"
        
    return False, f"Invalid transition from {c} to {n}."


def update_booking(booking_no: str, data: Dict[str, Any], tenant_id: str = None) -> bool:
    
    tenant_id = get_current_tenant_id()
    existing = get_booking(booking_no, tenant_id)
    if not existing:
        return False
        
    current_status = existing.get("status", "DRAFT").upper()
    
    # Block editing if locked
    if current_status in ["CONVERTED", "CONVERTED TO JOB", "CANCELLED"]:
        # If the only field being updated is status, check transition (which will fail anyway due to transition rules, but let it proceed to status check)
        if set(data.keys()) - {"status"} and not (len(data.keys()) == 1 and "status" in data):
            raise ValueError(f"Booking is LOCKED (Status: {current_status}). Modifications are not permitted.")

    if "status" in data:
        new_status = data["status"].upper()
        allowed, reason = can_transition_booking_status(current_status, new_status)
        if not allowed:
            raise ValueError(reason)

    # Restrict fields for CONFIRMED (Require Controlled Revision for field changes)
    if current_status == "CONFIRMED" and set(data.keys()) - {"status", "job_no"}:
        raise ValueError("Cannot modify fields on a CONFIRMED booking directly. Create a Controlled Revision first.")

    allowed_fields = {
        "customer_id", "customer_name", "shipper", "consignee",
        "notify_party", "pol", "por", "pod", "final_destination",
        "transhipment_port", "cy_date", "cy_place", "cfs_date",
        "cfs_place", "customer_return_date", "return_place",
        "etd", "eta", "carrier", "m_vessel", "feeder", "liner",
        "vessel", "voyage", "closing_time", "cargo_type", "container_summary",
        "gross_weight", "measurement_cbm", "package_qty", "quantity",
        "package_unit", "commodity", "freight_term", "remark", "status", "quotation_id"
    }

    sets = []
    params = []

    for key in allowed_fields:
        if key in data:
            sets.append(f"{key}=%s")
            params.append(data[key])

    if not sets:
        return False

    params.append(booking_no)
    params.append(tenant_id)

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(f"""
                UPDATE bookings
                SET {', '.join(sets)},
                    updated_at=CURRENT_TIMESTAMP
                WHERE booking_no=%s AND tenant_id=%s
            """, params)

            conn.commit()

            return cur.rowcount > 0


# =========================================================
# DELETE BOOKING
# =========================================================

def delete_booking(booking_no: str, tenant_id: str = None) -> bool:
    
    tenant_id = get_current_tenant_id()
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                DELETE FROM bookings 
                WHERE booking_no=%s AND tenant_id=%s
            """, (booking_no, tenant_id))
            affected = cur.rowcount

            if affected > 0:
                conn.commit()
                return True
            return False


# =========================================================
# CONVERT BOOKING TO JOB
# =========================================================

def convert_booking_to_job(booking_no: str, user: dict) -> str:
    """
    Converts a confirmed booking into a billable operational job (shipment).
    Copies all relevant routing and cargo fields.
    Updates the booking status to 'CONVERTED TO JOB'.
    """
    tenant_id = get_current_tenant_id()
    
    # 1. Quick read check to get job_type & etd for job_no generation outside transaction
    existing = get_booking(booking_no, tenant_id)
    if not existing:
        raise ValueError("Booking not found.")
    if existing.get("status") in ["CONVERTED", "CONVERTED TO JOB"]:
        # Find existing job_no if already converted
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT job_no FROM shipments WHERE booking_no = %s", (booking_no,))
                ship_row = cur.fetchone()
                if ship_row:
                    return ship_row["job_no"]
        return existing.get("job_no", "")

    if str(existing.get("status", "")).upper() != "CONFIRMED":
        raise ValueError("Only CONFIRMED bookings can be converted to a Job.")

    from managers.document_numbering_service import generate_document_number
    job_no = generate_document_number(
        "JOB",
        existing.get("etd")
    )
    
    with get_connection() as conn:
        try:
            with conn.cursor() as cur:
                # 2. Atomic Status Update
                cur.execute(
                    "UPDATE bookings SET status = %s, job_no = %s WHERE booking_no = %s AND tenant_id = %s AND status = 'CONFIRMED'",
                    ("CONVERTED TO JOB", job_no, booking_no, tenant_id)
                )
                
                if cur.rowcount == 0:
                    raise ValueError("Only CONFIRMED bookings can be converted to a Job.")
                
                # 3. Fetch full booking details
                cur.execute("SELECT * FROM bookings WHERE booking_no = %s AND tenant_id = %s", (booking_no, tenant_id))
                booking = dict(cur.fetchone())

                # Fetch salesperson from original quotation for salesperson performance tracking continuity
                salesperson = None
                q_id = booking.get("quotation_id")
                q_ref = booking.get("quotation_no")
                if q_id:
                    cur.execute("SELECT salesperson FROM quotations WHERE id = %s AND tenant_id = %s LIMIT 1", (q_id, tenant_id))
                    q_row = cur.fetchone()
                    if q_row:
                        salesperson = q_row["salesperson"] if isinstance(q_row, dict) else q_row[0]
                elif q_ref:
                    cur.execute("SELECT salesperson FROM quotations WHERE quotation_no = %s AND tenant_id = %s LIMIT 1", (q_ref, tenant_id))
                    q_row = cur.fetchone()
                    if q_row:
                        salesperson = q_row["salesperson"] if isinstance(q_row, dict) else q_row[0]
                
                # 4. Insert Shipment
                from managers.shipment_manager import SHIPMENT_FIELDS
                
                job_payload = {
                    "booking_no": booking_no,
                    "quotation_no": str(booking.get("quotation_id")) if booking.get("quotation_id") else None,
                    "job_type": booking.get("job_type"),
                    "customer_name": booking.get("customer_name"),
                    "notify_party": booking.get("notify_party"),
                    "sales_person": salesperson,
                    "shipper": booking.get("shipper"),
                    "consignee": booking.get("consignee"),
                    "cargo_type": booking.get("cargo_type"),
                    "carrier": booking.get("carrier"),
                    "place_of_receipt": booking.get("por"),
                    "pol": booking.get("pol"),
                    "transshipment_port": booking.get("transhipment_port"),
                    "pod": booking.get("pod"),
                    "final_destination": booking.get("final_destination"),
                    "etd": booking.get("etd"),
                    "eta": booking.get("eta"),
                    "vessel": booking.get("vessel"),
                    "voyage": booking.get("voyage"),
                    "freight_term": booking.get("freight_term"),
                    "commodity": booking.get("commodity"),
                    "package_quantity": booking.get("package_qty"),
                    "package_type": booking.get("package_unit"),
                    "gross_weight": booking.get("gross_weight"),
                    "cbm": booking.get("measurement_cbm"),
                    "created_by": user.get("username", "system"),
                    "status": "Proceed",
                    "actual_departure": None,
                    "actual_arrival": None
                }
                
                from managers.shipment_manager import get_reporting_period
                rep_month, rep_year = get_reporting_period(job_payload)
                job_payload["reporting_month"] = rep_month
                job_payload["reporting_year"] = rep_year
                
                data = {k: v for k, v in job_payload.items() if k in SHIPMENT_FIELDS}
                cols = ["job_no"] + list(data.keys())
                vals = [job_no] + list(data.values())
                
                placeholders = ", ".join(["%s"] * len(cols))
                columns = ", ".join(cols)
                
                cur.execute(
                    f"INSERT INTO shipments ({columns}) VALUES ({placeholders})",
                    tuple(vals)
                )
                
                # Fetch shipment ID
                cur.execute("SELECT id FROM shipments WHERE job_no = %s AND tenant_id = %s", (job_no, tenant_id))
                ship_row_new = cur.fetchone()
                if ship_row_new:
                    shipment_id = ship_row_new["id"]
                    # Idempotent JOB CREATED milestone insert
                    cur.execute(
                        "SELECT id FROM shipment_milestones WHERE shipment_id = %s AND milestone_code = 'JOB_CREATED' AND tenant_id = %s",
                        (shipment_id, tenant_id)
                    )
                    if not cur.fetchone():
                        from datetime import datetime
                        cur.execute(
                            """
                            INSERT INTO shipment_milestones 
                            (shipment_id, tenant_id, milestone_code, milestone_name, planned_date, actual_date, remarks, status) 
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                            """,
                            (shipment_id, tenant_id, "JOB_CREATED", "Job Created from Booking", datetime.now(), datetime.now(), f"Auto-generated from booking {booking_no}", "Completed")
                        )

                conn.commit()
                
                from core.audit import log_action
                log_action(user.get("id", 1), tenant_id, "booking", booking_no, f"CONVERTED_TO_JOB:{job_no}")
                
                return job_no
                
        except Exception as e:
            conn.rollback()
            raise ValueError(f"Transaction failed: {e}")


# =========================================================
# BOOKING REVISION WORKFLOW
# =========================================================

def _json_serializable(obj):
    from decimal import Decimal
    if isinstance(obj, (date, datetime)):
        return obj.isoformat()
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError(f"Type {type(obj)} not serializable")


def create_booking_revision(
    booking_no: str,
    revision_reason: str,
    user: Dict[str, Any],
    tenant_id: str = None
) -> int:
    """
    Creates a controlled revision of a Booking.
    - Saves current booking state to booking_revisions table as JSON snapshot.
    - Increments revision_no on bookings table.
    - Status transitions back to DRAFT for edits.
    """
    if not revision_reason or not revision_reason.strip():
        raise ValueError("Revision reason is required.")

    tenant_id = get_current_tenant_id()
    booking = get_booking(booking_no, tenant_id)
    if not booking:
        raise ValueError("Booking not found.")

    current_status = str(booking.get("status", "DRAFT")).upper()
    if current_status in ["CONVERTED", "CONVERTED TO JOB"]:
        raise ValueError("Cannot revise a booking that has already been converted to a Job.")
    if current_status == "CANCELLED":
        raise ValueError("Cannot revise a cancelled booking.")

    rev_by = str(user.get("username", "system_actor"))
    curr_rev_no = int(booking.get("revision_no") or 0)

    # Convert snapshot dict to JSON
    snapshot_json = json.dumps(booking, default=_json_serializable)

    with get_connection() as conn:
        with conn.cursor() as cur:
            # 1. Insert snapshot into booking_revisions
            cur.execute("""
                INSERT INTO booking_revisions (
                    booking_no, revision_no, revised_by, revision_reason, snapshot, tenant_id
                )
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (booking_no, curr_rev_no, rev_by, revision_reason.strip(), snapshot_json, tenant_id))

            # 2. Increment revision_no and set status back to DRAFT for editing
            new_rev_no = curr_rev_no + 1
            cur.execute("""
                UPDATE bookings
                SET revision_no = %s,
                    status = 'DRAFT',
                    revision_reason = %s,
                    revised_by = %s,
                    revised_at = CURRENT_TIMESTAMP,
                    updated_at = CURRENT_TIMESTAMP
                WHERE booking_no = %s AND tenant_id = %s
            """, (new_rev_no, revision_reason.strip(), rev_by, booking_no, tenant_id))

            conn.commit()

    log_action(
        user.get("id", 1),
        tenant_id,
        "booking",
        booking_no,
        f"REVISE:REV_{new_rev_no}"
    )

    return new_rev_no


def get_revision_history(booking_no: str) -> List[Dict[str, Any]]:
    """Fetches full revision history snapshots for a given booking_no."""
    tenant_id = get_current_tenant_id()
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, booking_no, revision_no, revised_by, revised_at, revision_reason, snapshot, created_at
                FROM booking_revisions
                WHERE booking_no = %s AND tenant_id = %s
                ORDER BY revision_no DESC
            """, (booking_no, tenant_id))
            rows = cur.fetchall()
            results = []
            for r in rows:
                row_dict = dict(r)
                if row_dict.get("snapshot"):
                    try:
                        row_dict["parsed_snapshot"] = json.loads(row_dict["snapshot"])
                    except Exception:
                        row_dict["parsed_snapshot"] = {}
                results.append(row_dict)
            return results


def get_booking_revision(booking_no: str, revision_no: int) -> Optional[Dict[str, Any]]:
    """Fetches a specific historical revision snapshot."""
    tenant_id = get_current_tenant_id()
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT * FROM booking_revisions
                WHERE booking_no = %s AND revision_no = %s AND tenant_id = %s
            """, (booking_no, revision_no, tenant_id))
            row = cur.fetchone()
            if row:
                row_dict = dict(row)
                if row_dict.get("snapshot"):
                    try:
                        row_dict["parsed_snapshot"] = json.loads(row_dict["snapshot"])
                    except Exception:
                        row_dict["parsed_snapshot"] = {}
                return row_dict
            return None