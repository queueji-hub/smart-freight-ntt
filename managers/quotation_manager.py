"""Quotation CRUD operations."""
from datetime import date, datetime, timedelta
from typing import List, Dict, Any, Optional
from database.connection import get_connection
from managers.customer_manager import upsert_customer


def _generate_quotation_no(job_type: str, ref_date=None) -> str:
    """Generate quotation number with Q prefix using a separate counter.
    
    Format: Q{JOB_TYPE}{YYMM}{NNNN}, e.g. QSE26050001
    Uses 'Q-{job_type}' as counter key so it's separate from shipment counter.
    """
    if job_type not in ("SE", "SI", "AE", "AI", "TE", "TI"):
        raise ValueError(f"Invalid job_type: {job_type}")
    
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
    counter_key = f"Q-{job_type}"
    
    with get_connection() as conn:
        conn.execute("""
            INSERT INTO job_counters (job_type, yymm, last_running)
            VALUES (?, ?, 1)
            ON CONFLICT (job_type, yymm) DO UPDATE
            SET last_running = last_running + 1
        """, (counter_key, yymm))
        row = conn.execute(
            "SELECT last_running FROM job_counters WHERE job_type=? AND yymm=?",
            (counter_key, yymm)
        ).fetchone()
    
    return f"Q{job_type}{yymm}{row[0]:04d}"


def create_quotation(quotation: Dict[str, Any], items: List[Dict[str, Any]]) -> str:
    """Create a quotation with items. Returns the generated quotation_no.
    
    Format: Q{JOB_TYPE}{YYMM}{NNNN} (e.g. QSE26050001)
    The 'Q' prefix distinguishes quotations from shipment job numbers.
    Uses a separate counter from shipments so numbers don't collide.
    """
    quotation_no = _generate_quotation_no(
        quotation["job_type"], quotation.get("quotation_date")
    )
    
    # Auto-save customer info
    upsert_customer(
        quotation.get("customer_name"),
        quotation.get("attention"),
        quotation.get("tel"),
    )
    
    with get_connection() as conn:
        cur = conn.execute("""
            INSERT INTO quotations (
                quotation_no, job_type, customer_id, customer_name, shipper_cnee,
                carrier, pol, pod, service_type, attention, tel, incoterm,
                commodity, weight, quantity_desc, payment_term,
                quotation_date, validity_date, subject, terms_conditions, prepared_by
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            quotation_no, quotation["job_type"], quotation.get("customer_id"),
            quotation.get("customer_name"), quotation.get("shipper_cnee"),
            quotation.get("carrier"), quotation.get("pol"), quotation.get("pod"),
            quotation.get("service_type"), quotation.get("attention"), quotation.get("tel"),
            quotation.get("incoterm"), quotation.get("commodity"), quotation.get("weight"),
            quotation.get("quantity_desc"), quotation.get("payment_term", "30 Days"),
            quotation.get("quotation_date"), quotation.get("validity_date"),
            quotation.get("subject"), quotation.get("terms_conditions"),
            quotation.get("prepared_by"),
        ))
        quotation_id = cur.lastrowid
        
        for idx, item in enumerate(items):
            conn.execute("""
                INSERT INTO quotation_items
                (quotation_id, description, currency, price, unit, remark, sort_order)
                VALUES (?,?,?,?,?,?,?)
            """, (
                quotation_id, item["description"], item.get("currency", "USD"),
                item["price"], item.get("unit"), item.get("remark"), idx,
            ))
    
    return quotation_no


def get_quotation_by_no(quotation_no: str) -> Optional[Dict[str, Any]]:
    """Fetch a quotation and its items by quotation_no."""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM quotations WHERE quotation_no = ?", (quotation_no,)
        ).fetchone()
        if not row:
            return None
        quotation = dict(row)
        items = conn.execute(
            "SELECT * FROM quotation_items WHERE quotation_id = ? ORDER BY sort_order",
            (quotation["id"],)
        ).fetchall()
        quotation["items"] = [dict(i) for i in items]
        return quotation


def list_quotations(job_type: Optional[str] = None) -> List[Dict[str, Any]]:
    """List all quotations, optionally filtered by job_type."""
    sql = "SELECT * FROM quotations"
    params = ()
    if job_type:
        sql += " WHERE job_type = ?"
        params = (job_type,)
    sql += " ORDER BY quotation_date DESC, id DESC"
    with get_connection() as conn:
        rows = conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]


def update_quotation(quotation_no: str, data: Dict[str, Any], items: List[Dict[str, Any]], new_quotation_no: str = None) -> bool:
    """Update an existing quotation header + replace all items.
    Optionally change the quotation_no itself."""
    # Auto-save customer info on update
    upsert_customer(
        data.get("customer_name"),
        data.get("attention"),
        data.get("tel"),
    )
    
    with get_connection() as conn:
        row = conn.execute(
            "SELECT id FROM quotations WHERE quotation_no=?", (quotation_no,)
        ).fetchone()
        if not row:
            return False
        qid = row[0]
        
        # Update quotation_no if changed
        final_no = new_quotation_no if new_quotation_no else quotation_no
        
        # Update header fields
        conn.execute("""
            UPDATE quotations SET
                quotation_no=?, customer_name=?, shipper_cnee=?, carrier=?, pol=?, pod=?,
                service_type=?, attention=?, tel=?, incoterm=?, commodity=?,
                weight=?, quantity_desc=?, payment_term=?,
                quotation_date=?, validity_date=?, subject=?, terms_conditions=?
            WHERE id=?
        """, (
            final_no,
            data.get("customer_name"), data.get("shipper_cnee"),
            data.get("carrier"), data.get("pol"), data.get("pod"),
            data.get("service_type"), data.get("attention"), data.get("tel"),
            data.get("incoterm"), data.get("commodity"), data.get("weight"),
            data.get("quantity_desc"), data.get("payment_term"),
            data.get("quotation_date"), data.get("validity_date"),
            data.get("subject"), data.get("terms_conditions"),
            qid,
        ))
        
        # Replace items
        conn.execute("DELETE FROM quotation_items WHERE quotation_id=?", (qid,))
        for idx, item in enumerate(items):
            conn.execute("""
                INSERT INTO quotation_items
                (quotation_id, description, currency, price, unit, remark, sort_order)
                VALUES (?,?,?,?,?,?,?)
            """, (
                qid, item["description"], item.get("currency", "USD"),
                item["price"], item.get("unit"), item.get("remark"), idx,
            ))
    return True


def duplicate_quotation(source_no: str, new_job_type: str = None) -> Optional[str]:
    """Copy an existing quotation to a new one with a new quotation_no.
    Returns the new quotation_no or None if source not found."""
    source = get_quotation_by_no(source_no)
    if not source:
        return None
    
    job_type = new_job_type or source["job_type"]
    
    new_data = {
        "job_type": job_type,
        "customer_name": source.get("customer_name"),
        "shipper_cnee": source.get("shipper_cnee"),
        "carrier": source.get("carrier"),
        "pol": source.get("pol"),
        "pod": source.get("pod"),
        "service_type": source.get("service_type"),
        "attention": source.get("attention"),
        "tel": source.get("tel"),
        "incoterm": source.get("incoterm"),
        "commodity": source.get("commodity"),
        "weight": source.get("weight"),
        "quantity_desc": source.get("quantity_desc"),
        "payment_term": source.get("payment_term"),
        "quotation_date": date.today().isoformat(),
        "validity_date": (date.today() + timedelta(days=30)).isoformat(),
        "subject": source.get("subject"),
        "terms_conditions": source.get("terms_conditions"),
    }
    
    items = []
    for item in source.get("items", []):
        items.append({
            "description": item["description"],
            "currency": item.get("currency", "USD"),
            "price": item["price"],
            "unit": item.get("unit"),
            "remark": item.get("remark"),
        })
    
    return create_quotation(new_data, items)
