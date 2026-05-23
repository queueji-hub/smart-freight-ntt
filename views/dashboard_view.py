from database.connection import get_connection

from managers.kpi_manager import (
    get_kpi_summary,
    get_finance_kpi,
    get_top_routes,
    get_port_monthly_volume
)

# =========================
# KPI CORE
# =========================

kpi = get_kpi_summary()

st.metric("Total Jobs", kpi["total_shipments"])
st.metric("Active Jobs", kpi["active_jobs"])
st.metric("Finished", kpi["finished_jobs"])
st.metric("Closed", kpi["closed_jobs"])


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