"""Atomic Job Number generator: [{COMPANY}-]{TYPE}{YY}{MM}{NNNN}.

Examples:
  SI26050004       - default (no company prefix)
  NTT-SE2605001    - with company prefix
"""
from datetime import date, datetime
from typing import Optional
from database.connection import get_connection


VALID_JOB_TYPES = ("SE", "SI", "AE", "AI", "TE", "TI")


def _resolve_date(ref_date) -> date:
    if ref_date is None:
        return date.today()
    if isinstance(ref_date, str):
        return datetime.strptime(ref_date, "%Y-%m-%d").date()
    if isinstance(ref_date, datetime):
        return ref_date.date()
    return ref_date


def generate_job_number(job_type: str,
                        ref_date=None,
                        company_prefix: Optional[str] = None,
                        digits: int = 4) -> str:
    """Generate next sequential job number.
    
    Args:
        job_type: One of SE/SI/AE/AI/TE/TI
        ref_date: Reference date (default: today)
        company_prefix: Optional prefix like "NTT" → "NTT-SE26050001"
        digits: Number of digits in running number (default 4)
    """
    if job_type not in VALID_JOB_TYPES:
        raise ValueError(f"Invalid job_type: {job_type}")
    
    ref = _resolve_date(ref_date)
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
    
    running = f"{row[0]:0{digits}d}"
    base = f"{job_type}{yymm}{running}"
    if company_prefix:
        return f"{company_prefix.strip().rstrip('-')}-{base}"
    return base


def generate_booking_number(job_type: str, ref_date=None,
                             company_prefix: Optional[str] = None) -> str:
    """Generate booking number — same format as job number, prefixed with B-."""
    base = generate_job_number(job_type, ref_date, company_prefix)
    return f"B-{base}" if not company_prefix else base.replace("-", "-B-", 1)
