from typing import Dict, Any, List, Optional
from database.connection import get_connection
from managers.tenant_context import get_current_tenant_id

def get_month_end_summary(reporting_month: str, reporting_year: Optional[str] = None) -> Dict[str, Any]:
    tenant_id = get_current_tenant_id()
    
    # Handle YYYY-MM format
    if "-" in reporting_month:
        parts = reporting_month.split("-")
        reporting_year = parts[0]
        reporting_month = parts[1]
        
    with get_connection() as conn:
        with conn.cursor() as cur:
            # 1. Job Statistics
            cur.execute("""
                SELECT 
                    COUNT(id) as total_jobs,
                    SUM(CASE WHEN UPPER(job_type) LIKE '%%EXPORT%%' THEN 1 ELSE 0 END) as export_jobs,
                    SUM(CASE WHEN UPPER(job_type) LIKE '%%IMPORT%%' THEN 1 ELSE 0 END) as import_jobs,
                    SUM(CASE WHEN UPPER(mode) = 'SEA' THEN 1 ELSE 0 END) as sea_jobs,
                    SUM(CASE WHEN UPPER(mode) = 'AIR' THEN 1 ELSE 0 END) as air_jobs,
                    SUM(CASE WHEN UPPER(mode) = 'ROAD' THEN 1 ELSE 0 END) as road_jobs,
                    SUM(CASE WHEN financial_status = 'Open' THEN 1 ELSE 0 END) as open_jobs,
                    SUM(CASE WHEN financial_status = 'Closed' THEN 1 ELSE 0 END) as closed_jobs
                FROM shipments
                WHERE reporting_month = %s AND reporting_year = %s AND tenant_id = %s
            """, (reporting_month, reporting_year, tenant_id))
            job_stats = dict(cur.fetchone() or {})
            
            # 2. Unbilled / Uncosted Tracking
            cur.execute("""
                SELECT 
                    job_no
                FROM shipments s
                WHERE reporting_month = %s AND reporting_year = %s AND tenant_id = %s
                AND NOT EXISTS (SELECT 1 FROM job_costs jc WHERE jc.shipment_id = s.id AND jc.cost_type = 'AR')
            """, (reporting_month, reporting_year, tenant_id))
            unbilled = [r['job_no'] for r in cur.fetchall()]
            
            cur.execute("""
                SELECT 
                    job_no
                FROM shipments s
                WHERE reporting_month = %s AND reporting_year = %s AND tenant_id = %s
                AND NOT EXISTS (SELECT 1 FROM job_costs jc WHERE jc.shipment_id = s.id AND jc.cost_type = 'AP')
            """, (reporting_month, reporting_year, tenant_id))
            uncosted = [r['job_no'] for r in cur.fetchall()]
            
            # 3. Aggregated Financials
            # Here we just fetch estimated vs actual for the whole month for executive view
            cur.execute("""
                SELECT 
                    jc.cost_type, jc.cost_status, SUM(jc.amount_thb) as total
                FROM job_costs jc
                JOIN shipments s ON jc.shipment_id = s.id
                WHERE s.reporting_month = %s AND s.reporting_year = %s AND s.tenant_id = %s
                GROUP BY jc.cost_type, jc.cost_status
            """, (reporting_month, reporting_year, tenant_id))
            
            financials = {'ar_actual': 0.0, 'ap_actual': 0.0, 'ap_posted': 0.0}
            for row in cur.fetchall():
                c_type = row['cost_type']
                c_status = row['cost_status']
                total = float(row['total'] or 0)
                
                if c_type == 'AR' and c_status != 'ESTIMATED':
                    financials['ar_actual'] += total
                elif c_type == 'AP' and c_status == 'ACTUAL':
                    financials['ap_actual'] += total
                elif c_type == 'AP' and c_status == 'POSTED':
                    financials['ap_posted'] += total
                    
            return {
                "reporting_month": reporting_month,
                "reporting_year": reporting_year,
                "job_stats": job_stats,
                "unbilled_jobs": unbilled,
                "uncosted_jobs": uncosted,
                "financials": financials
            }
