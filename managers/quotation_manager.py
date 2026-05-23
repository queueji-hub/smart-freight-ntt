from datetime import date
from typing import List, Dict, Any, Optional
from database.connection import get_connection
from managers.customer_manager import upsert_customer

def create_quotation(quotation: Dict[str, Any], items: List[Dict[str, Any]]) -> str:
    """Create a new quotation with transaction safety."""
    quotation_no = _generate_quotation_no(quotation["job_type"], quotation.get("quotation_date"))
    upsert_customer(quotation.get("customer_name"), quotation.get("attention"), quotation.get("tel"))
    
    with get_connection() as conn:
        # Create Header
        cur = conn.execute("""
            INSERT INTO quotations (quotation_no, job_type, customer_id, customer_name, shipper_cnee, carrier, pol, pod, 
                                    service_type, attention, tel, incoterm, commodity, weight, quantity_desc, 
                                    payment_term, quotation_date, validity_date, subject, terms_conditions, prepared_by) 
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id
        """, (
            quotation_no, quotation["job_type"], quotation.get("customer_id"), quotation.get("customer_name"), 
            quotation.get("shipper_cnee"), quotation.get("carrier"), quotation.get("pol"), quotation.get("pod"), 
            quotation.get("service_type"), quotation.get("attention"), quotation.get("tel"), quotation.get("incoterm"), 
            quotation.get("commodity"), quotation.get("weight"), quotation.get("quantity_desc"), quotation.get("payment_term", "30 Days"), 
            quotation.get("quotation_date"), quotation.get("validity_date"), quotation.get("subject"), quotation.get("terms_conditions"), 
            quotation.get("prepared_by")
        ))
        qid = cur.fetchone()['id']
        
        # Create Items
        for idx, item in enumerate(items):
            conn.execute("""
                INSERT INTO quotation_items (quotation_id, description, currency, price, unit, remark, sort_order) 
                VALUES (%s,%s,%s,%s,%s,%s,%s)
            """, (qid, item["description"], item.get("currency", "USD"), item["price"], item.get("unit"), item.get("remark"), idx))
        
        conn.commit()
    return quotation_no

def update_quotation(quotation_no: str, data: Dict[str, Any], items: List[Dict[str, Any]], new_quotation_no: str = None) -> bool:
    """Update quotation details and replace all items."""
    final_no = new_quotation_no or quotation_no
    with get_connection() as conn:
        row = conn.execute("SELECT id FROM quotations WHERE quotation_no=%s", (quotation_no,)).fetchone()
        if not row: return False
        qid = row['id']
        
        conn.execute("""
            UPDATE quotations SET quotation_no=%s, customer_name=%s, shipper_cnee=%s, carrier=%s, pol=%s, pod=%s, 
            service_type=%s, attention=%s, tel=%s, incoterm=%s, commodity=%s, weight=%s, quantity_desc=%s, 
            payment_term=%s, quotation_date=%s, validity_date=%s, subject=%s, terms_conditions=%s 
            WHERE id=%s
        """, (final_no, data.get("customer_name"), data.get("shipper_cnee"), data.get("carrier"), data.get("pol"), 
              data.get("pod"), data.get("service_type"), data.get("attention"), data.get("tel"), data.get("incoterm"), 
              data.get("commodity"), data.get("weight"), data.get("quantity_desc"), data.get("payment_term"), 
              data.get("quotation_date"), data.get("validity_date"), data.get("subject"), data.get("terms_conditions"), qid))
        
        # Update items (Delete & Insert strategy is safest for lists)
        conn.execute("DELETE FROM quotation_items WHERE quotation_id=%s", (qid,))
        for idx, item in enumerate(items):
            conn.execute("""
                INSERT INTO quotation_items (quotation_id, description, currency, price, unit, remark, sort_order) 
                VALUES (%s,%s,%s,%s,%s,%s,%s)
            """, (qid, item["description"], item.get("currency", "USD"), item["price"], item.get("unit"), item.get("remark"), idx))
        
        conn.commit()
    return True

def get_quotation_by_no(quotation_no):
    """
    Get quotation by quotation number
    """

    with get_connection() as conn:

        result = conn.execute(
            """
            SELECT *
            FROM quotations
            WHERE quotation_no = %s
            """,
            (quotation_no,)
        ).fetchone()

        return dict(result) if result else None

def list_quotations():
    """
    Return all quotations
    """

    with get_connection() as conn:

        results = conn.execute(
            """
            SELECT *
            FROM quotations
            ORDER BY id DESC
            """
        ).fetchall()

        return [
            dict(r)
            for r in results
        ]

def upsert_customer(customer_data):
    """
    Create or update customer placeholder
    """

    return customer_data

def duplicate_quotation(quotation_no):
    """
    Duplicate quotation placeholder
    """

    original = get_quotation_by_no(quotation_no)

    if not original:
        return None

    # TODO:
    # create duplicated quotation logic later

    return original