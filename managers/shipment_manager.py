from managers.tenant_context import get_current_tenant_id
from typing import List, Dict, Any, Optional
from database.connection import get_connection
from managers.document_numbering_service import generate_document_number, normalize_doc_no

# =========================
# CONFIG
# =========================

SHIPMENT_FIELDS = [
    "status", "job_type", "booking_no", 
    "customer_id", "customer_name",
    "sales_id", "notify_party", "sales_person", "operations_owner", 
    "customer_reference", "quotation_no",
    "shipper", "consignee", "cargo_type", "carrier",
    "place_of_receipt", "pol", "transshipment_port", "pod", 
    "place_of_delivery", "final_destination", 
    "origin_country", "destination_country",
    "etd", "eta", "actual_departure", "actual_arrival",
    "mbl_no", "hbl_no", "bl_no", "invoice_no",
    "vessel", "voyage", "mother_vessel", "mother_voyage", "feeder_vessel", "feeder_voyage", "incoterm", "service_type", "freight_term",
    "commodity", "hs_code", "package_type", "package_quantity",
    "gross_weight", "net_weight", "cbm", "chargeable_weight",
    "is_dg", "is_temp_controlled", "special_cargo_remarks",
    "customs_declaration_no", "customs_status", 
    "customs_broker", "customs_clearance_date",
    "customer_paid", "remark",
    "reporting_date", "reporting_month", "reporting_year",
    "financial_status", "document_status", "mode", "closed_at", "closed_by",
    "created_by", "updated_by"
]

STATUS_FLOW = ["Proceed", "In Transit", "Arrived", "Finished", "Closed", "Canceled"]


def get_reporting_period(job: Dict[str, Any]) -> tuple[str, str]:
    """
    Canonical reporting period extractor.
    EXPORT: Month/Year of ETD
    IMPORT: Month/Year of ETA
    """
    job_type = str(job.get("job_type", "")).upper()
    reporting_date = None
    if "EXPORT" in job_type:
        reporting_date = job.get("etd")
    elif "IMPORT" in job_type:
        reporting_date = job.get("eta")
    else:
        reporting_date = job.get("etd") or job.get("eta")
        
    if not reporting_date:
        from datetime import datetime
        reporting_date = datetime.now().date()
        
    try:
        from datetime import datetime, date
        if isinstance(reporting_date, str):
            rd = datetime.strptime(reporting_date[:10], "%Y-%m-%d").date()
        elif isinstance(reporting_date, datetime):
            rd = reporting_date.date()
        else:
            rd = reporting_date
        return rd.strftime("%m"), rd.strftime("%Y")
    except:
        from datetime import datetime
        rd = datetime.now()
        return rd.strftime("%m"), rd.strftime("%Y")

# =========================
# CREATE JOB
# =========================

def create_shipment(data: Dict[str, Any], company_prefix: str = None) -> str:
    tenant_id = get_current_tenant_id()
    job_no = (data.get("job_no") or "").strip()
    if not job_no:
        job_no = generate_document_number(
            "JOB",
            data.get("etd")
        )
    
    raw_type = str(data.get("job_type") or data.get("mode") or data.get("transport") or "SE").strip().upper()
    type_map = {
        "SEA": "SE", "OCEAN": "SE", "SEA_EXP": "SE", "SE": "SE",
        "SEA_IMP": "SI", "SI": "SI",
        "AIR": "AE", "AIR_EXP": "AE", "AE": "AE",
        "AIR_IMP": "AI", "AI": "AI",
        "TRUCK": "TE", "ROAD": "TE", "TRK_EXP": "TE", "TE": "TE",
        "TRK_IMP": "TI", "TI": "TI",
    }
    data["job_type"] = type_map.get(raw_type, "SE")

    # ETD / ETA Business Logic
    m, y = get_reporting_period(data)
    data["reporting_month"] = m
    data["reporting_year"] = y

    data = {k: v for k, v in data.items() if k in SHIPMENT_FIELDS}

    with get_connection() as conn:
        with conn.cursor() as cur:
            # Query existing table columns dynamically to prevent UndefinedColumn errors
            table_cols: set[str] = set()
            try:
                cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name='shipments'")
                table_cols = {row["column_name"] if isinstance(row, dict) or hasattr(row, "keys") else row[0] for row in cur.fetchall()}
            except Exception:
                pass
            if not table_cols:
                try:
                    cur.execute("PRAGMA table_info(shipments)")
                    table_cols = {row[1] for row in cur.fetchall()}
                except Exception:
                    pass

            if table_cols:
                filtered_data = {k: v for k, v in data.items() if k in table_cols}
            else:
                filtered_data = data

            cols = ["job_no", "tenant_id"] + [k for k in filtered_data.keys() if k not in {"job_no", "tenant_id"}]
            vals = [job_no, tenant_id] + [filtered_data[k] for k in cols[2:]]

            placeholders = ", ".join(["%s"] * len(cols))
            columns = ", ".join(cols)

            cur.execute(
                f"INSERT INTO shipments ({columns}) VALUES ({placeholders})",
                tuple(vals)
            )
            conn.commit()

    return job_no


# =========================
# LIST JOBS
# =========================

def list_shipments(
    status: Optional[str] = None,
    job_type: Optional[str] = None,
    search_query: Optional[str] = None,
    etd_start: Optional[Any] = None,
    etd_end: Optional[Any] = None,
    eta_start: Optional[Any] = None,
    eta_end: Optional[Any] = None,
    limit: int = 200
) -> List[Dict]:
    tenant_id = get_current_tenant_id()
    sql = "SELECT * FROM shipments WHERE tenant_id = %s"
    params = [tenant_id]

    if status and status != "All":
        sql += " AND status = %s"
        params.append(status)

    if job_type and job_type != "All Types":
        sql += " AND job_type = %s"
        params.append(job_type)

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
            REPLACE(REPLACE(UPPER(job_no), '-', ''), ' ', '') LIKE %s OR
            LOWER(job_no) LIKE %s OR 
            LOWER(booking_no) LIKE %s OR 
            LOWER(customer_name) LIKE %s OR 
            LOWER(pol) LIKE %s OR 
            LOWER(pod) LIKE %s OR 
            LOWER(vessel) LIKE %s OR 
            LOWER(voyage) LIKE %s OR 
            LOWER(hbl_no) LIKE %s OR 
            LOWER(mbl_no) LIKE %s
        )"""
        params.extend([nq, q, q, q, q, q, q, q, q, q])

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

def get_shipment(job_no_or_id: Any) -> Optional[Dict]:
    if not job_no_or_id:
        return None
    tenant_id = get_current_tenant_id()
    with get_connection() as conn:
        with conn.cursor() as cur:
            if isinstance(job_no_or_id, int) or (isinstance(job_no_or_id, str) and job_no_or_id.isdigit()):
                cur.execute(
                    "SELECT * FROM shipments WHERE (id = %s OR job_no = %s) AND tenant_id = %s LIMIT 1",
                    (int(job_no_or_id), str(job_no_or_id), tenant_id)
                )
            else:
                cur.execute(
                    "SELECT * FROM shipments WHERE job_no = %s AND tenant_id = %s LIMIT 1",
                    (str(job_no_or_id), tenant_id)
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
    if not target:
        return False
    
    # 1. Status Validation
    if "status" in allowed:
        old_status = target.get("status", "Proceed")
        new_status = allowed["status"]
        if old_status != new_status:
            _validate_status_transition(old_status, new_status, target, allowed)
            
    # 2. Date Validation & ETD / ETA Business Logic
    merged = {**target, **allowed}
    if "actual_departure" in allowed or "actual_arrival" in allowed or "etd" in allowed:
        _validate_dates(merged)

    # Recalculate Reporting Date if ETD/ETA changed
    if "etd" in allowed or "eta" in allowed or "job_type" in allowed:
        m, y = get_reporting_period(merged)
        allowed["reporting_month"] = m
        allowed["reporting_year"] = y

    sets = ", ".join([f"{k}=%s" for k in allowed.keys()])
    values = list(allowed.values())

    values.append(job_no)
    values.append(get_current_tenant_id())

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"""
                UPDATE shipments
                SET {sets},
                    updated_at = CURRENT_TIMESTAMP
                WHERE job_no = %s AND tenant_id = %s
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
    tenant_id = get_current_tenant_id()
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM shipments WHERE job_no = %s AND tenant_id = %s",
                (job_no, tenant_id)
            )
            affected = cur.rowcount
            if affected > 0:
                conn.commit()
                return True
            return False


# =========================
# DASHBOARD STATS
# =========================

def get_dashboard_stats() -> Dict[str, Any]:
    tenant_id = get_current_tenant_id()
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
                WHERE tenant_id = %s
            """, (tenant_id,))
            row = cur.fetchone()
            return dict(row) if row else {}

# =========================
# JOB STATUS LOCK
# =========================
def _ensure_job_unlocked(job_no: str):
    """Enforces J3 Status Locking rules. Locked if Finished, Closed, or Canceled."""
    tenant_id = get_current_tenant_id()
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT status FROM shipments WHERE job_no = %s AND tenant_id = %s", (job_no, tenant_id))
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
    from managers.milestone_manager import list_milestones as _canon_list_milestones
    return _canon_list_milestones(job_no)

def add_milestone(data: Dict[str, Any]) -> bool:
    job_no = data.get("job_no")
    _ensure_job_unlocked(job_no)
    
    # Resolve shipment_id
    shipment_id = None
    if "shipment_id" in data:
        shipment_id = data["shipment_id"]
    elif job_no:
        tenant_id = get_current_tenant_id()
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT id FROM shipments WHERE job_no = %s AND tenant_id = %s", (job_no, tenant_id))
                srow = cur.fetchone()
                if srow:
                    shipment_id = srow["id"]
                    
    code = data.get("milestone_code")
    name = data.get("milestone_name")
    date_str = str(data.get("event_date"))[:16] if data.get("event_date") else None
    location = data.get("location", "")
    remark = data.get("remark", "")
    
    from managers.milestone_manager import add_milestone as _canon_add_milestone
    _canon_add_milestone(shipment_id, job_no, code, name, date_str, location, remark)
    return True
            
def delete_milestone(milestone_id: int, job_no: str) -> bool:
    _ensure_job_unlocked(job_no)
    from managers.milestone_manager import delete_milestone as _canon_del_milestone
    return _canon_del_milestone(milestone_id, job_no)

# =========================
# CONTAINERS
# =========================

def list_job_containers(job_no: str) -> List[Dict]:
    from managers.container_manager import list_containers
    return list_containers(job_no=job_no)

def add_job_container(data: Dict[str, Any]) -> bool:
    job_no = data.get("job_no")
    _ensure_job_unlocked(job_no)
    
    c_no = data.get("container_no", "").strip().upper()
    if not c_no:
        raise ValueError("Container Number cannot be empty.")
    
    if "shipment_id" not in data and job_no:
        tenant_id = get_current_tenant_id()
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT id FROM shipments WHERE job_no = %s AND tenant_id = %s", (job_no, tenant_id))
                srow = cur.fetchone()
                if srow:
                    data["shipment_id"] = srow["id"]
                    
    from managers.container_manager import add_container
    return add_container(data)

def delete_job_container(container_id: int, job_no: str) -> bool:
    _ensure_job_unlocked(job_no)
    from managers.container_manager import delete_container
    return delete_container(container_id, job_no)

# =========================
# FINANCIALS
# =========================

def get_job_financial_summary(shipment_id: int) -> Dict[str, float]:
    """Calculates Revenue, Cost, and Profit based on legacy job_costs + posted ap_vouchers."""
    summary = {
        "total_revenue_thb": 0.0,
        "total_cost_thb": 0.0,
        "gross_profit_thb": 0.0,
        "margin_percent": 0.0
    }
    
    tenant_id = get_current_tenant_id()
    with get_connection() as conn:
        with conn.cursor() as cur:
            # 1. Fetch Legacy Job Costs
            cur.execute(
                """
                SELECT c.cost_type, c.amount, c.exchange_rate, c.amount_thb 
                FROM job_costs c
                JOIN shipments s ON c.shipment_id = s.id
                WHERE c.shipment_id = %s AND s.tenant_id = %s
                """,
                (shipment_id, tenant_id)
            )
            costs = cur.fetchall()
            if costs:
                for row in costs:
                    ctype = str(row['cost_type']).upper() if isinstance(row, dict) else str(row[2]).upper()
                    amt_thb = float(row['amount_thb']) if isinstance(row, dict) else float(row[5])
                    
                    if ctype in ['REVENUE', 'AR']:
                        summary["total_revenue_thb"] += amt_thb
                    elif ctype in ['COST', 'AP']:
                        summary["total_cost_thb"] += amt_thb
            
            # 2. Fetch Posted AP Vouchers (D63)
            cur.execute("""
                SELECT ap.total, ap.exchange_rate
                FROM ap_vouchers ap
                JOIN shipments s ON ap.job_no = s.job_no
                WHERE s.id = %s AND ap.tenant_id = %s AND ap.status IN ('POSTED', 'PARTIALLY_PAID', 'PAID')
            """, (shipment_id, tenant_id))
            
            ap_costs = cur.fetchall()
            if ap_costs:
                for row in ap_costs:
                    total = float(row['total']) if isinstance(row, dict) else float(row[0])
                    ex_rate = float(row['exchange_rate']) if isinstance(row, dict) else float(row[1])
                    summary["total_cost_thb"] += (total * ex_rate)
                    
            # 3. Fetch AR from Invoices (D64)
            cur.execute("""
                SELECT i.subtotal, 1.0 AS exchange_rate
                FROM invoices i
                JOIN shipments s ON i.job_no = s.job_no
                WHERE s.id = %s AND i.tenant_id = %s AND i.payment_status IN ('APPROVED', 'PARTIALLY_PAID', 'PAID')
            """, (shipment_id, tenant_id))
            
            ar_rev = cur.fetchall()
            if ar_rev:
                for row in ar_rev:
                    total = float(row['subtotal']) if isinstance(row, dict) else float(row[0])
                    ex_rate = float(row.get('exchange_rate', 1.0)) if isinstance(row, dict) else (float(row[1]) if len(row) > 1 and row[1] else 1.0)
                    summary["total_revenue_thb"] += (total * ex_rate)
                    
    summary["gross_profit_thb"] = summary["total_revenue_thb"] - summary["total_cost_thb"]
    if summary["total_revenue_thb"] > 0:
        summary["margin_percent"] = (summary["gross_profit_thb"] / summary["total_revenue_thb"]) * 100
        
    return summary

# =========================
# MILESTONES
# =========================

def add_milestone(job_no: str, milestone_code: str, milestone_name: str, planned_date: str = None) -> bool:
    tenant_id = get_current_tenant_id()
    target = get_shipment(job_no)
    if not target:
        return False
        
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO shipment_milestones (tenant_id, shipment_id, milestone_code, milestone_name, planned_date)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (tenant_id, target['id'], milestone_code, milestone_name, planned_date)
            )
            conn.commit()
            return cur.rowcount > 0

def update_milestone(milestone_id: int, actual_date: str, status: str = 'COMPLETED', remarks: str = None) -> bool:
    tenant_id = get_current_tenant_id()
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE shipment_milestones
                SET actual_date = %s, status = %s, remarks = %s, updated_at = CURRENT_TIMESTAMP
                WHERE id = %s AND tenant_id = %s
                """,
                (actual_date, status, remarks, milestone_id, tenant_id)
            )
            conn.commit()
            return cur.rowcount > 0

def get_milestones(job_no: str) -> List[Dict]:
    tenant_id = get_current_tenant_id()
    target = get_shipment(job_no)
    if not target:
        return []
        
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT * FROM shipment_milestones 
                WHERE shipment_id = %s AND tenant_id = %s
                ORDER BY id ASC
                """,
                (target['id'], tenant_id)
            )
            rows = cur.fetchall()
            if not rows:
                return []
            cols = [desc[0] for desc in cur.description]
            return [dict(zip(cols, row)) for row in rows]
