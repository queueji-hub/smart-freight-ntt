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
    if "status" in allowed:
        old_status = target.get("status", "Proceed")
        new_status = allowed["status"]
        if old_status != new_status:
            _validate_status_transition(old_status, new_status, target, allowed)

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
        "Proceed": ["Finished", "Canceled"],
        "Finished": ["Closed", "Canceled"],
        "Closed": [],
        "Canceled": ["Proceed"] # Reopen
    }
    
    if new_status not in allowed.get(old_status, []):
        raise ValueError(f"Invalid transition from {old_status} to {new_status}")
        
    merged = {**current_data, **patch_data}
    
    if new_status == "Finished":
        if not merged.get("actual_departure") and not merged.get("actual_arrival"):
            raise ValueError("Cannot mark as Finished: Missing Actual Departure or Actual Arrival.")
    if new_status == "Closed":
        if not merged.get("actual_arrival"):
            raise ValueError("Cannot mark as Closed: Missing Actual Arrival.")

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
    code = data.get("milestone_code")
    date_str = str(data.get("event_date"))[:10] # compare day
    
    # Check for duplicates on same day
    existing = list_milestones(job_no)
    for m in existing:
        if m.get("milestone_code") == code and str(m.get("event_date"))[:10] == date_str:
            raise ValueError(f"Duplicate milestone: {code} already logged on {date_str}")

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
    cols = list(data.keys())
    vals = list(data.values())
    placeholders = ", ".join(["%s"] * len(cols))
    columns = ", ".join(cols)

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"INSERT INTO containers ({columns}) VALUES ({placeholders})",
                tuple(vals)
            )
            conn.commit()
            return cur.rowcount > 0

def delete_job_container(container_id: int) -> bool:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM containers WHERE id = %s", (container_id,))
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