from typing import List, Dict, Any, Optional
from database.connection import get_connection
from managers.tenant_context import get_current_tenant_id
from core.audit import log_action

def get_ap_vouchers() -> List[Dict[str, Any]]:
    tenant_id = get_current_tenant_id()
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT ap.*, v.legal_name as vendor_name 
                FROM ap_vouchers ap
                JOIN vendors v ON ap.vendor_id = v.id
                WHERE ap.tenant_id = %s 
                ORDER BY ap.created_at DESC
            """, (tenant_id,))
            rows = cur.fetchall()
            return [dict(r) for r in rows] if rows else []

def get_ap_voucher(voucher_id: int) -> Optional[Dict[str, Any]]:
    tenant_id = get_current_tenant_id()
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT ap.*, v.legal_name as vendor_name 
                FROM ap_vouchers ap
                JOIN vendors v ON ap.vendor_id = v.id
                WHERE ap.id = %s AND ap.tenant_id = %s
            """, (voucher_id, tenant_id))
            row = cur.fetchone()
            return dict(row) if row else None

def create_ap_voucher(data: Dict[str, Any], user: Dict[str, Any]) -> int:
    tenant_id = get_current_tenant_id()
    with get_connection() as conn:
        try:
            with conn.cursor() as cur:
                # Basic validation
                cur.execute("SELECT id FROM vendors WHERE id=%s AND tenant_id=%s", (data.get('vendor_id'), tenant_id))
                if not cur.fetchone():
                    raise ValueError("Vendor not found or unauthorized")
                
                cur.execute("""
                    INSERT INTO ap_vouchers (
                        tenant_id, vendor_id, job_no, invoice_no, invoice_date, due_date,
                        currency, exchange_rate, subtotal, tax, total, created_by
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id
                """, (
                    tenant_id,
                    data.get('vendor_id'),
                    data.get('job_no'),
                    data.get('invoice_no'),
                    data.get('invoice_date'),
                    data.get('due_date'),
                    data.get('currency', 'THB'),
                    data.get('exchange_rate', 1.0),
                    data.get('subtotal', 0.0),
                    data.get('tax', 0.0),
                    data.get('total', 0.0),
                    user["username"] if user else 'system'
                ))
                row = cur.fetchone()
                try:
                    voucher_id = row["id"]
                except Exception:
                    voucher_id = row[0]
                conn.commit()
                if user:
                    log_action(user["id"], tenant_id, "ap_voucher", str(voucher_id), "CREATED")
                return voucher_id
        except Exception as e:
            conn.rollback()
            raise RuntimeError(f"Failed to create AP voucher: {str(e)}")

def update_ap_voucher_status(voucher_id: int, new_status: str, user: Dict[str, Any]):
    tenant_id = get_current_tenant_id()
    with get_connection() as conn:
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE ap_vouchers SET status=%s, updated_at=CURRENT_TIMESTAMP
                    WHERE id=%s AND tenant_id=%s
                """, (new_status, voucher_id, tenant_id))
                
                if cur.rowcount == 0:
                    raise ValueError("AP voucher not found or unauthorized")
                conn.commit()
                if user:
                    log_action(user["id"], tenant_id, "ap_voucher", str(voucher_id), f"STATUS_{new_status}")
        except Exception as e:
            conn.rollback()
            raise RuntimeError(f"Failed to update AP voucher status: {str(e)}")
