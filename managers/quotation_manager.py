from managers.tenant_context import get_current_tenant_id
from managers.document_numbering_service import generate_document_number, normalize_doc_no
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

    quotation_no = data.get("quotation_no") or generate_document_number("QT", q_date_obj)

    with get_connection() as conn:
        with conn.cursor() as cur:
            try:
                tenant_id = get_current_tenant_id()
                # 1. Master Header Record Insertion
                cur.execute("""
                    INSERT INTO quotations (
                        quotation_no, job_type, customer_name, attention, tel,
                        carrier, pol, pod, quotation_date, validity_date,
                        payment_term, commodity, subject, terms_conditions,
                        status, created_at, tenant_id,
                        customer_address, customer_email, salesperson,
                        shipper, consignee, service_type, origin, destination,
                        incoterm, freight_term, hs_code, quantity, package_type,
                        weight_kg, volume_cbm, container_type, container_quantity, is_dg
                    )
                    VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP, %s,
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                    );
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
                    data.get("status") or "Draft",
                    tenant_id,
                    data.get("customer_address", ""),
                    data.get("customer_email", ""),
                    data.get("salesperson", ""),
                    data.get("shipper", ""),
                    data.get("consignee", ""),
                    data.get("service_type", ""),
                    data.get("origin", ""),
                    data.get("destination", ""),
                    data.get("incoterm", ""),
                    data.get("freight_term", ""),
                    data.get("hs_code", ""),
                    float(data.get("quantity") or 0.0),
                    data.get("package_type", ""),
                    float(data.get("weight_kg") or 0.0),
                    float(data.get("volume_cbm") or 0.0),
                    data.get("container_type", ""),
                    int(data.get("container_quantity") or 0),
                    bool(data.get("is_dg") or False)
                ))

                cur.execute("SELECT id FROM quotations WHERE quotation_no = %s AND tenant_id = %s LIMIT 1;", (quotation_no, tenant_id))
                result = cur.fetchone()
                quotation_id = result[0] if isinstance(result, (tuple, list)) else result["id"]

                # 2. Child Line Items Segment Iteration
                for idx, item in enumerate(items):
                    qty = float(item.get("quantity") or 1.0)
                    unit_rate = float(item.get("unit_rate") or item.get("price") or 0.0)
                    amount = qty * unit_rate
                    
                    cur.execute("""
                        INSERT INTO quotation_items (
                            quotation_id, description, currency, price, unit, remark, sort_order,
                            basis, quantity, unit_rate, amount
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
                    """, (
                        quotation_id,
                        item.get("description", ""),
                        item.get("currency", "USD"),
                        amount, # legacy price = amount
                        item.get("unit", "SHPMT"),
                        item.get("remark", ""),
                        idx,
                        item.get("basis", ""),
                        qty,
                        unit_rate,
                        amount
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
    Tenant-isolated.
    """
    tenant_id = get_current_tenant_id()
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT 
                    quotation_no, job_type, customer_name, subject,
                    quotation_date, validity_date, status, pol, pod, salesperson,
                    service_type, incoterm
                FROM quotations 
                WHERE tenant_id = %s
                ORDER BY id DESC;
            """, (tenant_id,))
            rows = cur.fetchall()
            return [dict(r) for r in rows]


def get_quotation_by_no(quotation_no: str) -> Optional[Dict[str, Any]]:
    """
    Fetches aggregate data model mapping Header joined with Child Items rows.
    Tenant-isolated.
    """
    if not quotation_no:
        return None

    tenant_id = get_current_tenant_id()
    with get_connection() as conn:
        with conn.cursor() as cur:
            # Fetch Header record (tenant-isolated)
            cur.execute("""
                SELECT * FROM quotations WHERE quotation_no = %s AND tenant_id = %s LIMIT 1;
            """, (quotation_no, tenant_id))

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
                SELECT id, description, currency, price, unit, remark,
                       basis, quantity, unit_rate, amount 
                FROM quotation_items 
                WHERE quotation_id = %s 
                ORDER BY sort_order ASC;
            """, (q_data["id"],))

            q_data["items"] = [dict(r) for r in cur.fetchall()]

            return q_data


def get_quotation(quotation_no: str) -> Optional[Dict[str, Any]]:
    """Alias for get_quotation_by_no."""
    return get_quotation_by_no(quotation_no)



# =========================================================
# MUTATION WRITING: UPDATE QUOTATION
# =========================================================
def update_quotation(quotation_no: str, data: Dict[str, Any], items: List[Dict[str, Any]]) -> None:
    """
    Updates quotation metadata master record and replaces line rows in a block.
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            try:
                tenant_id = get_current_tenant_id()
                # 1. Row Lock Verification check (single fetch only, tenant-isolated)
                cur.execute("SELECT id FROM quotations WHERE quotation_no = %s AND tenant_id = %s LIMIT 1;", (quotation_no, tenant_id))
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
                        subject = %s, terms_conditions = %s,
                        customer_address = %s, customer_email = %s, salesperson = %s,
                        shipper = %s, consignee = %s, service_type = %s, origin = %s, destination = %s,
                        incoterm = %s, freight_term = %s, hs_code = %s, quantity = %s, package_type = %s,
                        weight_kg = %s, volume_cbm = %s, container_type = %s, container_quantity = %s, is_dg = %s,
                        status = COALESCE(%s, status)
                    WHERE id = %s AND tenant_id = %s;
                """, (
                    data.get("job_type"), data.get("customer_name"), data.get("attention"), data.get("tel"),
                    data.get("carrier"), data.get("pol"), data.get("pod"), data.get("quotation_date"),
                    data.get("validity_date"), data.get("payment_term"), data.get("commodity"),
                    data.get("subject"), data.get("terms_conditions"),
                    data.get("customer_address", ""), data.get("customer_email", ""), data.get("salesperson", ""),
                    data.get("shipper", ""), data.get("consignee", ""), data.get("service_type", ""), 
                    data.get("origin", ""), data.get("destination", ""), data.get("incoterm", ""), 
                    data.get("freight_term", ""), data.get("hs_code", ""), 
                    float(data.get("quantity") or 0.0), data.get("package_type", ""), 
                    float(data.get("weight_kg") or 0.0), float(data.get("volume_cbm") or 0.0), 
                    data.get("container_type", ""), int(data.get("container_quantity") or 0), 
                    bool(data.get("is_dg") or False),
                    data.get("status"),
                    q_id, tenant_id
                ))

                # 3. Purging historical items lines rows to overwrite safely
                cur.execute("DELETE FROM quotation_items WHERE quotation_id = %s;", (q_id,))

                # 4. Injecting updated fresh lines array block
                for idx, item in enumerate(items):
                    qty = float(item.get("quantity") or 1.0)
                    unit_rate = float(item.get("unit_rate") or item.get("price") or 0.0)
                    amount = qty * unit_rate
                    
                    cur.execute("""
                        INSERT INTO quotation_items (
                            quotation_id, description, currency, price, unit, remark, sort_order,
                            basis, quantity, unit_rate, amount
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
                    """, (
                        q_id,
                        item.get("description", ""),
                        item.get("currency", "USD"),
                        amount,
                        item.get("unit", "SHPMT"),
                        item.get("remark", ""),
                        idx,
                        item.get("basis", ""),
                        qty,
                        unit_rate,
                        amount
                    ))
                conn.commit()
            except Exception as e:
                conn.rollback()
                raise RuntimeError(f"Failed executing update transaction: {str(e)}")


def set_quotation_status(quotation_no: str, status: str) -> None:
    """Updates the lifecycle status of a quotation (e.g. Draft, Sent, Approved, Rejected, Cancelled)."""
    tenant_id = get_current_tenant_id()
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE quotations 
                SET status = %s 
                WHERE quotation_no = %s AND tenant_id = %s;
            """, (status, quotation_no, tenant_id))
            conn.commit()


def delete_quotation(quotation_no: str) -> bool:
    """
    Deletes quotation items and master quotation record atomically.
    Tenant-isolated.
    """
    if not quotation_no:
        return False
    tenant_id = get_current_tenant_id()
    with get_connection() as conn:
        with conn.cursor() as cur:
            try:
                cur.execute("SELECT id FROM quotations WHERE quotation_no = %s AND tenant_id = %s LIMIT 1;", (quotation_no, tenant_id))
                row = cur.fetchone()
                if not row:
                    return False
                q_id = row[0] if isinstance(row, (tuple, list)) else row["id"]

                cur.execute("DELETE FROM quotation_items WHERE quotation_id = %s;", (q_id,))
                cur.execute("DELETE FROM quotations WHERE id = %s AND tenant_id = %s;", (q_id, tenant_id))
                conn.commit()
                return True
            except Exception as e:
                conn.rollback()
                raise RuntimeError(f"Failed to delete quotation {quotation_no}: {str(e)}")


def duplicate_quotation(quotation_no: str) -> str:
    """
    Fetches an existing quotation layout pattern and duplicates it into a new transaction context sequence.
    """
    source_data = get_quotation_by_no(quotation_no)
    if not source_data:
        raise ValueError(f"Source quotation '{quotation_no}' not found.")

    source_data["quotation_date"] = datetime.now().strftime("%Y-%m-%d")
    source_data["validity_date"] = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
    source_data["status"] = "Draft"
    source_data.pop("quotation_no", None)

    return create_quotation(source_data, source_data.get("items", []))

def create_quotation_revision(quotation_no: str) -> str:
    """
    Creates a new revision of the given quotation.
    Marks the source quotation as SUPERSEDED (read-only/immutable).
    Generates a new revision number by appending -R1, -R2, etc.
    """
    source_data = get_quotation_by_no(quotation_no)
    if not source_data:
        raise ValueError(f"Source quotation '{quotation_no}' not found.")

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE quotations SET status = 'SUPERSEDED'
                WHERE quotation_no = %s;
            """, (quotation_no,))
            conn.commit()

    import re
    match = re.search(r'-R(\d+)$', quotation_no)
    if match:
        rev = int(match.group(1)) + 1
        base = quotation_no[:match.start()]
        new_qno = f"{base}-R{rev}"
    else:
        new_qno = f"{quotation_no}-R1"

    source_data["quotation_no"] = new_qno
    source_data["status"] = "ACTIVE"
    return create_quotation(source_data, source_data.get("items", []))