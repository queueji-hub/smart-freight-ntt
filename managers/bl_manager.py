from managers.tenant_context import get_current_tenant_id
"""
B/L (Bill of Lading) Manager — J4
Handles HBL / MBL creation, CRUD, prefill from Job,
container mapping, status workflow, and edit locking.

Architecture:
  Shipment → bills_of_lading (header) → bl_containers (junction) → containers

Isolation rule: B/L is a downstream snapshot.
  Editing B/L does NOT modify Job.
  Editing Job does NOT silently modify an existing B/L.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, date
from database.connection import get_connection
from managers.document_numbering_service import generate_document_number, normalize_doc_no

# =========================================================
# CONSTANTS
# =========================================================

BL_STATUS_FLOW: Dict[str, List[str]] = {
    "Draft":      ["Submitted", "Cancelled"],
    "Submitted":  ["Approved", "Draft", "Cancelled"],
    "Approved":   ["Issued",   "Cancelled"],
    "Issued":     ["Surrendered"],
    "Surrendered": [],
    "Cancelled":  [],
}

LOCKED_STATUSES = {"Approved", "Issued", "Surrendered", "Cancelled"}
EDITABLE_STATUSES = {"Draft", "Submitted"}

BL_TYPES = ("HBL", "MBL")


# =========================================================
# SAFE VALUE HELPERS
# =========================================================

def _s(val, default="") -> str:
    """NULL-safe string conversion. Never returns 'None' or literal 'None'."""
    if val is None:
        return default
    v = str(val).strip()
    if not v or v.lower() == "none":
        return default
    return v


def _f(val, default=0.0) -> float:
    """NULL-safe float conversion."""
    try:
        return float(val) if val is not None else default
    except (TypeError, ValueError):
        return default


def _i(val, default=0) -> int:
    """NULL-safe integer conversion."""
    try:
        return int(val) if val is not None else default
    except (TypeError, ValueError):
        return default


def _safe_date(val) -> Optional[date]:
    """NULL-safe date parsing."""
    if not val:
        return None
    if isinstance(val, datetime):
        return val.date()
    if isinstance(val, date):
        return val
    try:
        return datetime.strptime(str(val)[:10], "%Y-%m-%d").date()
    except Exception:
        return None


# =========================================================
# B/L NUMBER GENERATOR
# =========================================================

def generate_bl_number(bl_type: str, ref_date=None) -> str:
    """
    Generate a unique B/L number following project numbering convention.
    Format: {HBL|MBL}{YYMM}{NNNN}
    Uses job_counters table for atomic sequence generation.
    """
    if bl_type not in BL_TYPES:
        raise ValueError(f"bl_type must be one of {BL_TYPES}")

    d = _safe_date(ref_date) or date.today()
    yymm = d.strftime("%y%m")
    counter_key = f"BL_{bl_type}"

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO job_counters (job_type, yymm, last_running)
                VALUES (%s, %s, 1)
                ON CONFLICT (job_type, yymm)
                DO UPDATE SET last_running = job_counters.last_running + 1
            """, (counter_key, yymm))

            cur.execute(
                "SELECT last_running FROM job_counters WHERE job_type=%s AND yymm=%s",
                (counter_key, yymm)
            )
            row = cur.fetchone()
            conn.commit()
            seq = row["last_running"]

    return f"{bl_type}{yymm}{seq:04d}"


# =========================================================
# STATUS HELPERS
# =========================================================

def can_transition_bl_status(current: str, target: str) -> bool:
    """Return True if the status transition is permitted."""
    return target in BL_STATUS_FLOW.get(current, [])


def _ensure_bl_unlocked(bl_id: int) -> Dict:
    """
    Raise ValueError if B/L is locked (Approved/Issued/Surrendered/Cancelled).
    Returns the full B/L doc dict on success.
    """
    doc = get_bl(bl_id)
    if not doc:
        raise ValueError(f"B/L id={bl_id} not found.")
    status = doc.get("status", "Draft")
    if status in LOCKED_STATUSES:
        raise ValueError(f"B/L '{doc.get('bl_no')}' is {status} and cannot be modified.")
    return doc


# =========================================================
# JOB PREFILL HELPER
# =========================================================

def prefill_bl_from_job(job_no: str, bl_type: str) -> Dict[str, Any]:
    """
    Build a prefill dict from an existing Job / Shipment.
    Returns a safe snapshot — does NOT write to DB.
    Callers must explicitly pass to create_bl().
    """
    from managers.shipment_manager import get_shipment
    job = get_shipment(job_no)
    if not job:
        raise ValueError(f"Job '{job_no}' not found.")

    return {
        "shipment_id":         job.get("id"),
        "job_no":              job_no,
        "booking_no":          _s(job.get("booking_no")),
        "bl_type":             bl_type,
        "status":              "Draft",
        # Parties
        "shipper":             _s(job.get("shipper")),
        "consignee":           _s(job.get("consignee")),
        "notify_party":        _s(job.get("notify_party")),
        # Routing
        "place_of_receipt":    _s(job.get("place_of_receipt")),
        "port_of_loading":     _s(job.get("pol")),
        "port_of_discharge":   _s(job.get("pod")),
        "place_of_delivery":   _s(job.get("place_of_delivery")),
        "final_destination":   _s(job.get("final_destination")),
        # Vessel
        "vessel":              _s(job.get("vessel")),
        "voyage":              _s(job.get("voyage")),
        # Dates
        "etd":                 job.get("etd"),
        "eta":                 job.get("eta"),
        # Freight
        "freight_term":        _s(job.get("freight_term")),
        "freight_payable_at":  "",
        # Cargo
        "description_of_goods": _s(job.get("commodity")),
        "hs_code":             _s(job.get("hs_code")),
        "package_qty":         _i(job.get("package_quantity")),
        "package_type":        _s(job.get("package_type")),
        "gross_weight":        _f(job.get("gross_weight")),
        "measurement_cbm":     _f(job.get("cbm")),
    }


# =========================================================
# CRUD — B/L DOCUMENTS
# =========================================================

def create_bl(
    job_no: str,
    bl_type: str,
    user: dict,
    extra_data: Optional[Dict[str, Any]] = None,
) -> int:
    """
    Create a B/L from a Job.
    Prefills from Job. extra_data can override any prefilled field.
    Returns the new bl_id (INTEGER).
    Raises ValueError on duplicate B/L number or job lock.
    """
    from managers.shipment_manager import _ensure_job_unlocked
    _ensure_job_unlocked(job_no)

    if bl_type not in BL_TYPES:
        raise ValueError(f"bl_type must be one of {BL_TYPES}")

    data = prefill_bl_from_job(job_no, bl_type)
    if extra_data:
        data.update(extra_data)

    # Generate B/L number if not provided
    if not data.get("bl_no"):
        data["bl_no"] = generate_document_number(bl_type, _safe_date(data.get("etd")))

    data["created_by"] = _s(user.get("username"), "system")
    data.setdefault("status", "Draft")

    cols = list(data.keys())
    vals = list(data.values())
    placeholders = ", ".join(["%s"] * len(cols))
    columns = ", ".join(cols)

    with get_connection() as conn:
        with conn.cursor() as cur:
            try:
                cur.execute(
                    f"INSERT INTO bills_of_lading ({columns}) VALUES ({placeholders}) RETURNING id",
                    tuple(vals)
                )
                row = cur.fetchone()
                conn.commit()
                return row["id"] if row else cur.lastrowid
            except Exception as e:
                conn.rollback()
                err = str(e)
                if "UNIQUE" in err or "unique" in err:
                    raise ValueError(f"B/L number '{data['bl_no']}' already exists.")
                raise


def get_bl(bl_id: int) -> Optional[Dict]:
    """Fetch a B/L record by id. Returns None if not found."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM bills_of_lading WHERE id = %s AND tenant_id = %s", (bl_id,))
            row = cur.fetchone()
            return dict(row) if row else None


def get_bl_by_no(bl_no: str) -> Optional[Dict]:
    """Fetch a B/L record by bl_no."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM bills_of_lading WHERE bl_no = %s", (bl_no,))
            row = cur.fetchone()
            return dict(row) if row else None


def list_bls(job_no: Optional[str] = None, status: Optional[str] = None) -> List[Dict]:
    """List B/Ls with optional filters, scoped by tenant. Recovers gracefully if table is missing."""
    tenant_id = get_current_tenant_id()
    sql = "SELECT * FROM bills_of_lading WHERE tenant_id = %s"
    params = [tenant_id]
    
    if job_no:
        sql += " AND job_no = %s"
        params.append(job_no)
    if status:
        sql += " AND status = %s"
        params.append(status)
        
    sql += " ORDER BY created_at ASC"

    with get_connection() as conn:
        with conn.cursor() as cur:
            try:
                cur.execute(sql, tuple(params))
                return [dict(r) for r in cur.fetchall()]
            except Exception as e:
                # Graceful degradation if bills_of_lading table does not exist
                print(f"[SCHEMA GAP WARNING] bills_of_lading table query failed: {e}")
                return []



def update_bl(bl_id: int, data: Dict[str, Any]) -> bool:
    """
    Update editable fields on a DRAFT or SUBMITTED B/L.
    Validates numeric fields.
    Does NOT touch job/booking/quotation data.
    """
    _ensure_bl_unlocked(bl_id)

    # Numeric validation
    for field, label in [("gross_weight", "Gross Weight"), ("measurement_cbm", "CBM"), ("package_qty", "Package Qty")]:
        if field in data:
            val = _f(data[field])
            if val < 0:
                raise ValueError(f"{label} must be >= 0")
            data[field] = val

    # Remove protected fields
    for protected in ("id", "bl_no", "job_no", "shipment_id", "booking_no", "created_at", "created_by"):
        data.pop(protected, None)

    if not data:
        return False

    sets = ", ".join([f"{k}=%s" for k in data.keys()])
    values = list(data.values())
    values.append(bl_id)

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"UPDATE bills_of_lading SET {sets}, updated_at=CURRENT_TIMESTAMP WHERE id = %s AND tenant_id = %s",
                tuple(values)
            )
            conn.commit()
            return cur.rowcount > 0


def delete_bl(bl_id: int) -> bool:
    """
    Delete a DRAFT / SUBMITTED B/L.
    bl_containers rows are removed via ON DELETE CASCADE.
    Never removes Job containers.
    """
    _ensure_bl_unlocked(bl_id)
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM bills_of_lading WHERE id = %s AND tenant_id = %s", (bl_id,))
            conn.commit()
            return cur.rowcount > 0


def update_bl_status(bl_id: int, new_status: str) -> bool:
    """
    Transition a B/L through its lifecycle.
    Validates required fields before Issuing.
    """
    doc = get_bl(bl_id)
    if not doc:
        raise ValueError(f"B/L id={bl_id} not found.")

    old_status = doc.get("status", "Draft")
    if not can_transition_bl_status(old_status, new_status):
        allowed = BL_STATUS_FLOW.get(old_status, [])
        raise ValueError(
            f"Invalid B/L status transition from '{old_status}' to '{new_status}'. "
            f"Allowed: {allowed}"
        )

    # Validate required fields before Issued
    if new_status == "Issued":
        missing = []
        for req in ("shipper", "consignee", "port_of_loading", "port_of_discharge", "description_of_goods"):
            if not _s(doc.get(req)):
                missing.append(req)
        if missing:
            raise ValueError(f"Cannot Issue B/L — missing required fields: {', '.join(missing)}")

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE bills_of_lading SET status=%s, updated_at=CURRENT_TIMESTAMP WHERE id=%s",
                (new_status, bl_id)
            )
            conn.commit()
            return cur.rowcount > 0


# =========================================================
# CONTAINER MAPPING
# =========================================================

def list_bl_containers(bl_id: int) -> List[Dict]:
    """List all containers linked to a B/L via bl_containers junction."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT c.id, c.container_no, c.container_size, c.container_type,
                       c.seal_no, c.vgm_kg, c.tare_weight, c.gross_weight,
                       c.job_no, bc.id AS junction_id
                FROM   containers c
                JOIN   bl_containers bc ON c.id = bc.container_id
                WHERE  bc.bl_id = %s
                ORDER  BY c.container_no
            """, (bl_id,))
            return [dict(r) for r in cur.fetchall()]


def add_bl_container(bl_id: int, container_id: int) -> bool:
    """
    Link an existing Job container to a B/L.
    Validates:
      1. Container must exist.
      2. Container must belong to the SAME Job as the B/L.
      3. No duplicate mapping.
    """
    doc = _ensure_bl_unlocked(bl_id)
    bl_job_no = doc.get("job_no")

    with get_connection() as conn:
        with conn.cursor() as cur:
            # Fetch container to verify existence & same-job
            cur.execute("SELECT job_no FROM containers WHERE id = %s AND tenant_id = %s", (container_id,))
            c_row = cur.fetchone()
            if not c_row:
                raise ValueError(f"Container id={container_id} does not exist.")
            if c_row["job_no"] != bl_job_no:
                raise ValueError(
                    f"Container belongs to Job '{c_row['job_no']}', "
                    f"but B/L belongs to Job '{bl_job_no}'. Cross-job mapping is forbidden."
                )

            try:
                cur.execute(
                    "INSERT INTO bl_containers (bl_id, container_id) VALUES (%s, %s)",
                    (bl_id, container_id)
                )
                conn.commit()
                return cur.rowcount > 0
            except Exception as e:
                conn.rollback()
                if "UNIQUE" in str(e) or "unique" in str(e):
                    return True  # Already linked — idempotent
                raise


def remove_bl_container(bl_id: int, container_id: int) -> bool:
    """
    Remove a container link from a B/L.
    Does NOT delete the actual container from the Job.
    """
    _ensure_bl_unlocked(bl_id)
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM bl_containers WHERE bl_id=%s AND container_id=%s",
                (bl_id, container_id)
            )
            conn.commit()
            return cur.rowcount > 0