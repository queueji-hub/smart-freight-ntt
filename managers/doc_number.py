from datetime import date, datetime
from database.connection import get_connection

VALID_DOC_TYPES = ("INV", "BN", "CN", "DN", "SOA")

def generate_doc_number(doc_type: str, ref_date=None, digits: int = 4) -> str:
    """Generate next sequential document number using atomic updates."""
    if doc_type not in VALID_DOC_TYPES:
        raise ValueError(f"Invalid doc_type: {doc_type}")
    
    # Resolve Date
    ref = ref_date if isinstance(ref_date, date) else date.today()
    if isinstance(ref_date, str):
        ref = datetime.strptime(ref_date, "%Y-%m-%d").date()
    
    yymm = f"{ref.year % 100:02d}{ref.month:02d}"
    
    # Atomic generation
    with get_connection() as conn:
        # ด้วย RealDictCursor, row ที่ได้จะเป็น dict
        row = conn.execute("""
            INSERT INTO doc_counters (doc_type, yymm, last_running)
            VALUES (%s, %s, 1)
            ON CONFLICT (doc_type, yymm) 
            DO UPDATE SET last_running = doc_counters.last_running + 1
            RETURNING last_running
        """, (doc_type, yymm)).fetchone()
        
        conn.commit()
        running_number = row['last_running']
    
    return f"{doc_type}{yymm}{running_number:0{digits}d}"