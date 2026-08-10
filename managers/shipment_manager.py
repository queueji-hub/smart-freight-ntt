from typing import List, Dict, Any, Optional
from database.connection import get_connection
from managers.job_number import generate_job_number

# =========================
# CONFIG
# =========================

SHIPMENT_FIELDS = [
    "status", "job_type", "booking_no", 
    "customer_id", "customer_name",
    "notify_party", "sales_person", "operations_owner", 
    "customer_reference", "quotation_no",
    "shipper", "consignee", "cargo_type", "carrier",
    "place_of_receipt", "pol", "transshipment_port", "pod", 
    "place_of_delivery", "final_destination", 
    "origin_country", "destination_country",
    "etd", "eta", "actual_departure", "actual_arrival",
    "mbl_no", "hbl_no", "bl_no", "invoice_no",
    "vessel", "voyage", "incoterm", "service_type", "freight_term",
    "commodity", "hs_code", "package_type", "package_quantity",
    "gross_weight", "net_weight", "cbm", "chargeable_weight",
    "is_dg", "is_temp_controlled", "special_cargo_remarks",
    "customs_declaration_no", "customs_status", 
    "customs_broker", "customs_clearance_date",
    "customer_paid", "remark",
    "created_by", "updated_by"
]

STATUS_FLOW = ["Proceed", "In Transit", "Arrived", "Finished", "Closed", "Canceled"]


# =========================
# CREATE JOB
# =========================

def create_shipment(data: Dict[str, Any], company_prefix: str = None) -> str:
    job_no = generate_job_number(
        data.get("job_type", "SE"),
        data.get("etd"),
        company_prefix
    )

    data = {k: v for k, v in data.items() if k in SHIPMENT_FIELDS}

    cols = ["job_no"] + list(data.keys())
    vals = [job_no] + list(data.values())

    placeholders = ", ".join(["%s"] * len(cols))
    columns = ", ".join(cols)

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"INSERT INTO shipments ({columns}) VALUES ({placeholders})",
                tuple(vals)
            )
            conn.commit()

    return job_no


# =========================
# LIST JOBS
# =========================

def list_shipments(status: Optional[str] = None, limit: int = 200) -> List[Dict]:
    sql = "SELECT * FROM shipments WHERE 1=1"
    params = []

    if status:
        sql += " AND status = %s"
        params.append(status)

    sql += " ORDER BY created_at DESC LIMIT %s"
    params.append(limit)

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()
            return [dict(r) for r in rows]


# =========================
# GET SINGLE JOB
# =========================

def get_shipment(job_no: str) -> Optional[Dict]:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM shipments WHERE job_no = %s",
                (job_no,)
            )
            row = cur.fetchone()
            return dict(row) if row else None


# =========================
# UPDATE JOB (SAFE PATCH)
# =========================

def update_shipment(job_no: str, data: Dict[str, Any]) -> bool:
    allowed = {k: v for k, v in data.items() if k in SHIPMENT_FIELDS}

    if not allowed:
        return False
        
    target = get_shipment(job_no)
    
    # 1. Status Validation
    if "status" in allowed:
        old_status = target.get("status", "Proceed")
        new_status = allowed["status"]
        if old_status != new_status:
            _validate_status_transition(old_status, new_status, target, allowed)
            
    # 2. Date Validation
    merged = {**target, **allowed}
    if "actual_departure" in allowed or "actual_arrival" in allowed or "etd" in allowed:
        _validate_dates(merged)

    sets = ", ".join([f"{k}=%s" for k in allowed.keys()])
    values = list(allowed.values())

    values.append(job_no)

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"""
                UPDATE shipments
                SET {sets},
                    updated_at = CURRENT_TIMESTAMP
                WHERE job_no = %s
                """,
                tuple(values)
            )
            conn.commit()
            return cur.rowcount > 0


# =========================
# DELETE JOB (SOFT SAFE OPTION)
# =========================

def _validate_status_transition(old_status: str, new_status: str, current_data: Dict, patch_data: Dict):
    """Enforces the Freight Forwarding State Machine."""
    allowed = {
        "Proceed": ["In Transit", "Canceled"],
        "In Transit": ["Arrived", "Canceled"],
        "Arrived": ["Finished"],
        "Finished": ["Closed"],
        "Closed": [],
        "Canceled": ["Proceed"] # Reopen
    }
    
    if new_status not in allowed.get(old_status, []):
        raise ValueError(f"Invalid transition from {old_status} to {new_status}")
        
    merged = {**current_data, **patch_data}
    
    if new_status == "In Transit":
        if not merged.get("actual_departure"):
            raise ValueError("Cannot mark as In Transit: Missing Actual Departure.")
    if new_status == "Arrived":
        if not merged.get("actual_arrival"):
            raise ValueError("Cannot mark as Arrived: Missing Actual Arrival.")
    if new_status == "Finished":
        if not merged.get("actual_departure") or not merged.get("actual_arrival"):
            raise ValueError("Cannot mark as Finished: Missing Actual Dates.")
    if new_status == "Closed":
        if not merged.get("actual_arrival"):
            raise ValueError("Cannot mark as Closed: Missing Actual Arrival.")
            
def _validate_dates(merged_data: Dict):
    """Validates operational dates against planned dates."""
    from datetime import date, datetime
    def to_date(val):
        if not val:
            return None
        if isinstance(val, date) and not isinstance(val, datetime):
            return val
        if isinstance(val, datetime):
            return val.date()
        try:
            return datetime.strptime(str(val)[:10], "%Y-%m-%d").date()
        except Exception:
            return None

    etd = to_date(merged_data.get("etd"))
    actual_departure = to_date(merged_data.get("actual_departure"))
    actual_arrival = to_date(merged_data.get("actual_arrival"))
    
    if actual_departure and etd:
        if actual_departure < etd:
            # Optionally block, or allow with override. We enforce blocking unless override logic exists.
            raise ValueError("Actual Departure cannot be earlier than ETD.")
            
    if actual_arrival and actual_departure:
        if actual_arrival < actual_departure:
            raise ValueError("Actual Arrival cannot be earlier than Actual Departure.")

def delete_shipment(job_no: str) -> bool:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM shipments WHERE job_no = %s",
                (job_no,)
            )
            conn.commit()

    return True


# =========================
# DASHBOARD STATS
# =========================

def get_dashboard_stats() -> Dict[str, Any]:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    COUNT(*) as total,
                    COALESCE(SUM(CASE WHEN status='Proceed' THEN 1 ELSE 0 END), 0) as proceed,
                    COALESCE(SUM(CASE WHEN status='Finished' THEN 1 ELSE 0 END), 0) as finished,
                    COALESCE(SUM(CASE WHEN status='Closed' THEN 1 ELSE 0 END), 0) as closed,
                    COALESCE(SUM(CASE WHEN status='Canceled' THEN 1 ELSE 0 END), 0) as canceled
                FROM shipments
            """)
            row = cur.fetchone()
            return dict(row) if row else {}

# =========================
# JOB STATUS LOCK
# =========================
def _ensure_job_unlocked(job_no: str):
    """Enforces J3 Status Locking rules. Locked if Finished, Closed, or Canceled."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT status FROM shipments WHERE job_no = %s", (job_no,))
            row = cur.fetchone()
            if not row:
                raise ValueError("Shipment not found.")
            status = row["status"]
            if status in ["Finished", "Closed", "Canceled"]:
                raise ValueError(f"Job is locked (Status: {status}). Modification is forbidden.")

# =========================
# SHIPMENT MILESTONES
# =========================

def list_milestones(job_no: str) -> List[Dict]:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM shipment_milestones WHERE job_no = %s ORDER BY event_date ASC",
                (job_no,)
            )
            return [dict(r) for r in cur.fetchall()]

def add_milestone(data: Dict[str, Any]) -> bool:
    job_no = data.get("job_no")
    _ensure_job_unlocked(job_no)
    
    code = data.get("milestone_code")
    date_str = str(data.get("event_date"))[:16] # compare to the minute
    location = data.get("location", "")
    
    # Check for exact duplicates
    existing = list_milestones(job_no)
    for m in existing:
        if m.get("milestone_code") == code and str(m.get("event_date"))[:16] == date_str and (m.get("location") or "") == location:
            raise ValueError(f"Duplicate milestone: {code} already logged at this time and location.")

    cols = list(data.keys())
    vals = list(data.values())
    placeholders = ", ".join(["%s"] * len(cols))
    columns = ", ".join(cols)
    
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"INSERT INTO shipment_milestones ({columns}) VALUES ({placeholders})",
                tuple(vals)
            )
            conn.commit()
            return cur.rowcount > 0
            
def delete_milestone(milestone_id: int, job_no: str) -> bool:
    _ensure_job_unlocked(job_no)
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM shipment_milestones WHERE id = %s AND job_no = %s", (milestone_id, job_no))
            conn.commit()
            return cur.rowcount > 0

# =========================
# CONTAINERS
# =========================

def list_job_containers(job_no: str) -> List[Dict]:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM containers WHERE job_no = %s ORDER BY created_at ASC",
                (job_no,)
            )
            return [dict(r) for r in cur.fetchall()]

def add_job_container(data: Dict[str, Any]) -> bool:
    job_no = data.get("job_no")
    _ensure_job_unlocked(job_no)
    
    # Validation
    vgm = float(data.get("vgm_kg", 0.0) or 0.0)
    tare = float(data.get("tare_weight", 0.0) or 0.0)
    gross = float(data.get("gross_weight", 0.0) or 0.0)
    
    if vgm < 0 or tare < 0 or gross < 0:
        raise ValueError("Container weights (VGM, Tare, Gross) must be >= 0.")
        
    c_no = data.get("container_no", "").strip().upper()
    if not c_no:
        raise ValueError("Container Number cannot be empty.")
    data["container_no"] = c_no
    
    cols = list(data.keys())
    vals = list(data.values())
    placeholders = ", ".join(["%s"] * len(cols))
    columns = ", ".join(cols)

    import sqlite3
    with get_connection() as conn:
        try:
            with conn.cursor() as cur:
                cur.execute(
                    f"INSERT INTO containers ({columns}) VALUES ({placeholders})",
                    tuple(vals)
                )
                conn.commit()
                return cur.rowcount > 0
        except sqlite3.IntegrityError:
            raise ValueError(f"Duplicate Container: {c_no} is already attached to this shipment.")
        except Exception as e:
            if "UNIQUE constraint" in str(e):
                raise ValueError(f"Duplicate Container: {c_no} is already attached to this shipment.")
            raise e

def delete_job_container(container_id: int, job_no: str) -> bool:
    _ensure_job_unlocked(job_no)
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM containers WHERE id = %s AND job_no = %s", (container_id, job_no))
            conn.commit()
            return cur.rowcount > 0

# =========================
# FINANCIALS
# =========================

def get_job_financial_summary(shipment_id: int) -> Dict[str, float]:
    """Calculates Revenue, Cost, and Profit based on job_costs."""
    summary = {
        "total_revenue_thb": 0.0,
        "total_cost_thb": 0.0,
        "gross_profit_thb": 0.0,
        "margin_percent": 0.0
    }
    
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT cost_type, amount, exchange_rate, amount_thb FROM job_costs WHERE shipment_id = %s",
                (shipment_id,)
            )
            costs = cur.fetchall()
            if not costs:
                return summary
                
            for row in costs:
                ctype = str(row['cost_type']).upper() if isinstance(row, dict) else str(row[2]).upper()
                amt_thb = float(row['amount_thb']) if isinstance(row, dict) else float(row[5])
                
                if ctype in ['REVENUE', 'AR']:
                    summary["total_revenue_thb"] += amt_thb
                elif ctype in ['COST', 'AP']:
                    summary["total_cost_thb"] += amt_thb
                    
    summary["gross_profit_thb"] = summary["total_revenue_thb"] - summary["total_cost_thb"]
    if summary["total_revenue_thb"] > 0:
        summary["margin_percent"] = (summary["gross_profit_thb"] / summary["total_revenue_thb"]) * 100
        
    return summary