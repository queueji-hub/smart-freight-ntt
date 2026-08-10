from typing import Dict, Any, List, Optional
from database.connection import get_connection
from managers.tenant_context import get_current_tenant_id
from managers.profit_manager import get_profit_summary

def create_commission_draft(job_no: str, sales_person: str, basis: str = 'Gross Profit', rate: float = 10.0) -> int:
    tenant_id = get_current_tenant_id()
    
    # Calculate amount based on basis
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM shipments WHERE job_no=%s AND tenant_id=%s", (job_no, tenant_id))
            row = cur.fetchone()
            if not row:
                raise ValueError("Shipment not found")
            shipment_id = row['id']
            
    summary = get_profit_summary(shipment_id)
    
    base_amount = 0.0
    if basis == 'Gross Profit':
        base_amount = summary['actual_net_profit']
    elif basis == 'Revenue':
        base_amount = summary['ar_actual']
        
    commission_amount = (base_amount * rate) / 100.0 if base_amount > 0 else 0.0
    
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO commissions (
                    tenant_id, job_no, sales_person, basis, rate, commission_amount, status
                ) VALUES (%s, %s, %s, %s, %s, %s, 'DRAFT')
                RETURNING id
            """, (tenant_id, job_no, sales_person, basis, rate, commission_amount))
            row = cur.fetchone()
            conn.commit()
            return row['id']

def update_commission_status(commission_id: int, status: str, approved_by: str = None) -> bool:
    tenant_id = get_current_tenant_id()
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE commissions 
                SET status=%s, approved_by=%s, calculated_at=CURRENT_TIMESTAMP 
                WHERE id=%s AND tenant_id=%s
            """, (status, approved_by, commission_id, tenant_id))
            conn.commit()
            return cur.rowcount > 0

def get_sales_performance(reporting_month: str) -> List[Dict[str, Any]]:
    """
    Returns Sales Performance aggregated by salesperson based on EXPORT (ETD) / IMPORT (ETA) reporting month rule.
    """
    tenant_id = get_current_tenant_id()
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT 
                    sales_person,
                    COUNT(id) as total_jobs,
                    SUM(CASE WHEN UPPER(job_type) LIKE '%%EXPORT%%' THEN 1 ELSE 0 END) as export_jobs,
                    SUM(CASE WHEN UPPER(job_type) LIKE '%%IMPORT%%' THEN 1 ELSE 0 END) as import_jobs
                FROM shipments
                WHERE reporting_month = %s AND tenant_id = %s
                GROUP BY sales_person
            """, (reporting_month, tenant_id))
            rows = cur.fetchall()
            return [dict(r) for r in rows]
