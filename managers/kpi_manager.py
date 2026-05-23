from database.connection import get_connection


# =========================
# SAFE CONVERTER
# =========================
def _row_to_dict(row):
    return dict(row) if row else {}


def _rows_to_list(rows):
    return [dict(r) for r in rows] if rows else []


# =========================
# KPI SUMMARY (SHIPMENT)
# =========================
def get_kpi_summary():
    with get_connection() as conn:
        row = conn.execute("""
            SELECT
                COUNT(*) AS total_shipments,

                COALESCE(SUM(CASE WHEN status='Proceed' THEN 1 ELSE 0 END),0) AS active_jobs,
                COALESCE(SUM(CASE WHEN status='Finished' THEN 1 ELSE 0 END),0) AS finished_jobs,
                COALESCE(SUM(CASE WHEN status='Closed' THEN 1 ELSE 0 END),0) AS closed_jobs,
                COALESCE(SUM(CASE WHEN status='Canceled' THEN 1 ELSE 0 END),0) AS canceled_jobs,

                COALESCE(SUM(CASE WHEN DATE(etd) = CURRENT_DATE THEN 1 ELSE 0 END),0) AS etd_today,
                COALESCE(SUM(CASE WHEN DATE(eta) = CURRENT_DATE THEN 1 ELSE 0 END),0) AS eta_today

            FROM shipments
        """).fetchone()

    return _row_to_dict(row)


# =========================
# MONTHLY FLOW (ETD / ETA)
# =========================
def get_monthly_flow():
    with get_connection() as conn:
        row = conn.execute("""
            SELECT
                COALESCE(COUNT(*) FILTER (
                    WHERE DATE_TRUNC('month', etd) = DATE_TRUNC('month', CURRENT_DATE)
                ),0) AS etd_this_month,

                COALESCE(COUNT(*) FILTER (
                    WHERE DATE_TRUNC('month', eta) = DATE_TRUNC('month', CURRENT_DATE)
                ),0) AS eta_this_month

            FROM shipments
        """).fetchone()

    return _row_to_dict(row)


# =========================
# FINANCE KPI
# =========================
def get_finance_kpi():
    with get_connection() as conn:
        row = conn.execute("""
            SELECT
                COALESCE(SUM(total_amount),0) AS revenue,
                COALESCE(SUM(outstanding),0) AS ar
            FROM invoices
        """).fetchone()

    return _row_to_dict(row)


# =========================
# TOP ROUTES (POL → POD)
# =========================
def get_top_routes(limit=10):
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT
                pol,
                pod,
                COUNT(*) AS volume
            FROM shipments
            GROUP BY pol, pod
            ORDER BY volume DESC
            LIMIT %s
        """, (limit,)).fetchall()

    return _rows_to_list(rows)


# =========================
# ETA / ETD DASHBOARD VIEW DATA
# =========================
def get_eta_etd_overview():
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT
                job_no,
                customer_name,
                pol,
                pod,
                etd,
                eta,
                status
            FROM shipments
            ORDER BY COALESCE(etd, eta) DESC
            LIMIT 50
        """).fetchall()

    return _rows_to_list(rows)


# =========================
# PORT MONTHLY VOLUME (THAILAND OPS)
# =========================
def get_port_monthly_volume():
    with get_connection() as conn:
        cur = conn.execute("""
            SELECT
                COALESCE(pol, 'UNKNOWN') AS pol,
                COUNT(*) AS export_volume,
                COUNT(CASE WHEN pod ILIKE '%TH%' THEN 1 END) AS import_volume
            FROM shipments
            WHERE pol IS NOT NULL
            GROUP BY pol
            ORDER BY COUNT(*) DESC
        """)

        rows = cur.fetchall()

    return [dict(r) for r in rows] if rows else []