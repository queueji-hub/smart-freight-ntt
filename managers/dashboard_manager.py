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
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    pol,
                    pod,
                    COUNT(*) AS volume
                FROM shipments
                GROUP BY pol, pod
                ORDER BY volume DESC
                LIMIT 10
            """)
            return cur.fetchall()


# =========================
# 360° CROSS-FUNCTIONAL JOB INSPECTOR
# =========================

def get_360_job_details(query: str) -> dict:
    """
    360-degree inspection engine linking Sales (Quotation), Ops (Booking & Shipment),
    Accounting (Invoices & AR/AP Costs), and Security Audit Trail.
    """
    clean_q = (query or "").strip()
    if not clean_q:
        return {}

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
                    WHERE LOWER(job_no) LIKE %s OR LOWER(booking_no) LIKE %s OR LOWER(bl_no) LIKE %s OR LOWER(customer_name) LIKE %s
                    ORDER BY id DESC LIMIT 1
                """, (pattern, pattern, pattern, pattern))
                ship_row = cur.fetchone()

                if ship_row:
                    ship = dict(ship_row)
                    result["shipment"] = ship
                    job_no = ship.get("job_no", "")
                    booking_no = ship.get("booking_no", "")
                    shipment_id = ship.get("id")

                    # 2. Search Booking
                    if booking_no:
                        cur.execute("SELECT * FROM bookings WHERE LOWER(booking_no) = %s LIMIT 1", (booking_no.lower(),))
                        b_row = cur.fetchone()
                        if b_row:
                            result["booking"] = dict(b_row)

                    # 3. Search Invoices
                    cur.execute("SELECT * FROM invoices WHERE LOWER(job_no) = %s OR LOWER(customer_name) LIKE %s ORDER BY id DESC", 
                                (job_no.lower(), pattern))
                    result["invoices"] = [dict(r) for r in cur.fetchall()]

                    # 4. Search Costs & Profit Summary
                    if shipment_id:
                        cur.execute("SELECT * FROM job_costs WHERE shipment_id = %s ORDER BY cost_type ASC, id ASC", (shipment_id,))
                        costs = [dict(r) for r in cur.fetchall()]
                        result["costs"] = costs

                        # Calculate profit metrics
                        ar = sum(float(c.get("amount_thb", 0) or 0) for c in costs if c.get("cost_type") == "AR")
                        ap = sum(float(c.get("amount_thb", 0) or 0) for c in costs if c.get("cost_type") == "AP")
                        net = ar - ap
                        margin = (net / ar * 100) if ar > 0 else 0.0
                        result["profit_summary"] = {
                            "total_ar": round(ar, 2),
                            "total_ap": round(ap, 2),
                            "net_profit": round(net, 2),
                            "profit_margin": round(margin, 2)
                        }

                    # 5. Search Audit Trail Logs
                    cur.execute("""
                        SELECT a.*, COALESCE(u.username, 'System') as username
                        FROM audit_logs a
                        LEFT JOIN users u ON a.user_id = u.id
                        WHERE LOWER(a.entity_id) = %s OR LOWER(a.details) LIKE %s
                        ORDER BY a.timestamp DESC LIMIT 100
                    """, (job_no.lower(), pattern))
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