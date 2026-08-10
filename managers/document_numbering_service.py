"""
Centralized Document Numbering Service (P1.X Architecture)
Provides atomic, race-condition-free, tenant-isolated document numbering sequences.
"""

from datetime import datetime, date
import re
from typing import Optional
from database.connection import get_connection
from managers.tenant_context import get_current_tenant_id

def _resolve_date(ref_date) -> date:
    if isinstance(ref_date, date):
        return ref_date
    if isinstance(ref_date, datetime):
        return ref_date.date()
    if isinstance(ref_date, str):
        try:
            return datetime.strptime(ref_date, "%Y-%m-%d").date()
        except ValueError:
            pass
    return date.today()

def normalize_doc_no(doc_no: str) -> str:
    """
    Normalizes a document number for search convenience by stripping
    spaces, hyphens, slashes, dots, and forcing uppercase.
    Example: 'INV-2608-0001' -> 'INV26080001'
    """
    if not doc_no:
        return ""
    # Remove hyphens, spaces, slashes, dots, then uppercase
    normalized = re.sub(r'[\s\-\/\.]', '', doc_no)
    return normalized.upper()

def generate_document_number(doc_type: str, ref_date=None, digits: int = 4) -> str:
    """
    Generates the next sequential document number using an atomic UPSERT.
    Format: {PREFIX}-{YYMM}-{SEQ} (e.g., QT-2608-0001)
    
    Args:
        doc_type (str): The canonical prefix (e.g., "QT", "INV", "JOB")
        ref_date (date|str|None): The business date to base the sequence on (YYMM)
        digits (int): Padding for the sequence number (default: 4)
        
    Returns:
        str: The generated human-readable business document number.
    """
    tenant_id = get_current_tenant_id()
    if not tenant_id:
        raise RuntimeError("tenant_id is strictly required to generate document numbers.")
        
    d = _resolve_date(ref_date)
    yymm = d.strftime("%y%m")
    
    with get_connection() as conn:
        with conn.cursor() as cur:
            # Atomic generation
            # NOTE: RealDictCursor or sqlite3.Row will return dictionary-like access
            cur.execute("""
                INSERT INTO document_counters (tenant_id, doc_type, yymm, last_running)
                VALUES (%s, %s, %s, 1)
                ON CONFLICT (tenant_id, doc_type, yymm) 
                DO UPDATE SET last_running = document_counters.last_running + 1
                RETURNING last_running;
            """, (tenant_id, doc_type, yymm))
            row = cur.fetchone()
            
            # In SQLite via cursor.execute, RETURNING works if the DB engine supports it (SQLite 3.35+). 
            # Python's built-in sqlite3 generally supports it.
            # Fallback if RETURNING didn't return a row (driver issues):
            if not row:
                cur.execute(
                    "SELECT last_running FROM document_counters WHERE tenant_id=%s AND doc_type=%s AND yymm=%s", 
                    (tenant_id, doc_type, yymm)
                )
                row = cur.fetchone()
                
            conn.commit()
            
            running_val = row['last_running'] if isinstance(row, dict) or hasattr(row, 'keys') else row[0]
        
    seq = f"{running_val:0{digits}d}"
    return f"{doc_type.upper()}-{yymm}-{seq}"
