"""Quotation CRUD operations."""
from datetime import date, datetime, timedelta
from typing import List, Dict, Any, Optional
from database.connection import get_connection
from managers.customer_manager import upsert_customer

def _ensure_table():
    """Ensure quotations, quotation_items, and job_counters tables exist."""
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS quotations (
                id SERIAL PRIMARY KEY,
                quotation_no TEXT UNIQUE NOT NULL,
                job_type TEXT NOT NULL,
                customer_id INTEGER,
                customer_name TEXT,
                shipper_cnee TEXT,
                carrier TEXT,
                pol TEXT,
                pod TEXT,
                service_type TEXT,
                attention TEXT,
                tel TEXT,
                incoterm TEXT,
                commodity TEXT,
                weight TEXT,
                quantity_desc TEXT,
                payment_term TEXT,
                quotation_date DATE,
                validity_date DATE,
                subject TEXT,
                terms_conditions TEXT,
                prepared_by TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS quotation_items (
                id SERIAL PRIMARY KEY,
                quotation_id INTEGER REFERENCES quotations(id) ON DELETE CASCADE,
                description TEXT,
                currency TEXT,
                price NUMERIC(15,2),
                unit TEXT,
                remark TEXT,
                sort_order INTEGER
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS job_counters (
                job_type TEXT,
                yymm TEXT,
                last_running INTEGER,
                PRIMARY KEY (job_type, yymm)
            )
        """)

def _generate_quotation_no(job_type: str, ref_date=None) -> str:
    """Generate quotation number using PostgreSQL atomic increment."""
    if job_type not in ("SE", "SI", "AE", "AI", "TE", "TI"):
        raise ValueError(f"Invalid job_type: {job_type}")
    
    ref = ref_date if isinstance(ref_date, date) else date.today()
    yymm = f"{ref.year % 100:02d}{ref.month:02d}"
    counter_key = f"Q-{job_type}"
    
    with get_connection() as conn:
        row = conn.execute("""
            INSERT INTO job_counters (job_type, yymm, last_running)
            VALUES (%s, %s, 1)
            ON CONFLICT (job_type, yymm) 
            DO UPDATE SET last_running = job_counters.last_running + 1
            RETURNING last_running
        """, (counter_key, yymm)).fetchone()
    
    return f"Q{job_type}{yymm}{row[0]:04d}"

def list_quotations(limit: int = 50) -> List[Dict[str, Any]]:
    """Retrieve list of all quotations."""
    _ensure_table()
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM quotations ORDER BY created_at DESC LIMIT %s", (limit,)).fetchall()
        return [dict(r) for r in rows]

def create_quotation(quotation: Dict[str, Any], items: List[Dict[str, Any]]) -> str:
    """Create a quotation with items."""
    _ensure_table()
    quotation_no = _generate_quotation_no(quotation["job_type"], quotation.get("quotation_date"))
    
    upsert_customer(quotation.get("customer_name"), quotation.get("attention"), quotation.get("tel"))
    
    with get_connection() as conn:
        cur = conn.execute("""
            INSERT INTO quotations (
                quotation_no, job_type, customer_id, customer_name, shipper_cnee,
                carrier, pol, pod, service_type, attention, tel, incoterm,
                commodity, weight, quantity_desc, payment_term,
                quotation_date, validity_date, subject, terms_conditions, prepared_by
            ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            RETURNING id
        """, (
            quotation_no, quotation["job_type"], quotation.get("customer_id"),
            quotation.get("customer_name"), quotation.get("shipper_cnee"),
            quotation.get("carrier"), quotation.get("pol"), quotation.get("pod"),
            quotation.get("service_type"), quotation.get("attention"), quotation.get("tel"),
            quotation.get("incoterm"), quotation.get("commodity"), quotation.get("weight"),
            quotation.get("quantity_desc"), quotation.get("payment_term", "30 Days"),
            quotation.get("quotation_date"), quotation.get("validity_date"),
            quotation.get("subject"), quotation.get("terms_conditions"),
            quotation.get("prepared_by")
        ))
        qid = cur.fetchone()[0]
        
        for idx, item in enumerate(items):
            conn.execute("""
                INSERT INTO quotation_items (quotation_id, description, currency, price, unit, remark, sort_order)
                VALUES (%s,%s,%s,%s,%s,%s,%s)
            """, (qid, item["description"], item.get("currency", "USD"),
                  item["price"], item.get("unit"), item.get("remark"), idx))
    
    return quotation_no

def get_quotation_by_no(quotation_no: str) -> Optional[Dict[str, Any]]:
    """Fetch quotation by number."""
    _ensure_table()
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM quotations WHERE quotation_no = %s", (quotation_no,)).fetchone()
        if not row: return None
        quotation = dict(row)
        items = conn.execute("SELECT * FROM quotation_items WHERE quotation_id = %s ORDER BY sort_order", (quotation["id"],)).fetchall()
        quotation["items"] = [dict(i) for i in items]
        return quotation

def duplicate_quotation(quotation_no: str) -> Optional[str]:
    """Duplicate an existing quotation and return the new quotation number."""
    original = get_quotation_by_no(quotation_no)
    if not original:
        return None
    
    # แยกส่วน items ออกมา
    items = original.pop("items", [])
    
    # ลบ field ที่ไม่ต้องการให้ซ้ำ (เช่น id, created_at)
    original.pop("id", None)
    original.pop("created_at", None)
    original.pop("quotation_no", None)
    
    # อัปเดตวันที่เป็นวันนี้
    original["quotation_date"] = date.today()
    
    return create_quotation(original, items)

def update_quotation(quotation_no: str, data: Dict[str, Any], items: List[Dict[str, Any]], new_quotation_no: str = None) -> bool:
    """Update quotation header and items."""
    _ensure_table()
    with get_connection() as conn:
        row = conn.execute("SELECT id FROM quotations WHERE quotation_no=%s", (quotation_no,)).fetchone()
        if not row: return False
        qid = row[0]
        
        final_no = new_quotation_no or quotation_no
        conn.execute("""
            UPDATE quotations SET quotation_no=%s, customer_name=%s, shipper_cnee=%s, carrier=%s, pol=%s, pod=%s,
            service_type=%s, attention=%s, tel=%s, incoterm=%s, commodity=%s, weight=%s, quantity_desc=%s, 
            payment_term=%s, quotation_date=%s, validity_date=%s, subject=%s, terms_conditions=%s
            WHERE id=%s
        """, (final_no, data.get("customer_name"), data.get("shipper_cnee"), data.get("carrier"), data.get("pol"), 
              data.get("pod"), data.get("service_type"), data.get("attention"), data.get("tel"), data.get("incoterm"), 
              data.get("commodity"), data.get("weight"), data.get("quantity_desc"), data.get("payment_term"), 
              data.get("quotation_date"), data.get("validity_date"), data.get("subject"), data.get("terms_conditions"), qid))
        
        conn.execute("DELETE FROM quotation_items WHERE quotation_id=%s", (qid,))
        for idx, item in enumerate(items):
            conn.execute("""
                INSERT INTO quotation_items (quotation_id, description, currency, price, unit, remark, sort_order)
                VALUES (%s,%s,%s,%s,%s,%s,%s)
            """, (qid, item["description"], item.get("currency", "USD"), item["price"], item.get("unit"), item.get("remark"), idx))
    return True