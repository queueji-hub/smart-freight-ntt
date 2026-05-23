from database.connection import get_connection


# =========================
# KPI CORE
# =========================

def get_kpi_summary():
    with get_connection() as conn:
        return conn.execute("""
            SELECT
                COUNT(*) AS total_shipments,

                SUM(CASE WHEN status='Proceed' THEN 1 ELSE 0 END) AS active_jobs,
                SUM(CASE WHEN status='Finished' THEN 1 ELSE 0 END) AS finished_jobs,
                SUM(CASE WHEN status='Closed' THEN 1 ELSE 0 END) AS closed_jobs,

                SUM(CASE WHEN DATE(etd) = CURRENT_DATE THEN 1 ELSE 0 END) AS etd_today,
                SUM(CASE WHEN DATE(eta) = CURRENT_DATE THEN 1 ELSE 0 END) AS eta_today

            FROM shipments
        """).fetchone()


# =========================
# MONTHLY FLOW
# =========================

def get_monthly_flow():
    with get_connection() as conn:
        return conn.execute("""
            SELECT
                COUNT(*) FILTER (WHERE DATE_TRUNC('month', etd) = DATE_TRUNC('month', CURRENT_DATE)) AS etd_this_month,
                COUNT(*) FILTER (WHERE DATE_TRUNC('month', eta) = DATE_TRUNC('month', CURRENT_DATE)) AS eta_this_month
            FROM shipments
        """).fetchone()


# =========================
# FINANCE KPI
# =========================

def get_finance_kpi():
    with get_connection() as conn:
        return conn.execute("""
            SELECT
                COALESCE(SUM(total_amount),0) AS revenue,
                COALESCE(SUM(outstanding),0) AS ar
            FROM invoices
        """).fetchone()


# =========================
# TOP ROUTES
# =========================

def get_top_routes():
    with get_connection() as conn:
        return conn.execute("""
            SELECT
                pol,
                pod,
                COUNT(*) AS volume
            FROM shipments
            GROUP BY pol, pod
            ORDER BY volume DESC
            LIMIT 10
        """).fetchall()