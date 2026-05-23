"""Document number generator for financial docs."""
from datetime import date, datetime
from database.connection import get_connection

VALID_DOC_TYPES = ("INV", "BN", "CN", "DN", "SOA")

def _ensure_table():
    """Ensure the doc_counters table exists."""
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS doc_counters (
                doc_type TEXT NOT NULL,
                yymm TEXT NOT NULL,
                last_running INTEGER DEFAULT 0,
                PRIMARY KEY (doc_type, yymm)
            )
        """)

def generate_doc_number(doc_type: str, ref_date=None, digits: int = 4) -> str:
    """Generate next sequential document number."""
    _ensure_table()
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
        # 🟢 แก้ไข: ใช้ %s และ ON CONFLICT ของ PostgreSQL
        conn.execute("""
            INSERT INTO doc_counters (doc_type, yymm, last_running)
            VALUES (%s, %s, 1)
            ON CONFLICT (doc_type, yymm) 
            DO UPDATE SET last_running = doc_counters.last_running + 1
        """, (doc_type, yymm))
        
        # 🟢 แก้ไข: ใช้ %s
        row = conn.execute(
            "SELECT last_running FROM doc_counters WHERE doc_type=%s AND yymm=%s",
            (doc_type, yymm)
        ).fetchone()
    
    # ดึงค่าจาก row (อ้างอิงตาม index หรือชื่อคอลัมน์ ขึ้นอยู่กับการ config ของ connection)
    running_number = row[0] if isinstance(row, (list, tuple)) else row['last_running']
    
    return f"{doc_type}{yymm}{running_number:0{digits}d}"