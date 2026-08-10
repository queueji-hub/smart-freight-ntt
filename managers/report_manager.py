from typing import Dict, Any, List, Optional
from database.connection import get_connection
from managers.tenant_context import get_current_tenant_id

def get_sales_performance_report(
    reporting_month: str,
    reporting_year: str,
    sales_person: Optional[str] = None,
    job_type_filter: Optional[str] = None, # 'EXPORT', 'IMPORT', 'ALL'
    mode_filter: Optional[str] = None, # 'SEA', 'AIR', 'ROAD', 'ALL'
    customer_id: Optional[str] = None,
    status: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Returns aggregated Sales Performance metrics for a given reporting month/year.
    Adheres strictly to the EXPORT=ETD / IMPORT=ETA rule inherently stored in reporting_month/year.
    """
    tenant_id = get_current_tenant_id()
    
    # Base query for shipments
    query = """
        SELECT 
            s.sales_person,
            COUNT(s.id) as total_jobs,
            SUM(CASE WHEN s.job_type LIKE '%%EXPORT%%' THEN 1 ELSE 0 END) as export_jobs,
            SUM(CASE WHEN s.job_type LIKE '%%IMPORT%%' THEN 1 ELSE 0 END) as import_jobs,
            SUM(CASE WHEN UPPER(s.mode) = 'SEA' THEN 1 ELSE 0 END) as sea_jobs,
            SUM(CASE WHEN UPPER(s.mode) = 'AIR' THEN 1 ELSE 0 END) as air_jobs,
            SUM(CASE WHEN UPPER(s.mode) = 'ROAD' THEN 1 ELSE 0 END) as cross_border_jobs,
            SUM(CASE WHEN s.status != 'Lost' THEN 1 ELSE 0 END) as won_jobs,
            SUM(CASE WHEN s.status = 'Lost' THEN 1 ELSE 0 END) as lost_jobs,
            
            -- Revenue (AR)
            SUM(COALESCE(ar_est.total, 0)) as estimated_revenue,
            SUM(COALESCE(ar_act.total, 0)) as actual_revenue,
            SUM(COALESCE(ar_act.total, 0) + COALESCE(ar_est.total, 0)) as sales_revenue, -- AR total
            
            -- Cost (AP)
            SUM(COALESCE(ap_est.total, 0)) as estimated_cost,
            SUM(COALESCE(ap_acc.total, 0) + COALESCE(ap_act.total, 0) + COALESCE(ap_pst.total, 0)) as actual_cost,
            
            -- Gross Profit
            SUM(COALESCE(ar_act.total, 0) - (COALESCE(ap_acc.total, 0) + COALESCE(ap_act.total, 0) + COALESCE(ap_pst.total, 0))) as actual_gp,
            
            -- AR/AP status
            SUM(COALESCE(ar_act.total, 0)) as outstanding_ar -- simplistic for now, assuming actual = outstanding until paid
        FROM shipments s
        
        -- Subqueries to bucket costs per shipment safely
        LEFT JOIN (SELECT shipment_id, SUM(amount_thb) as total FROM job_costs WHERE cost_type='AR' AND cost_status='ESTIMATED' GROUP BY shipment_id) ar_est ON s.id = ar_est.shipment_id
        LEFT JOIN (SELECT shipment_id, SUM(amount_thb) as total FROM job_costs WHERE cost_type='AR' AND cost_status='ACTUAL' GROUP BY shipment_id) ar_act ON s.id = ar_act.shipment_id
        
        LEFT JOIN (SELECT shipment_id, SUM(amount_thb) as total FROM job_costs WHERE cost_type='AP' AND cost_status='ESTIMATED' GROUP BY shipment_id) ap_est ON s.id = ap_est.shipment_id
        LEFT JOIN (SELECT shipment_id, SUM(amount_thb) as total FROM job_costs WHERE cost_type='AP' AND cost_status='ACCRUED' GROUP BY shipment_id) ap_acc ON s.id = ap_acc.shipment_id
        LEFT JOIN (SELECT shipment_id, SUM(amount_thb) as total FROM job_costs WHERE cost_type='AP' AND cost_status='ACTUAL' GROUP BY shipment_id) ap_act ON s.id = ap_act.shipment_id
        LEFT JOIN (SELECT shipment_id, SUM(amount_thb) as total FROM job_costs WHERE cost_type='AP' AND cost_status='POSTED' GROUP BY shipment_id) ap_pst ON s.id = ap_pst.shipment_id
        
        WHERE s.tenant_id = %s AND s.reporting_month = %s AND s.reporting_year = %s
    """
    
    params = [tenant_id, reporting_month, reporting_year]
    
    if sales_person:
        query += " AND s.sales_person = %s"
        params.append(sales_person)
    if job_type_filter and job_type_filter != 'ALL':
        query += " AND s.job_type LIKE %s"
        params.append(f"%{job_type_filter}%")
    if mode_filter and mode_filter != 'ALL':
        query += " AND UPPER(s.mode) = %s"
        params.append(mode_filter.upper())
    if customer_id:
        query += " AND s.customer_id = %s"
        params.append(customer_id)
    if status:
        query += " AND s.status = %s"
        params.append(status)
        
    query += " GROUP BY s.sales_person"
    
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, tuple(params))
            rows = cur.fetchall()
            
            results = []
            for row in rows:
                d = dict(row)
                
                # Calculations
                actual_rev = float(d['actual_revenue'] or 0)
                actual_cost = float(d['actual_cost'] or 0)
                actual_gp = float(d['actual_gp'] or 0)
                d['gross_margin_pct'] = round((actual_gp / actual_rev * 100), 2) if actual_rev > 0 else 0.0
                
                # Clean up None
                for k, v in d.items():
                    if v is None:
                        d[k] = 0
                        
                results.append(d)
            return results

def get_company_monthly_performance(
    reporting_month: str,
    reporting_year: str
) -> Dict[str, Any]:
    """
    Returns Executive Monthly Company Performance.
    """
    sales_perf = get_sales_performance_report(reporting_month, reporting_year)
    
    summary = {
        "operations": {
            "total_jobs": sum(s['total_jobs'] for s in sales_perf),
            "export_jobs": sum(s['export_jobs'] for s in sales_perf),
            "import_jobs": sum(s['import_jobs'] for s in sales_perf),
            "sea_jobs": sum(s['sea_jobs'] for s in sales_perf),
            "air_jobs": sum(s['air_jobs'] for s in sales_perf),
            "cross_border_jobs": sum(s['cross_border_jobs'] for s in sales_perf),
            "won_jobs": sum(s['won_jobs'] for s in sales_perf)
        },
        "revenue": {
            "estimated_revenue": sum(s['estimated_revenue'] for s in sales_perf),
            "actual_revenue": sum(s['actual_revenue'] for s in sales_perf),
            "outstanding_ar": sum(s['outstanding_ar'] for s in sales_perf)
        },
        "cost": {
            "estimated_cost": sum(s['estimated_cost'] for s in sales_perf),
            "actual_cost": sum(s['actual_cost'] for s in sales_perf)
        },
        "profit": {
            "actual_gp": sum(s['actual_gp'] for s in sales_perf)
        },
        "sales": sales_perf
    }
    
    rev = summary["revenue"]["actual_revenue"]
    gp = summary["profit"]["actual_gp"]
    summary["profit"]["gross_margin_pct"] = round((gp / rev * 100), 2) if rev > 0 else 0.0
    
    return summary

def get_salesperson_job_drilldown(
    reporting_month: str,
    reporting_year: str,
    sales_person: str
) -> List[Dict[str, Any]]:
    """
    Returns drill-down list of jobs for a salesperson in a given month.
    """
    tenant_id = get_current_tenant_id()
    query = """
        SELECT 
            s.job_no, s.customer_name, s.job_type, s.mode, s.etd, s.eta, s.status,
            COALESCE(ar_act.total, 0) as actual_revenue,
            (COALESCE(ap_acc.total, 0) + COALESCE(ap_act.total, 0) + COALESCE(ap_pst.total, 0)) as actual_cost
        FROM shipments s
        LEFT JOIN (SELECT shipment_id, SUM(amount_thb) as total FROM job_costs WHERE cost_type='AR' AND cost_status='ACTUAL' GROUP BY shipment_id) ar_act ON s.id = ar_act.shipment_id
        LEFT JOIN (SELECT shipment_id, SUM(amount_thb) as total FROM job_costs WHERE cost_type='AP' AND cost_status='ACCRUED' GROUP BY shipment_id) ap_acc ON s.id = ap_acc.shipment_id
        LEFT JOIN (SELECT shipment_id, SUM(amount_thb) as total FROM job_costs WHERE cost_type='AP' AND cost_status='ACTUAL' GROUP BY shipment_id) ap_act ON s.id = ap_act.shipment_id
        LEFT JOIN (SELECT shipment_id, SUM(amount_thb) as total FROM job_costs WHERE cost_type='AP' AND cost_status='POSTED' GROUP BY shipment_id) ap_pst ON s.id = ap_pst.shipment_id
        WHERE s.tenant_id = %s AND s.reporting_month = %s AND s.reporting_year = %s AND s.sales_person = %s
        ORDER BY s.job_no DESC
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, (tenant_id, reporting_month, reporting_year, sales_person))
            rows = cur.fetchall()
            
            results = []
            for row in rows:
                d = dict(row)
                rev = float(d['actual_revenue'] or 0)
                cost = float(d['actual_cost'] or 0)
                gp = rev - cost
                d['gross_profit'] = gp
                d['gross_margin_pct'] = round((gp / rev * 100), 2) if rev > 0 else 0.0
                results.append(d)
            return results
