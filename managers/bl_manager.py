from typing import Dict, Any, List
import sqlite3
from datetime import datetime
from database.connection import get_connection
from managers.shipment_manager import get_shipment, _ensure_job_unlocked

BL_STATUS_FLOW = {
    "Draft": ["Verified", "Cancelled"],
    "Verified": ["Released", "Draft", "Cancelled"],
    "Released": ["Cancelled"],
    "Cancelled": []
}

def _ensure_bl_unlocked(bl_id: int):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT status, job_no FROM bills_of_lading WHERE id = %s", (bl_id,))
            row = cur.fetchone()
            if not row:
                raise ValueError("B/L not found.")
            
            # Check B/L lock
            status = row["status"]
            if status in ["Released", "Cancelled"]:
                raise ValueError(f"B/L is {status} and cannot be modified.")
                
            # Check Job lock
            _ensure_job_unlocked(row["job_no"])
            return row["job_no"]

def list_bl_documents(job_no: str) -> List[Dict]:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM bills_of_lading WHERE job_no = %s ORDER BY created_at ASC", (job_no,))
            return [dict(r) for r in cur.fetchall()]

def get_bl_document(bl_id: int) -> Dict:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM bills_of_lading WHERE id = %s", (bl_id,))
            row = cur.fetchone()
            return dict(row) if row else None

def create_bl_document(job_no: str, bl_type: str, user: dict) -> int:
    """Creates a new B/L and prefills data from the Job."""
    _ensure_job_unlocked(job_no)
    
    if bl_type not in ["HBL", "MBL"]:
        raise ValueError("bl_type must be HBL or MBL")
        
    job = get_shipment(job_no)
    if not job:
        raise ValueError("Job not found.")
        
    # Generate B/L No
    import time
    bl_no = f"{bl_type}-{job_no}-{int(time.time())}"
    
    # Prefill mapping
    payload = {
        "bl_no": bl_no,
        "job_no": job_no,
        "shipment_id": job["id"],
        "bl_type": bl_type,
        "status": "Draft",
        "shipper": job.get("shipper"),
        "consignee": job.get("consignee"),
        "notify_party": job.get("notify_party"),
        "pol": job.get("pol"),
        "pod": job.get("pod"),
        "place_of_receipt": job.get("place_of_receipt"),
        "place_of_delivery": job.get("place_of_delivery"),
        "final_destination": job.get("final_destination"),
        "vessel": job.get("vessel"),
        "voyage": job.get("voyage"),
        "freight_term": job.get("freight_term"),
        "gross_weight": float(job.get("gross_weight") or 0.0),
        "measurement_cbm": float(job.get("cbm") or 0.0),
        "package_quantity": int(job.get("package_quantity") or 0),
        "package_type": job.get("package_type"),
        "description_of_goods": job.get("commodity")
    }
    
    cols = list(payload.keys())
    vals = list(payload.values())
    placeholders = ", ".join(["%s"] * len(cols))
    columns = ", ".join(cols)
    
    with get_connection() as conn:
        try:
            with conn.cursor() as cur:
                cur.execute(
                    f"INSERT INTO bills_of_lading ({columns}) VALUES ({placeholders})",
                    tuple(vals)
                )
                conn.commit()
                # return id
                return cur.lastrowid
        except sqlite3.IntegrityError:
            raise ValueError("Duplicate B/L Number.")

def update_bl_document(bl_id: int, data: Dict[str, Any]) -> bool:
    _ensure_bl_unlocked(bl_id)
    
    # Validation
    qty = float(data.get("package_quantity", 0) or 0)
    gw = float(data.get("gross_weight", 0.0) or 0.0)
    cbm = float(data.get("measurement_cbm", 0.0) or 0.0)
    
    if qty < 0 or gw < 0 or cbm < 0:
        raise ValueError("Quantities and weights must be >= 0")
        
    sets = ", ".join([f"{k}=%s" for k in data.keys()])
    values = list(data.values())
    values.append(bl_id)
    
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"UPDATE bills_of_lading SET {sets}, updated_at=CURRENT_TIMESTAMP WHERE id = %s",
                tuple(values)
            )
            conn.commit()
            return cur.rowcount > 0

def update_bl_status(bl_id: int, new_status: str) -> bool:
    doc = get_bl_document(bl_id)
    if not doc:
        raise ValueError("B/L not found.")
        
    old_status = doc["status"]
    if new_status not in BL_STATUS_FLOW.get(old_status, []):
        raise ValueError(f"Invalid B/L status transition from {old_status} to {new_status}")
        
    # If transitioning to Released, validate required fields
    if new_status == "Released":
        required = ["shipper", "consignee", "pol", "pod"]
        for f in required:
            if not doc.get(f):
                raise ValueError(f"Cannot Release B/L: Missing required field '{f}'")
                
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("UPDATE bills_of_lading SET status = %s WHERE id = %s", (new_status, bl_id))
            conn.commit()
            return cur.rowcount > 0

def delete_bl_document(bl_id: int) -> bool:
    _ensure_bl_unlocked(bl_id)
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM bills_of_lading WHERE id = %s", (bl_id,))
            conn.commit()
            return cur.rowcount > 0

def list_bl_containers(bl_id: int) -> List[Dict]:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT c.*, bc.id as junction_id
                FROM containers c
                JOIN bl_containers bc ON c.id = bc.container_id
                WHERE bc.bl_id = %s
            """, (bl_id,))
            return [dict(r) for r in cur.fetchall()]

def link_container_to_bl(bl_id: int, container_id: int) -> bool:
    _ensure_bl_unlocked(bl_id)
    with get_connection() as conn:
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO bl_containers (bl_id, container_id) VALUES (%s, %s)",
                    (bl_id, container_id)
                )
                conn.commit()
                return cur.rowcount > 0
        except sqlite3.IntegrityError:
            # Already linked, ignore gracefully
            return True

def unlink_container_from_bl(bl_id: int, container_id: int) -> bool:
    _ensure_bl_unlocked(bl_id)
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM bl_containers WHERE bl_id = %s AND container_id = %s", (bl_id, container_id))
            conn.commit()
            return cur.rowcount > 0