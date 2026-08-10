from datetime import date, datetime
from typing import Optional
from database.connection import get_connection

VALID_JOB_TYPES = ("SE", "SI", "AE", "AI", "TE", "TI")

def _resolve_date(ref_date) -> date:
    if isinstance(ref_date, date): return ref_date
    if isinstance(ref_date, datetime): return ref_date.date()
    if isinstance(ref_date, str):
        try: return datetime.strptime(ref_date, "%Y-%m-%d").date()
        except ValueError: pass
    return date.today()

def generate_job_number(job_type: str, ref_date=None, 
                        company_prefix: Optional[str] = None, digits: int = 4) -> str:
    """Generate next sequential job number using PostgreSQL atomic updates."""
    if job_type not in VALID_JOB_TYPES:
        raise ValueError(f"Invalid job_type: {job_type}")
    
    yymm = _resolve_date(ref_date).strftime("%y%m")
    
    with get_connection() as conn:
        # Atomic increment
        conn.execute("""
            INSERT INTO job_counters (job_type, yymm, last_running)
            VALUES (%s, %s, 1)
            ON CONFLICT (job_type, yymm) 
            DO UPDATE SET last_running = job_counters.last_running + 1
        """, (job_type, yymm))
        
        row = conn.execute(
            "SELECT last_running FROM job_counters WHERE job_type=%s AND yymm=%s", 
            (job_type, yymm)
        ).fetchone()
        
        conn.commit() # มั่นใจว่าบันทึกค่าลงตารางจริง
        running_val = row['last_running']
    
    running = f"{running_val:0{digits}d}"
    base = f"{job_type}{yymm}{running}"
    
    prefix = "NTT"
    if company_prefix:
        p = company_prefix.strip().rstrip('-')
        if p and p.lower() not in ("default", "none"):
            prefix = p
    return f"{prefix}-{base}"

def generate_booking_number(job_type: str, ref_date=None, 
                            company_prefix: Optional[str] = None) -> str:
    """Generate booking number."""
    base = generate_job_number(job_type, ref_date, company_prefix)
    if "-" in base:
        parts = base.split('-', 1)
        return f"{parts[0]}-B-{parts[1]}"
    return f"NTT-B-{base}"