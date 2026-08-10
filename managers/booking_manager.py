from typing import List, Dict, Any, Optional
from database.connection import get_connection
from managers.job_number import generate_job_number
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
    if user is None:
        user = {"tenant_id": "default", "id": 1}

    tenant_id = user.get("tenant_id", "default")

    booking_no = generate_job_number(
        data.get("job_type", "SE"),
        data.get("created_at"),
        tenant_id
    )

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

def get_booking(booking_no: str, tenant_id: str = "default") -> Optional[Dict[str, Any]]:

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
    tenant_id: str = "default",
    status: str = None,
    customer_id: int = None,
    limit: int = 100
) -> List[Dict[str, Any]]:

    sql = """
        SELECT *
        FROM bookings
        WHERE tenant_id=%s
    """

    params = [tenant_id]

    if status:
        sql += " AND status=%s"
        params.append(status)

    if customer_id:
        sql += " AND customer_id=%s"
        params.append(customer_id)

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


def update_booking(booking_no: str, data: Dict[str, Any], tenant_id: str = "default") -> bool:
    
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

    # Restrict fields for CONFIRMED
    if current_status == "CONFIRMED" and set(data.keys()) - {"status"}:
        restricted = {"pol", "pod", "customer_id", "job_type", "freight_term"}
        attempted_restricted = restricted.intersection(data.keys())
        if attempted_restricted:
             raise ValueError(f"Cannot modify critical routing/commercial fields ({', '.join(attempted_restricted)}) while CONFIRMED.")

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

def delete_booking(booking_no: str, tenant_id: str = "default") -> bool:

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
    tenant_id = user.get("tenant_id", "default")
    
    with get_connection() as conn:
        try:
            with conn.cursor() as cur:
                # 1. Check if already converted
                cur.execute("SELECT job_no FROM shipments WHERE booking_no = %s", (booking_no,))
                ship_row = cur.fetchone()
                if ship_row:
                    return ship_row["job_no"]
                
                # 2. Lock/Reload Booking & Atomic Status Update
                # By updating first and checking rowcount, we prevent concurrent threads from both converting.
                cur.execute(
                    "UPDATE bookings SET status = %s WHERE booking_no = %s AND tenant_id = %s AND status = 'CONFIRMED'",
                    ("CONVERTED TO JOB", booking_no, tenant_id)
                )
                
                if cur.rowcount == 0:
                    # If 0 rows updated, it was either not found, already converted, or not CONFIRMED
                    cur.execute("SELECT status FROM bookings WHERE booking_no = %s AND tenant_id = %s", (booking_no, tenant_id))
                    row = cur.fetchone()
                    if not row:
                        raise ValueError("Booking not found.")
                    raise ValueError("Only CONFIRMED bookings can be converted to a Job.")
                
                # 3. Fetch Booking details to copy
                cur.execute("SELECT * FROM bookings WHERE booking_no = %s AND tenant_id = %s", (booking_no, tenant_id))
                booking = dict(cur.fetchone())
                    
                # 4. Generate Job Number
                from managers.job_number import generate_job_number
                job_no = generate_job_number(
                    booking.get("job_type", "SE"),
                    booking.get("etd")
                )
                
                # 5. Insert Shipment
                from managers.shipment_manager import SHIPMENT_FIELDS
                
                job_payload = {
                    "booking_no": booking_no,
                    "quotation_no": str(booking.get("quotation_id")) if booking.get("quotation_id") else None,
                    "job_type": booking.get("job_type"),
                    "customer_name": booking.get("customer_name"),
                    "notify_party": booking.get("notify_party"),
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
                cur.execute("SELECT id FROM shipments WHERE job_no = %s", (job_no,))
                ship_row_new = cur.fetchone()
                if ship_row_new:
                    shipment_id = ship_row_new["id"]
                    # Idempotent JOB CREATED milestone insert
                    cur.execute(
                        "SELECT id FROM shipment_milestones WHERE job_no = %s AND milestone_code = 'JOB_CREATED'",
                        (job_no,)
                    )
                    if not cur.fetchone():
                        from datetime import datetime
                        cur.execute(
                            """
                            INSERT INTO shipment_milestones 
                            (shipment_id, job_no, milestone_code, milestone_name, event_date, remark, created_by) 
                            VALUES (%s, %s, %s, %s, %s, %s, %s)
                            """,
                            (shipment_id, job_no, "JOB_CREATED", "Job Created from Booking", datetime.now(), f"Auto-generated from booking {booking_no}", user.get("username", "system"))
                        )

                conn.commit()
                
                from core.audit import log_action
                log_action(user.get("id", 1), tenant_id, "booking", booking_no, f"CONVERTED_TO_JOB:{job_no}")
                
                return job_no
                
        except Exception as e:
            conn.rollback()
            raise ValueError(f"Transaction failed: {e}")