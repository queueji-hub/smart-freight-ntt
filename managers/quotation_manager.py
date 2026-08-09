"""
Quotation Transactional Database Manager
PostgreSQL Stable Release - Production Ready
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from database.connection import get_connection


# =========================================================
# CORE TRANSACTION: CREATE QUOTATION (ACID COMPLIANT)
# =========================================================
def create_quotation(data: Dict[str, Any], items: List[Dict[str, Any]]) -> str:
    """
    Inserts a quotation master record and its child lines atomically.
    Uses PostgreSQL standard placeholders (%s) and sequence generation.
    """
    from managers.quotation_number import generate_quotation_number

    # Generate tracking identity
    q_date_val = data.get("quotation_date") or datetime.now().strftime("%Y-%m-%d")
    v_date_val = data.get("validity_date") or (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")

    if isinstance(q_date_val, str) and len(q_date_val) >= 10:
        try:
            q_date_obj = datetime.strptime(q_date_val[:10], "%Y-%m-%d")
        except ValueError:
            q_date_obj = datetime.now()
    else:
        q_date_obj = datetime.now()
        q_date_val = q_date_obj.strftime("%Y-%m-%d")

    job_type = data.get("job_type") or "SE"
    if job_type not in ["SE", "SI", "AE", "AI", "TE", "TI"]:
        mapping = {"SEA_EXP": "SE", "SEA_IMP": "SI", "AIR_EXP": "AE", "AIR_IMP": "AI", "TRK_EXP": "TE", "TRK_IMP": "TI", "FREIGHT": "SE"}
        job_type = mapping.get(job_type, "SE")

    quotation_no = generate_quotation_number(job_type, q_date_obj)

    with get_connection() as conn:
        with conn.cursor() as cur:
            try:
                # 1. Master Header Record Insertion
                cur.execute("""
                    INSERT INTO quotations (
                        quotation_no, job_type, customer_name, attention, tel,
                        carrier, pol, pod, quotation_date, validity_date,
                        payment_term, commodity, subject, terms_conditions,
                        status, created_by, created_at
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP);
                """, (
                    quotation_no,
                    job_type,
                    data.get("customer_name") or "Valued Customer",
                    data.get("attention", ""),
                    data.get("tel", ""),
                    data.get("carrier", ""),
                    data.get("pol", ""),
                    data.get("pod", ""),
                    q_date_val,
                    v_date_val,
                    data.get("payment_term", "Net 30"),
                    data.get("commodity", ""),
                    data.get("subject", ""),
                    data.get("terms_conditions", ""),
                    "ACTIVE",
                    data.get("created_by", "system")
                ))

                cur.execute("SELECT id FROM quotations WHERE quotation_no = %s LIMIT 1;", (quotation_no,))
                result = cur.fetchone()
                quotation_id = result[0] if isinstance(result, (tuple, list)) else result["id"]

                # 2. Child Line Items Segment Iteration
                for idx, item in enumerate(items):
                    cur.execute("""
                        INSERT INTO quotation_items (
                            quotation_id, description, currency, price, unit, remark, sort_order
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s);
                    """, (
                        quotation_id,
                        item.get("description", ""),
                        item.get("currency", "USD"),
                        float(item.get("price", 0.0)),
                        item.get("unit", "SHPMT"),
                        item.get("remark", ""),
                        idx
                    ))

                conn.commit()
                return quotation_no

            except Exception as e:
                conn.rollback()
                raise RuntimeError(f"Database Transaction Aborted: {str(e)}")


# =========================================================
# DATA FETCHING & SYNCHRONIZATION
# =========================================================
def list_quotations() -> List[Dict[str, Any]]:
    """
    Returns full array index log history sorted dynamically for dataframes.
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT 
                    quotation_no, job_type, customer_name, subject,
                    quotation_date, validity_date, status
                FROM quotations 
                ORDER BY id DESC;
            """)
            rows = cur.fetchall()
            return [dict(r) for r in rows]


def get_quotation_by_no(quotation_no: str) -> Optional[Dict[str, Any]]:
    """
    Fetches aggregate data model mapping Header joined with Child Items rows.
    """
    if not quotation_no:
        return None

    with get_connection() as conn:
        with conn.cursor() as cur:
            # Fetch Header record
            cur.execute("""
                SELECT * FROM quotations WHERE quotation_no = %s LIMIT 1;
            """, (quotation_no,))

            row = cur.fetchone()
            if not row:
                return None

            q_data = dict(row)

            # Format dates seamlessly to strings for frontend engine compliance
            for date_key in ["quotation_date", "validity_date"]:
                if date_key in q_data and q_data[date_key] and not isinstance(q_data[date_key], str):
                    q_data[date_key] = q_data[date_key].strftime("%Y-%m-%d")

            # Fetch Child Item Array rows
            cur.execute("""
                SELECT id, description, currency, price, unit, remark 
                FROM quotation_items 
                WHERE quotation_id = %s 
                ORDER BY sort_order ASC;
            """, (q_data["id"],))

            q_data["items"] = [dict(r) for r in cur.fetchall()]

            return q_data


# =========================================================
# MUTATION WRITING: UPDATE QUOTATION
# =========================================================
def update_quotation(quotation_no: str, data: Dict[str, Any], items: List[Dict[str, Any]]) -> None:
    """
    Updates quotation metadata master record and replaces line rows in a block.
    Fixed: removed duplicate fetchone() that caused NoneType crash.
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            try:
                # 1. Row Lock Verification check (single fetch only)
                cur.execute("SELECT id FROM quotations WHERE quotation_no = %s LIMIT 1;", (quotation_no,))
                header = cur.fetchone()
                if not header:
                    raise ValueError(f"Quotation '{quotation_no}' not found in database.")

                q_id = header[0] if isinstance(header, (tuple, list)) else header["id"]

                # 2. Mutating structural properties data
                cur.execute("""
                    UPDATE quotations SET
                        job_type = %s, customer_name = %s, attention = %s, tel = %s,
                        carrier = %s, pol = %s, pod = %s, quotation_date = %s,
                        validity_date = %s, payment_term = %s, commodity = %s,
                        subject = %s, terms_conditions = %s, updated_by = %s
                    WHERE id = %s;
                """, (
                    data.get("job_type"), data.get("customer_name"), data.get("attention"), data.get("tel"),
                    data.get("carrier"), data.get("pol"), data.get("pod"), data.get("quotation_date"),
                    data.get("validity_date"), data.get("payment_term"), data.get("commodity"),
                    data.get("subject"), data.get("terms_conditions"), data.get("updated_by", "system"), q_id
                ))

                # 3. Purging historical items lines rows to overwrite safely
                cur.execute("DELETE FROM quotation_items WHERE quotation_id = %s;", (q_id,))

                # 4. Injecting updated fresh lines array block
                for idx, item in enumerate(items):
                    cur.execute("""
                        INSERT INTO quotation_items (
                            quotation_id, description, currency, price, unit, remark, sort_order
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s);
                    """, (
                        q_id, item.get("description", ""), item.get("currency", "USD"),
                        float(item.get("price", 0.0)), item.get("unit", "SHPMT"), item.get("remark", ""), idx
                    ))

                conn.commit()
            except Exception as e:
                conn.rollback()
                raise RuntimeError(f"Failed executing update transaction: {str(e)}")


def duplicate_quotation(quotation_no: str) -> str:
    """
    Fetches an existing quotation layout pattern and duplicates it into a new transaction context sequence.
    """
    source_data = get_quotation_by_no(quotation_no)
    if not source_data:
        raise ValueError(f"Source quotation '{quotation_no}' not found.")

    source_data["quotation_date"] = datetime.now().strftime("%Y-%m-%d")
    source_data["validity_date"] = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")

    return create_quotation(source_data, source_data.get("items", []))