"""Document number generator for financial docs (Invoice, BN, CN, DN, SOA).

Format: {DOC_TYPE}{YY}{MM}{NNNN}
Examples:
  INV26050001  - Invoice
  BN26050001   - Billing Note
  CN26050001   - Credit Note
  DN26050001   - Debit Note
  SOA26050001  - Statement of Account
"""
from datetime import date, datetime
from database.connection import get_connection


VALID_DOC_TYPES = ("INV", "BN", "CN", "DN", "SOA")


def generate_doc_number(doc_type: str, ref_date=None, digits: int = 4) -> str:
    """Generate next sequential document number."""
    if doc_type not in VALID_DOC_TYPES:
        raise ValueError(f"Invalid doc_type: {doc_type}")
    
    if ref_date is None:
        ref = date.today()
    elif isinstance(ref_date, str):
        ref = datetime.strptime(ref_date, "%Y-%m-%d").date()
    elif isinstance(ref_date, datetime):
        ref = ref_date.date()
    else:
        ref = ref_date
    
    yymm = f"{ref.year % 100:02d}{ref.month:02d}"
    
    with get_connection() as conn:
        conn.execute("""
            INSERT INTO doc_counters (doc_type, yymm, last_running)
            VALUES (?, ?, 1)
            ON CONFLICT (doc_type, yymm) DO UPDATE
            SET last_running = last_running + 1
        """, (doc_type, yymm))
        row = conn.execute(
            "SELECT last_running FROM doc_counters WHERE doc_type=? AND yymm=?",
            (doc_type, yymm)
        ).fetchone()
    
    return f"{doc_type}{yymm}{row[0]:0{digits}d}"
