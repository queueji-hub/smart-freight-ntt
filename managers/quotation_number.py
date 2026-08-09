"""
Quotation Number Sequence Generator
Generates unique sequential quotation tracking identifiers (e.g., QT-2608-0001)
"""

from datetime import datetime
from database.connection import get_connection

def generate_quotation_number(job_type: str = "FREIGHT", date_obj: datetime = None) -> str:
    """
    Generates an incremental quotation document number based on year, month, and sequence index.
    """
    now = date_obj or datetime.now()
    prefix = "QT"
    yymm = now.strftime("%y%m")
    base_prefix = f"{prefix}-{yymm}-"

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT quotation_no FROM quotations 
                WHERE quotation_no LIKE %s 
                ORDER BY quotation_no DESC LIMIT 1
            """, (f"{base_prefix}%",))
            row = cur.fetchone()

            if row:
                last_no = row.get("quotation_no", "") if isinstance(row, dict) else row[0]
                try:
                    last_seq = int(last_no.split("-")[-1])
                    seq = last_seq + 1
                except (ValueError, IndexError):
                    seq = 1
            else:
                seq = 1

            return f"{base_prefix}{seq:04d}"
