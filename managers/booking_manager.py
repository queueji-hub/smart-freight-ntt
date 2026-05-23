"""Booking Confirmation management."""
from typing import List, Dict, Any, Optional
from database.connection import get_connection
from managers.job_number import generate_job_number

def _ensure_table():
    """Create bookings table if missing."""
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS bookings (
                id SERIAL PRIMARY KEY,
                booking_no TEXT UNIQUE NOT NULL,
                job_type TEXT,
                customer_id INTEGER,
                customer_name TEXT,
                shipper TEXT,
                consignee TEXT,
                notify_party TEXT,
                pol TEXT,
                por TEXT,
                pod TEXT,
                final_destination TEXT,
                transhipment_port TEXT,
                cy_date DATE,
                cy_place TEXT,
                cfs_date DATE,
                cfs_place TEXT,
                customer_return_date DATE,
                return_place TEXT,
                etd DATE,
                eta DATE,
                carrier TEXT,
                m_vessel TEXT,
                feeder TEXT,
                liner TEXT,
                closing_time TIMESTAMP,
                cargo_type TEXT,
                commodity TEXT,
                quantity TEXT,
                remark TEXT,
                quotation_id INTEGER,
                status TEXT DEFAULT 'pending',
                created_by TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

def create_booking(data: Dict[str, Any], company_prefix: str = None) -> str:
    """Create new booking confirmation. Returns booking_no."""
    _ensure_table()
    booking_no = generate_job_number(
        data.get("job_type", "SE"), data.get("created_at"), company_prefix
    )
    
    fields = (
        "booking_no", "job_type", "customer_id", "customer_name",
        "shipper", "consignee", "notify_party",
        "pol", "por", "pod", "final_destination", "transhipment_port",
        "cy_date", "cy_place", "cfs_date", "cfs_place",
        "customer_return_date", "return_place",
        "etd", "eta", "carrier", "m_vessel", "feeder", "liner",
        "closing_time", "cargo_type", "commodity", "quantity", "remark",
        "quotation_id", "created_by"
    )
    
    placeholders = ",".join(["%s"] * len(fields))
    cols = ",".join(fields)
    
    with get_connection() as conn:
        conn.execute(
            f"INSERT INTO bookings ({cols}) VALUES ({placeholders})",
            tuple([booking_no] + [data.get(f) for f in fields[1:]])
        )
    return booking_no

def get_booking(booking_no: str) -> Optional[Dict[str, Any]]:
    """Retrieve a single booking record."""
    _ensure_table()
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM bookings WHERE booking_no=%s", (booking_no,)
        ).fetchone()
        
    if not row: return None
    # แปลง Row เป็น Dict อย่างปลอดภัย
    return dict(row) if hasattr(row, 'keys') else {k: v for k, v in zip(['id', 'booking_no', 'job_type', 'customer_id', 'customer_name', 'shipper', 'consignee', 'notify_party', 'pol', 'por', 'pod', 'final_destination', 'transhipment_port', 'cy_date', 'cy_place', 'cfs_date', 'cfs_place', 'customer_return_date', 'return_place', 'etd', 'eta', 'carrier', 'm_vessel', 'feeder', 'liner', 'closing_time', 'cargo_type', 'commodity', 'quantity', 'remark', 'quotation_id', 'status', 'created_by', 'created_at', 'updated_at'], row)}

def list_bookings(status: str = None, customer_id: int = None, limit: int = None) -> List[Dict[str, Any]]:
    """List bookings with optional filters."""
    _ensure_table()
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
        rows = conn.execute(sql, params).fetchall()
        # แปลงเป็น List of Dict
        return [dict(r) if hasattr(r, 'keys') else {k: v for k, v in zip(['id', 'booking_no', 'job_type', 'customer_id', 'customer_name', 'shipper', 'consignee', 'notify_party', 'pol', 'por', 'pod', 'final_destination', 'transhipment_port', 'cy_date', 'cy_place', 'cfs_date', 'cfs_place', 'customer_return_date', 'return_place', 'etd', 'eta', 'carrier', 'm_vessel', 'feeder', 'liner', 'closing_time', 'cargo_type', 'commodity', 'quantity', 'remark', 'quotation_id', 'status', 'created_by', 'created_at', 'updated_at'], r)} for r in rows]

def update_booking(booking_no: str, data: Dict[str, Any]) -> bool:
    """Update existing booking record."""
    _ensure_table()
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
    return True

def delete_booking(booking_no: str) -> bool:
    """Delete booking record."""
    _ensure_table()
    with get_connection() as conn:
        conn.execute("DELETE FROM bookings WHERE booking_no=%s", (booking_no,))
    return True