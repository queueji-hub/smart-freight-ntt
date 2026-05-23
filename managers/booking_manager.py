from typing import List, Dict, Any, Optional
from database.connection import get_connection
from managers.job_number import generate_job_number

def create_booking(data: Dict[str, Any], company_prefix: str = None) -> str:
    """Create new booking confirmation. Returns booking_no."""
    booking_no = generate_job_number(
        data.get("job_type", "SE"), data.get("created_at"), company_prefix
    )
    
    fields = [
        "booking_no", "job_type", "customer_id", "customer_name",
        "shipper", "consignee", "notify_party", "pol", "por", "pod", 
        "final_destination", "transhipment_port", "cy_date", "cy_place", 
        "cfs_date", "cfs_place", "customer_return_date", "return_place",
        "etd", "eta", "carrier", "m_vessel", "feeder", "liner",
        "closing_time", "cargo_type", "commodity", "quantity", "remark",
        "quotation_id", "created_by"
    ]
    
    placeholders = ", ".join(["%s"] * len(fields))
    cols = ", ".join(fields)
    values = [booking_no] + [data.get(f) for f in fields[1:]]
    
    with get_connection() as conn:
        conn.execute(f"INSERT INTO bookings ({cols}) VALUES ({placeholders})", tuple(values))
        conn.commit()
    return booking_no

def get_booking(booking_no: str) -> Optional[Dict[str, Any]]:
    """Retrieve a single booking record."""
    with get_connection() as conn:
        cursor = conn.execute("SELECT * FROM bookings WHERE booking_no=%s", (booking_no,))
        return cursor.fetchone()  # ข้อมูลจะเป็น dict อยู่แล้วจาก RealDictCursor

def list_bookings(status: str = None, customer_id: int = None, limit: int = None) -> List[Dict[str, Any]]:
    """List bookings with optional filters."""
    sql = "SELECT * FROM bookings WHERE 1=1"
    params = []
    if status:
        sql += " AND status=%s"; params.append(status)
    if customer_id:
        sql += " AND customer_id=%s"; params.append(customer_id)
    sql += " ORDER BY created_at DESC, id DESC"
    if limit:
        sql += " LIMIT %s"; params.append(int(limit))
        
    with get_connection() as conn:
        return list(conn.execute(sql, params).fetchall())

def update_booking(booking_no: str, data: Dict[str, Any]) -> bool:
    """Update existing booking record."""
    allowed = (
        "customer_id", "customer_name", "shipper", "consignee", "notify_party",
        "pol", "por", "pod", "final_destination", "transhipment_port",
        "cy_date", "cy_place", "cfs_date", "cfs_place",
        "customer_return_date", "return_place",
        "etd", "eta", "carrier", "m_vessel", "feeder", "liner",
        "closing_time", "cargo_type", "commodity", "quantity", "remark",
        "status",
    )
    
    sets, params = [], []
    for f in allowed:
        if f in data:
            sets.append(f"{f}=%s")
            params.append(data[f])
    
    if not sets: return False
    
    sets.append("updated_at=CURRENT_TIMESTAMP")
    params.append(booking_no)
    
    with get_connection() as conn:
        conn.execute(f"UPDATE bookings SET {', '.join(sets)} WHERE booking_no=%s", params)
        conn.commit()
    return True

def delete_booking(booking_no: str) -> bool:
    """Delete booking record."""
    with get_connection() as conn:
        conn.execute("DELETE FROM bookings WHERE booking_no=%s", (booking_no,))
        conn.commit()
    return True