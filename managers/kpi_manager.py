from database.connection import get_connection


def get_kpi_summary():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    COUNT(*) AS total_shipments,
                    SUM(CASE WHEN status='Proceed' THEN 1 ELSE 0 END),
                    SUM(CASE WHEN status='Finished' THEN 1 ELSE 0 END),
                    SUM(CASE WHEN status='Closed' THEN 1 ELSE 0 END),
                    SUM(CASE WHEN DATE(etd) = CURRENT_DATE THEN 1 ELSE 0 END),
                    SUM(CASE WHEN DATE(eta) = CURRENT_DATE THEN 1 ELSE 0 END)
                FROM shipments
            """)
            row = cur.fetchone()

    return {
        "total_shipments": row[0] or 0,
        "active_jobs": row[1] or 0,
        "finished_jobs": row[2] or 0,
        "closed_jobs": row[3] or 0,
        "etd_today": row[4] or 0,
        "eta_today": row[5] or 0,
    }