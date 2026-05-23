"""Atomic Job Number generator."""
from datetime import date, datetime
from typing import Optional
from database.connection import get_connection

VALID_JOB_TYPES = ("SE", "SI", "AE", "AI", "TE", "TI")

def _ensure_table():
    """Ensure the job_counters table exists."""
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS job_counters (
                job_type TEXT NOT NULL,
                yymm TEXT NOT NULL,
                last_running INTEGER DEFAULT 0,
                PRIMARY KEY (job_type, yymm)
            )
        """)

def _resolve_date(ref_date) -> date:
    if ref_date is None:
        return date.today()
    if isinstance(ref_date, str):
        try:
            return datetime.strptime(ref_date, "%Y-%m-%d").date()
        except ValueError:
            return date.today()
    if isinstance(ref_date, datetime):
        return ref_date.date()
    return ref_date

def generate_job_number(job_type: str,
                        ref_date=None,
                        company_prefix: Optional[str] = None,
                        digits: int = 4) -> str:
    """Generate next sequential job number using PostgreSQL atomic updates."""
    _ensure_table()
    if job_type not in VALID_JOB_TYPES:
        raise ValueError(f"Invalid job_type: {job_type}")
    
    ref = _resolve_date(ref_date)
    yymm = f"{ref.year % 100:02d}{ref.month:02d}"
    
    with get_connection() as conn:
        # Atomic increment using RETURNING
        row = conn.execute("""
            INSERT INTO job_counters (job_type, yymm, last_running)
            VALUES (%s, %s, 1)
            ON CONFLICT (job_type, yymm) 
            DO UPDATE SET last_running = job_counters.last_running + 1
            RETURNING last_running
        """, (job_type, yymm)).fetchone()
    
    # Handle Row result (supports both tuple and dict-like cursor results)
    running_val = row[0] if row and hasattr(row, '__getitem__') and not isinstance(row, dict) else row['last_running']
    
    running = f"{running_val:0{digits}d}"
    base = f"{job_type}{yymm}{running}"
    
    if company_prefix:
        prefix = company_prefix.strip().rstrip('-')
        return f"{prefix}-{base}"
    return base

def generate_booking_number(job_type: str, ref_date=None,
                             company_prefix: Optional[str] = None) -> str:
    """Generate booking number."""
    base = generate_job_number(job_type, ref_date, company_prefix)
    # logic: if has prefix, insert B, else prepend B-
    if company_prefix:
        parts = base.split('-', 1)
        return f"{parts[0]}-B-{parts[1]}"
    return f"B-{base}"