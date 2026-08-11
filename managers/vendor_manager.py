from typing import List, Dict, Any, Optional
from database.connection import get_connection
from managers.tenant_context import get_current_tenant_id
from core.audit import log_action

def get_vendors() -> List[Dict[str, Any]]:
    tenant_id = get_current_tenant_id()
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT * FROM vendors 
                WHERE tenant_id = %s 
                ORDER BY legal_name ASC
            """, (tenant_id,))
            rows = cur.fetchall()
            return [dict(r) for r in rows] if rows else []

def get_vendor(vendor_id: int) -> Optional[Dict[str, Any]]:
    tenant_id = get_current_tenant_id()
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT * FROM vendors 
                WHERE id = %s AND tenant_id = %s
            """, (vendor_id, tenant_id))
            row = cur.fetchone()
            return dict(row) if row else None

def create_vendor(data: Dict[str, Any], user: Dict[str, Any]) -> int:
    tenant_id = get_current_tenant_id()
    with get_connection() as conn:
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO vendors (
                        tenant_id, vendor_code, legal_name, tax_id, country, currency, created_by
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id
                """, (
                    tenant_id, 
                    data.get('vendor_code'),
                    data.get('legal_name'),
                    data.get('tax_id'),
                    data.get('country'),
                    data.get('currency', 'THB'),
                    user["username"] if user else 'system'
                ))
                row = cur.fetchone()
                try:
                    vendor_id = row["id"]
                except Exception:
                    vendor_id = row[0]
                conn.commit()
                if user:
                    log_action(user["id"], tenant_id, "vendor", str(vendor_id), "CREATED")
                return vendor_id
        except Exception as e:
            conn.rollback()
            raise RuntimeError(f"Failed to create vendor: {str(e)}")

def update_vendor(vendor_id: int, data: Dict[str, Any], user: Dict[str, Any]):
    tenant_id = get_current_tenant_id()
    with get_connection() as conn:
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE vendors SET
                        legal_name = %s,
                        tax_id = %s,
                        country = %s,
                        currency = %s,
                        status = %s,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s AND tenant_id = %s
                """, (
                    data.get('legal_name'),
                    data.get('tax_id'),
                    data.get('country'),
                    data.get('currency'),
                    data.get('status', 'Active'),
                    vendor_id,
                    tenant_id
                ))
                if cur.rowcount == 0:
                    raise ValueError("Vendor not found or unauthorized")
                conn.commit()
                if user:
                    log_action(user["id"], tenant_id, "vendor", str(vendor_id), "UPDATED")
        except Exception as e:
            conn.rollback()
            raise RuntimeError(f"Failed to update vendor: {str(e)}")
