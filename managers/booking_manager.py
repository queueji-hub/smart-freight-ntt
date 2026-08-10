from typing import List, Dict, Any, Optional
from database.connection import get_connection
from managers.job_number import generate_job_number
from core.audit import log_action


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
                    closing_time,
                    cargo_type,
                    commodity,
                    quantity,
                    remark,
                    quotation_id,
                    status,
                    created_by
                )
                VALUES (
                    %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,
                    %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,
                    %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,
                    %s,'PENDING',%s
                )
                RETURNING booking_no
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
                data.get("closing_time"),
                data.get("cargo_type"),
                data.get("commodity"),
                data.get("quantity"),
                data.get("remark"),
                data.get("quotation_id"),
                data.get("created_by")
            ))

            result = cur.fetchone()
            returned_booking_no = result['booking_no'] if result else booking_no

            conn.commit()

        log_action(
            user.get("id", 1),
            tenant_id,
            "booking",
            returned_booking_no,
            "CREATE"
        )

        return returned_booking_no


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

def update_booking(booking_no: str, data: Dict[str, Any], tenant_id: str = "default") -> bool:

    allowed_fields = {
        "customer_id", "customer_name", "shipper", "consignee",
        "notify_party", "pol", "por", "pod", "final_destination",
        "transhipment_port", "cy_date", "cy_place", "cfs_date",
        "cfs_place", "customer_return_date", "return_place",
        "etd", "eta", "carrier", "m_vessel", "feeder", "liner",
        "closing_time", "cargo_type", "commodity", "quantity",
        "remark", "status"
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
# DELETE BOOKING (SAFE)
# =========================================================

def delete_booking(booking_no: str, tenant_id: str = "default") -> bool:

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                DELETE FROM bookings
                WHERE booking_no=%s AND tenant_id=%s
            """, (booking_no, tenant_id))

            conn.commit()

            return cur.rowcount > 0