from managers.tenant_context import get_current_tenant_id
from database.connection import get_connection


# =========================
# KPI CORE
# =========================

def get_kpi_summary():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    COUNT(*) AS total_shipments,

                    SUM(CASE WHEN status='Proceed' THEN 1 ELSE 0 END) AS active_jobs,
                    SUM(CASE WHEN status='Finished' THEN 1 ELSE 0 END) AS finished_jobs,
                    SUM(CASE WHEN status='Closed' THEN 1 ELSE 0 END) AS closed_jobs,

                    SUM(CASE WHEN DATE(etd) = CURRENT_DATE THEN 1 ELSE 0 END) AS etd_today,
                    SUM(CASE WHEN DATE(eta) = CURRENT_DATE THEN 1 ELSE 0 END) AS eta_today

                FROM shipments
            """)
            return cur.fetchone()


# =========================
# MONTHLY FLOW
# =========================

def get_monthly_flow():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    COUNT(*) FILTER (WHERE DATE_TRUNC('month', etd) = DATE_TRUNC('month', CURRENT_DATE)) AS etd_this_month,
                    COUNT(*) FILTER (WHERE DATE_TRUNC('month', eta) = DATE_TRUNC('month', CURRENT_DATE)) AS eta_this_month
                FROM shipments
            """)
            return cur.fetchone()


# =========================
# OPERATIONAL CONTROL TOWER STATS (PHASE B)
# =========================

def get_operational_control_tower_stats() -> dict:
    """Aggregates high-level stats for Quotations, Bookings, Jobs, Containers, B/L, Schedule, Exceptions"""
    from managers.tenant_context import get_current_tenant_id
    tenant_id = get_current_tenant_id()
    
    stats = {
        "quotation": {"total": 0, "draft": 0, "active": 0, "converted": 0, "expired": 0},
        "booking": {"total": 0, "draft": 0, "submitted": 0, "confirmed": 0, "converted": 0, "revised": 0, "unconverted_confirmed": 0},
        "job": {"total": 0, "proceed": 0, "in_transit": 0, "arrived": 0, "finished": 0, "closed": 0, "cancelled": 0},
        "container": {"total_containers": 0, "jobs_with_containers": 0, "jobs_missing_containers": 0},
        "bl": {"draft": 0, "issued": 0, "cancelled": 0, "total": 0},
        "schedule": {"etd_today": 0, "etd_7d": 0, "etd_14d": 0, "eta_today": 0, "eta_7d": 0, "eta_14d": 0, "overdue_eta": 0},
        "exceptions": {"unconverted_confirmed_booking": 0, "job_without_container": 0, "job_without_bl": 0, "overdue_eta": 0, "missing_etd": 0, "missing_eta": 0, "missing_vessel": 0}
    }

    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                # 1. Quotation Stats
                cur.execute("""
                    SELECT 
                        COUNT(*) as total,
                        SUM(CASE WHEN LOWER(status) = 'draft' THEN 1 ELSE 0 END) as draft,
                        SUM(CASE WHEN LOWER(status) = 'active' THEN 1 ELSE 0 END) as active,
                        SUM(CASE WHEN LOWER(status) = 'converted' THEN 1 ELSE 0 END) as converted,
                        SUM(CASE WHEN LOWER(status) = 'expired' THEN 1 ELSE 0 END) as expired
                    FROM quotations
                    WHERE tenant_id = %s
                """, (tenant_id,))
                row = cur.fetchone()
                if row:
                    q_dict = dict(row) if hasattr(row, "keys") else dict(zip(["total", "draft", "active", "converted", "expired"], row))
                    stats["quotation"] = {k: int(v or 0) for k, v in q_dict.items()}

                # 2. Booking Stats
                cur.execute("""
                    SELECT 
                        COUNT(*) as total,
                        SUM(CASE WHEN LOWER(status) = 'draft' THEN 1 ELSE 0 END) as draft,
                        SUM(CASE WHEN LOWER(status) = 'submitted' THEN 1 ELSE 0 END) as submitted,
                        SUM(CASE WHEN LOWER(status) = 'confirmed' THEN 1 ELSE 0 END) as confirmed,
                        SUM(CASE WHEN LOWER(status) = 'converted_to_job' OR LOWER(status) = 'converted to job' THEN 1 ELSE 0 END) as converted,
                        SUM(CASE WHEN revision_no > 0 THEN 1 ELSE 0 END) as revised,
                        SUM(CASE WHEN LOWER(status) = 'confirmed' AND (job_no IS NULL OR job_no = '') THEN 1 ELSE 0 END) as unconverted_confirmed
                    FROM bookings
                    WHERE tenant_id = %s
                """, (tenant_id,))
                row = cur.fetchone()
                if row:
                    b_cols = ["total", "draft", "submitted", "confirmed", "converted", "revised", "unconverted_confirmed"]
                    b_dict = dict(row) if hasattr(row, "keys") else dict(zip(b_cols, row))
                    stats["booking"] = {k: int(v or 0) for k, v in b_dict.items()}
                    stats["booking"]["unconverted_confirmed"] = int(b_dict.get("unconverted_confirmed") or 0)

                # 3. Job Stats
                cur.execute("""
                    SELECT 
                        COUNT(*) as total,
                        SUM(CASE WHEN LOWER(status) = 'proceed' THEN 1 ELSE 0 END) as proceed,
                        SUM(CASE WHEN LOWER(status) = 'in_transit' OR LOWER(status) = 'in transit' THEN 1 ELSE 0 END) as in_transit,
                        SUM(CASE WHEN LOWER(status) = 'arrived' THEN 1 ELSE 0 END) as arrived,
                        SUM(CASE WHEN LOWER(status) = 'finished' THEN 1 ELSE 0 END) as finished,
                        SUM(CASE WHEN LOWER(status) = 'closed' THEN 1 ELSE 0 END) as closed,
                        SUM(CASE WHEN LOWER(status) = 'cancelled' OR LOWER(status) = 'canceled' THEN 1 ELSE 0 END) as cancelled
                    FROM shipments
                    WHERE tenant_id = %s
                """, (tenant_id,))
                row = cur.fetchone()
                if row:
                    j_cols = ["total", "proceed", "in_transit", "arrived", "finished", "closed", "cancelled"]
                    j_dict = dict(row) if hasattr(row, "keys") else dict(zip(j_cols, row))
                    stats["job"] = {k: int(v or 0) for k, v in j_dict.items()}

                # 4. Container Stats
                cur.execute("SELECT COUNT(*) FROM containers WHERE tenant_id = %s", (tenant_id,))
                total_ctrs = cur.fetchone()
                stats["container"]["total_containers"] = int(total_ctrs[0] if total_ctrs else 0)

                cur.execute("SELECT COUNT(DISTINCT job_no) FROM containers WHERE tenant_id = %s AND job_no IS NOT NULL AND job_no != ''", (tenant_id,))
                jobs_w_ctrs = cur.fetchone()
                stats["container"]["jobs_with_containers"] = int(jobs_w_ctrs[0] if jobs_w_ctrs else 0)
                stats["container"]["jobs_missing_containers"] = max(0, stats["job"]["total"] - stats["container"]["jobs_with_containers"])

                # 5. B/L Stats
                cur.execute("""
                    SELECT 
                        COUNT(*) as total,
                        SUM(CASE WHEN LOWER(status) = 'draft' THEN 1 ELSE 0 END) as draft,
                        SUM(CASE WHEN LOWER(status) = 'issued' THEN 1 ELSE 0 END) as issued,
                        SUM(CASE WHEN LOWER(status) = 'cancelled' THEN 1 ELSE 0 END) as cancelled
                    FROM bills_of_lading
                    WHERE tenant_id = %s
                """, (tenant_id,))
                row = cur.fetchone()
                if row:
                    bl_cols = ["total", "draft", "issued", "cancelled"]
                    bl_dict = dict(row) if hasattr(row, "keys") else dict(zip(bl_cols, row))
                    stats["bl"] = {k: int(v or 0) for k, v in bl_dict.items()}

                # 6. Schedule & Exception Stats
                cur.execute("""
                    SELECT
                        SUM(CASE WHEN etd = CURRENT_DATE THEN 1 ELSE 0 END) as etd_today,
                        SUM(CASE WHEN etd >= CURRENT_DATE AND etd <= CURRENT_DATE + INTERVAL '7 days' THEN 1 ELSE 0 END) as etd_7d,
                        SUM(CASE WHEN etd >= CURRENT_DATE AND etd <= CURRENT_DATE + INTERVAL '14 days' THEN 1 ELSE 0 END) as etd_14d,
                        SUM(CASE WHEN eta = CURRENT_DATE THEN 1 ELSE 0 END) as eta_today,
                        SUM(CASE WHEN eta >= CURRENT_DATE AND eta <= CURRENT_DATE + INTERVAL '7 days' THEN 1 ELSE 0 END) as eta_7d,
                        SUM(CASE WHEN eta >= CURRENT_DATE AND eta <= CURRENT_DATE + INTERVAL '14 days' THEN 1 ELSE 0 END) as eta_14d,
                        SUM(CASE WHEN eta < CURRENT_DATE AND LOWER(status) NOT IN ('finished', 'closed', 'cancelled') THEN 1 ELSE 0 END) as overdue_eta,
                        SUM(CASE WHEN (etd IS NULL OR etd = '') AND LOWER(status) NOT IN ('finished', 'closed', 'cancelled') THEN 1 ELSE 0 END) as missing_etd,
                        SUM(CASE WHEN (eta IS NULL OR eta = '') AND LOWER(status) NOT IN ('finished', 'closed', 'cancelled') THEN 1 ELSE 0 END) as missing_eta,
                        SUM(CASE WHEN (vessel IS NULL OR vessel = '') AND LOWER(status) NOT IN ('finished', 'closed', 'cancelled') THEN 1 ELSE 0 END) as missing_vessel
                    FROM shipments
                    WHERE tenant_id = %s
                """, (tenant_id,))
                row = cur.fetchone()
                if row:
                    s_cols = ["etd_today", "etd_7d", "etd_14d", "eta_today", "eta_7d", "eta_14d", "overdue_eta", "missing_etd", "missing_eta", "missing_vessel"]
                    s_dict = dict(row) if hasattr(row, "keys") else dict(zip(s_cols, row))
                    
                    stats["schedule"] = {
                        "etd_today": int(s_dict.get("etd_today") or 0),
                        "etd_7d": int(s_dict.get("etd_7d") or 0),
                        "etd_14d": int(s_dict.get("etd_14d") or 0),
                        "eta_today": int(s_dict.get("eta_today") or 0),
                        "eta_7d": int(s_dict.get("eta_7d") or 0),
                        "eta_14d": int(s_dict.get("eta_14d") or 0),
                        "overdue_eta": int(s_dict.get("overdue_eta") or 0)
                    }
                    
                    # 7. Exceptions Compilation
                    cur.execute("SELECT COUNT(DISTINCT job_no) FROM bills_of_lading WHERE tenant_id = %s AND job_no IS NOT NULL AND job_no != ''", (tenant_id,))
                    jobs_w_bl = cur.fetchone()
                    count_bl = int(jobs_w_bl[0] if jobs_w_bl else 0)

                    stats["exceptions"] = {
                        "unconverted_confirmed_booking": stats["booking"]["unconverted_confirmed"],
                        "job_without_container": stats["container"]["jobs_missing_containers"],
                        "job_without_bl": max(0, stats["job"]["total"] - count_bl),
                        "overdue_eta": int(s_dict.get("overdue_eta") or 0),
                        "missing_etd": int(s_dict.get("missing_etd") or 0),
                        "missing_eta": int(s_dict.get("missing_eta") or 0),
                        "missing_vessel": int(s_dict.get("missing_vessel") or 0)
                    }

    except Exception as e:
        print(f"[WARN] get_operational_control_tower_stats failed: {str(e)}")

    return stats


# =========================
# FINANCE KPI
# =========================

def get_finance_kpi():
    from managers.tenant_context import get_current_tenant_id
    tenant_id = get_current_tenant_id()
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    COALESCE(SUM(total_amount),0) AS revenue,
                    COALESCE(SUM(outstanding),0) AS ar
                FROM invoices
                WHERE tenant_id = %s
            """, (tenant_id,))
            return cur.fetchone()


# =========================
# TOP ROUTES
# =========================

def get_top_routes():
    from managers.tenant_context import get_current_tenant_id
    tenant_id = get_current_tenant_id()
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    pol,
                    pod,
                    COUNT(*) AS volume
                FROM shipments
                WHERE tenant_id = %s
                GROUP BY pol, pod
                ORDER BY volume DESC
                LIMIT 10
            """, (tenant_id,))
            return cur.fetchall()


# =========================
# 360° CROSS-FUNCTIONAL JOB INSPECTOR
# =========================

def get_360_job_details(query: str) -> dict:
    """
    360-degree inspection engine linking Sales (Quotation), Ops (Booking & Shipment),
    Accounting (Invoices & AR/AP Costs), and Security Audit Trail.
    """
    from managers.tenant_context import get_current_tenant_id
    from managers.shipment_manager import get_job_financial_summary
    
    clean_q = (query or "").strip()
    if not clean_q:
        return {}

    tenant_id = get_current_tenant_id()
    pattern = f"%{clean_q.lower()}%"
    result = {
        "shipment": None,
        "booking": None,
        "quotation": None,
        "invoices": [],
        "costs": [],
        "profit_summary": {"total_ar": 0.0, "total_ap": 0.0, "net_profit": 0.0, "profit_margin": 0.0},
        "audit_trail": []
    }

    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                # 1. Search Shipment
                cur.execute("""
                    SELECT * FROM shipments
                    WHERE tenant_id = %s AND (LOWER(job_no) LIKE %s OR LOWER(booking_no) LIKE %s OR LOWER(bl_no) LIKE %s OR LOWER(customer_name) LIKE %s)
                    ORDER BY id DESC LIMIT 1
                """, (tenant_id, pattern, pattern, pattern, pattern))
                ship_row = cur.fetchone()

                if ship_row:
                    ship = dict(ship_row)
                    result["shipment"] = ship
                    job_no = ship.get("job_no", "")
                    booking_no = ship.get("booking_no", "")
                    shipment_id = ship.get("id")

                    # 2. Search Booking
                    if booking_no:
                        cur.execute("SELECT * FROM bookings WHERE tenant_id = %s AND LOWER(booking_no) = %s LIMIT 1", (tenant_id, booking_no.lower()))
                        b_row = cur.fetchone()
                        if b_row:
                            result["booking"] = dict(b_row)

                    # 3. Search Invoices
                    cur.execute("SELECT * FROM invoices WHERE tenant_id = %s AND (LOWER(job_no) = %s OR LOWER(customer_name) LIKE %s) ORDER BY id DESC", 
                                (tenant_id, job_no.lower(), pattern))
                    result["invoices"] = [dict(r) for r in cur.fetchall()]

                    # 4. Search Costs & Profit Summary
                    if shipment_id:
                        cur.execute("""
                            SELECT c.* 
                            FROM job_costs c
                            JOIN shipments s ON c.shipment_id = s.id
                            WHERE s.tenant_id = %s AND c.shipment_id = %s 
                            ORDER BY c.cost_type ASC, c.id ASC
                        """, (tenant_id, shipment_id))
                        costs = [dict(r) for r in cur.fetchall()]
                        result["costs"] = costs

                        # Calculate profit metrics using the single source of truth
                        summary = get_job_financial_summary(shipment_id)
                        result["profit_summary"] = {
                            "total_ar": summary["total_revenue_thb"],
                            "total_ap": summary["total_cost_thb"],
                            "net_profit": summary["gross_profit_thb"],
                            "profit_margin": summary["margin_percent"]
                        }

                    # 5. Search Audit Trail Logs
                    cur.execute("""
                        SELECT a.*, 'System' as username
                        FROM audit_logs a
                        WHERE a.tenant_id = %s AND (LOWER(a.entity_id) = %s OR LOWER(a.details) LIKE %s)
                        ORDER BY a.timestamp DESC LIMIT 100
                    """, (tenant_id, job_no.lower(), pattern))
                    result["audit_trail"] = [dict(r) for r in cur.fetchall()]

                else:
                    # Fallback Search Quotation / Booking / Invoices directly if Shipment not matched
                    cur.execute("SELECT * FROM quotations WHERE LOWER(quotation_no) LIKE %s OR LOWER(customer_name) LIKE %s LIMIT 1", 
                                (pattern, pattern))
                    q_row = cur.fetchone()
                    if q_row:
                        result["quotation"] = dict(q_row)

                    cur.execute("SELECT * FROM bookings WHERE LOWER(booking_no) LIKE %s OR LOWER(customer_name) LIKE %s LIMIT 1", 
                                (pattern, pattern))
                    b_row = cur.fetchone()
                    if b_row:
                        result["booking"] = dict(b_row)

                    cur.execute("SELECT * FROM invoices WHERE LOWER(doc_no) LIKE %s OR LOWER(customer_name) LIKE %s", 
                                (pattern, pattern))
                    result["invoices"] = [dict(r) for r in cur.fetchall()]

    except Exception as e:
        print(f"[WARN] get_360_job_details failed: {str(e)}")

    return result