"""Atomic Job Number generator: {TYPE}{YY}{MM}{NNNN}, e.g. SI26050004."""
from datetime import date, datetime
from database.connection import get_connection


def generate_job_number(job_type, ref_date=None) -> str:
    """Generate next sequential job number for the given type and month.
    
    Format: {JOB_TYPE}{YY}{MM}{4-digit running}
    Example: SI26050004 (Sea Import, May 2026, running #4)
    """
    if job_type not in ("SE", "SI", "AE", "AI", "TE", "TI"):
        raise ValueError(f"Invalid job_type: {job_type}")
    
    # Accept date, datetime, ISO string, or None
    if ref_date is None:
        ref = date.today()
    elif isinstance(ref_date, str):
        ref = datetime.strptime(ref_date, "%Y-%m-%d").date()
    elif isinstance(ref_date, datetime):
        ref = ref_date.date()
    else:
        ref = ref_date
    yy = f"{ref.year % 100:02d}"
    mm = f"{ref.month:02d}"
    yymm = f"{yy}{mm}"
    
    with get_connection() as conn:
        conn.execute("""
            INSERT INTO job_counters (job_type, yymm, last_running)
            VALUES (?, ?, 1)
            ON CONFLICT (job_type, yymm) DO UPDATE
            SET last_running = last_running + 1
        """, (job_type, yymm))
        row = conn.execute(
            "SELECT last_running FROM job_counters WHERE job_type=? AND yymm=?",
            (job_type, yymm)
        ).fetchone()
    
    return f"{job_type}{yymm}{row[0]:04d}"
