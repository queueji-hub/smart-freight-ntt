import streamlit as st
import pandas as pd

# Safe integration layer to absorb relational schema changes smoothly
from managers.dashboard_manager import (
    get_kpi_summary,
    get_monthly_flow,
    get_finance_kpi,
    get_top_routes,
    get_360_job_details,
)

# =========================================================
# STRUCTURAL COMPATIBILITY VALUE HELPER (POSTGRESQL SAFE)
# =========================================================
def safe_numeric(val, default=0.0):
    if val is None:
        return default
    try:
        return float(val)
    except (ValueError, TypeError):
        return default

def safe_int(val, default=0):
    if val is None:
        return default
    try:
        return int(val)
    except (ValueError, TypeError):
        return default

# =========================================================
# 🚀 ULTIMATE SALES PERFORMANCE BOARD RENDER PIPELINE
# =========================================================
def render():
    st.markdown("<p style='color: #38BDF8; font-weight: 700; font-size: 13px; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 2px;'>Enterprise Executive Intelligence</p>", unsafe_allow_html=True)
    st.markdown("<h2 style='margin-top: 0px; font-weight: 800; color:#F8FAFC;'>🚢 Smart Freight Enterprise Control Tower</h2>", unsafe_allow_html=True)
    
    tab_ops, tab_dash, tab_360 = st.tabs([
        "🗼 Operational Logistics Tower",
        "📊 Executive Sales & Finance",
        "🔍 360° Universal Freight Inspector"
    ])

    with tab_ops:
        _render_operational_tower()

    with tab_dash:
        _render_dashboard_analytics()

    with tab_360:
        _render_360_inspector()


def _render_dashboard_analytics():
    # ---------------------------------------------------------
    # DATA INGESTION
    # ---------------------------------------------------------
    with st.spinner("Aggregating Multi-tenant Data Logs..."):
        try:
            kpi_data = get_kpi_summary() or {}
        except Exception as e:
            kpi_data = {}

        try:
            finance_data = get_finance_kpi() or {}
        except Exception as e:
            finance_data = {}

        try:
            flow_data = get_monthly_flow() or {}
        except Exception as e:
            flow_data = {}

        try:
            trade_lanes_raw = get_top_routes() or []
        except Exception as route_err:
            trade_lanes_raw = []

    # ---------------------------------------------------------
    # 💰 SECTION 1: FINANCIAL & TARGET TRACKER
    # ---------------------------------------------------------
    st.markdown("<h3 style='font-size:18px; color:#F1F5F9; font-weight:700; margin-bottom:12px;'>🏆 Revenue & Profit Margins (Month-to-Date)</h3>", unsafe_allow_html=True)
    
    fin_cols = st.columns(3)
    
    gross_revenue = safe_numeric(finance_data.get("revenue"))
    total_cost = safe_numeric(finance_data.get("cost"))
    net_profit = gross_revenue - total_cost
    profit_margin = (net_profit / gross_revenue * 100) if gross_revenue > 0 else 0
    outstanding_ar = safe_numeric(finance_data.get("ar"))
    
    fin_cols[0].metric("Gross Revenue (AR)", f"฿{gross_revenue:,.2f}", "Total Billed")
    fin_cols[1].metric("Net Profit (Est.)", f"฿{net_profit:,.2f}", f"{profit_margin:.1f}% Margin")
    fin_cols[2].metric("Outstanding (AR)", f"฿{outstanding_ar:,.2f}", "- Follow up required", delta_color="inverse")

    # 🎯 TARGET TRACKER PROGRESS BAR (Set target to 1,000,000 THB)
    MONTHLY_TARGET = 1000000 
    progress_percent = min((gross_revenue / MONTHLY_TARGET) * 100, 100)
    
    st.markdown(f"""
    <div style='background-color: #0F172A; padding: 15px; border-radius: 10px; border: 1px solid #1E293B;'>
        <div style='display: flex; justify-content: space-between; font-size: 14px; font-weight: bold; color: #94A3B8; margin-bottom: 8px;'>
            <span>🎯 Monthly Revenue Target (1M THB)</span>
            <span style='color: #38BDF8;'>{progress_percent:.1f}% Achieved</span>
        </div>
        <div style='background-color: #334155; border-radius: 10px; height: 12px; width: 100%;'>
            <div style='background: linear-gradient(90deg, #38BDF8 0%, #10B981 100%); height: 12px; border-radius: 10px; width: {progress_percent}%;'></div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<div style='margin: 25px 0;'></div>", unsafe_allow_html=True)

    # ---------------------------------------------------------
    # 📈 SECTION 2: SALES CONVERSION & OPERATIONS (WIN RATE)
    # ---------------------------------------------------------
    st.markdown("<h3 style='font-size:18px; color:#F1F5F9; font-weight:700; margin-bottom:12px;'>📈 Sales Pipeline & Conversion</h3>", unsafe_allow_html=True)
    
    total_quotes = safe_int(kpi_data.get("total_quotes", 1))
    active_jobs = safe_int(kpi_data.get("active_jobs"))
    finished_jobs = safe_int(kpi_data.get("finished_jobs"))
    closed_jobs = safe_int(kpi_data.get("closed_jobs"))
    
    total_won_jobs = active_jobs + finished_jobs + closed_jobs
    win_rate = (total_won_jobs / total_quotes * 100) if total_quotes > 0 else 0

    ops_cols = st.columns(4)
    ops_cols[0].metric("Total Won Jobs", total_won_jobs, f"Win Rate: {win_rate:.1f}%")
    ops_cols[1].metric("Active (In Transit)", active_jobs)
    ops_cols[2].metric("Finished (Awaiting Invoice)", finished_jobs, "Ready to Bill", delta_color="normal")
    ops_cols[3].metric("Closed (Fully Paid)", closed_jobs)

    st.markdown("<div style='margin: 25px 0;'></div>", unsafe_allow_html=True)
    st.markdown("<hr style='border-top: 1px solid #1E293B;'/>", unsafe_allow_html=True)

    # ---------------------------------------------------------
    # 🌍 SECTION 3: TOP TRADE LANES
    # ---------------------------------------------------------
    st.markdown("<h3 style='font-size:18px; color:#F1F5F9; font-weight:700; margin-bottom:4px;'>🌍 High-Yield Trade Lanes Performance</h3>", unsafe_allow_html=True)
    st.markdown("<p style='font-size:12px; color:#64748B; margin-bottom:14px;'>Focus your sales efforts on these high-volume routes.</p>", unsafe_allow_html=True)

    if trade_lanes_raw:
        df_lanes = pd.DataFrame(trade_lanes_raw)
        if len(df_lanes.columns) >= 3:
            df_lanes = df_lanes.iloc[:, :3]
            df_lanes.columns = ["POL (Origin)", "POD (Destination)", "Volume (TEUs/Jobs)"]
        
        st.dataframe(df_lanes, use_container_width=True, hide_index=True)
    else:
        st.info("ℹ️ No operational trade route statistics available for the current query lifecycle.")


# =========================================================
# 🔍 360° UNIVERSAL FREIGHT INSPECTOR VIEW RENDERER
# =========================================================
def _render_360_inspector():
    st.markdown("### 🔍 360° Universal Freight Inspector & Audit Vault")
    st.caption("Enter any Reference (Job No, Booking No, Quotation No, BL No, Invoice No, or Customer Name) for cross-functional inspection.")

    c_search, c_btn = st.columns([4, 1])
    q = c_search.text_input("Search Reference Identifier *", placeholder="e.g. SE26080001, BK-2026-08, INV-2026-001...", key="inspector_search_input")
    do_search = c_btn.button("⚡ Inspect Job", type="primary", use_container_width=True)

    if q.strip():
        with st.spinner("Extracting 360-degree relational data matrices..."):
            data = get_360_job_details(q.strip())

        if not any([data.get("shipment"), data.get("booking"), data.get("quotation"), data.get("invoices")]):
            st.warning(f"⚠️ No matching operational, sales, or financial records found for reference: '{q.strip()}'")
            return

        ship = data.get("shipment") or {}
        b = data.get("booking") or {}
        q_doc = data.get("quotation") or {}
        invs = data.get("invoices") or []
        costs = data.get("costs") or []
        prof = data.get("profit_summary") or {}
        logs = data.get("audit_trail") or []

        st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Job Identifier", ship.get("job_no") or b.get("booking_no") or q_doc.get("quotation_no") or "N/A")
        m2.metric("Customer / Debtor", ship.get("customer_name") or b.get("customer_name") or q_doc.get("customer_name") or "N/A")
        m3.metric("Current Status", ship.get("status") or b.get("status") or q_doc.get("status") or "N/A")
        m4.metric("Net Profit Margin", f"฿{prof.get('net_profit', 0):,.2f}", f"{prof.get('profit_margin', 0):.1f}% Yield")

        st.markdown("---")
        t_ops, t_sales, t_acc, t_audit = st.tabs([
            "📦 Operations & Shipments", 
            "📄 Sales & Quotations", 
            "💰 Accounting & Financials", 
            "📜 Audit Trail & History Log"
        ])

        with t_ops:
            st.markdown("##### Operational Shipment & Container Movement Details")
            if ship:
                st.json(ship)
            elif b:
                st.json(b)
            else:
                st.info("No active operations shipment record found.")

        with t_sales:
            st.markdown("##### Commercial Sales & Quotation Terms")
            if q_doc:
                st.json(q_doc)
            else:
                st.info("No linked sales quotation record found for this job reference.")

        with t_acc:
            st.markdown("##### Financial Accounting, Invoices & Cost Ledger")
            col_acc1, col_acc2 = st.columns(2)
            col_acc1.metric("Gross Accounts Receivable (AR)", f"฿{prof.get('total_ar', 0):,.2f}")
            col_acc2.metric("Gross Accounts Payable (AP)", f"฿{prof.get('total_ap', 0):,.2f}")

            if invs:
                st.markdown("<h6>Issued Financial Invoices & Billing Documents</h6>", unsafe_allow_html=True)
                st.dataframe(pd.DataFrame(invs), use_container_width=True, hide_index=True)

            if costs:
                st.markdown("<h6>Cost & Revenue Line Items (AR/AP Ledger)</h6>", unsafe_allow_html=True)
                st.dataframe(pd.DataFrame(costs), use_container_width=True, hide_index=True)


# =========================================================
# 🗼 OPERATIONAL LOGISTICS CONTROL TOWER
# =========================================================

def _render_operational_tower():
    from database.connection import get_connection
    from datetime import date, timedelta

    st.markdown("<h3 style='font-size:18px; color:#F1F5F9; font-weight:700; margin-bottom:12px;'>🗼 Freight Pipeline & Operational Control Tower</h3>", unsafe_allow_html=True)

    # 1. Multi-module KPI metrics
    c_q, c_b, c_j, c_bl = st.columns(4)

    counts = {
        "q_total": 0, "bk_total": 0, "job_total": 0, "bl_total": 0,
        "bk_confirmed": 0, "job_active": 0, "bl_issued": 0, "overdue_eta": 0
    }
    today_str = date.today().isoformat()

    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) as c FROM quotations")
                counts["q_total"] = cur.fetchone()["c"]

                cur.execute("SELECT COUNT(*) as c FROM bookings")
                counts["bk_total"] = cur.fetchone()["c"]

                cur.execute("SELECT COUNT(*) as c FROM bookings WHERE UPPER(status) = 'CONFIRMED'")
                counts["bk_confirmed"] = cur.fetchone()["c"]

                cur.execute("SELECT COUNT(*) as c FROM shipments")
                counts["job_total"] = cur.fetchone()["c"]

                cur.execute("SELECT COUNT(*) as c FROM shipments WHERE status IN ('Proceed', 'In Transit', 'Arrived')")
                counts["job_active"] = cur.fetchone()["c"]

                cur.execute("SELECT COUNT(*) as c FROM bills_of_lading")
                counts["bl_total"] = cur.fetchone()["c"]

                cur.execute("SELECT COUNT(*) as c FROM bills_of_lading WHERE status = 'Issued'")
                counts["bl_issued"] = cur.fetchone()["c"]

                cur.execute("SELECT COUNT(*) as c FROM shipments WHERE eta < %s AND status NOT IN ('Finished', 'Closed', 'Canceled')", (today_str,))
                counts["overdue_eta"] = cur.fetchone()["c"]
    except Exception as e:
        pass

    c_q.metric("Quotations", counts["q_total"], "Commercial Pipeline")
    c_b.metric("Bookings", counts["bk_total"], f"{counts['bk_confirmed']} Confirmed", delta_color="normal")
    c_j.metric("Active Jobs", counts["job_active"], f"Out of {counts['job_total']} total")
    c_bl.metric("Bill of Ladings", counts["bl_total"], f"{counts['bl_issued']} Issued", delta_color="normal")

    st.markdown("<div style='margin: 20px 0;'></div>", unsafe_allow_html=True)

    # 2. Upcoming Schedule (Next 14 Days)
    st.markdown("<h4 style='font-size:16px; color:#F1F5F9; font-weight:700;'>📅 Upcoming Operations (Next 14 Days Schedule)</h4>", unsafe_allow_html=True)
    next_14 = (date.today() + timedelta(days=14)).isoformat()

    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT job_no, customer_name, pol, pod, vessel, voyage, etd, eta, status
                    FROM shipments
                    WHERE etd BETWEEN %s AND %s OR eta BETWEEN %s AND %s
                    ORDER BY etd ASC LIMIT 10
                """, (today_str, next_14, today_str, next_14))
                rows = [dict(r) for r in cur.fetchall()]

        if rows:
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
        else:
            st.info("ℹ️ No upcoming shipments scheduled for departure/arrival in the next 14 days.")
    except Exception as e:
        st.warning(f"Unable to query schedule: {e}")

    st.markdown("<div style='margin: 20px 0;'></div>", unsafe_allow_html=True)

    # 3. Exception Monitor
    st.markdown("<h4 style='font-size:16px; color:#F1F5F9; font-weight:700;'>⚠️ Operational Exception & Warning Monitor</h4>", unsafe_allow_html=True)
    ex1, ex2, ex3 = st.columns(3)

    ex1.metric("Overdue ETAs", counts["overdue_eta"], "Action Required", delta_color="inverse")
    
    # Confirmed Bookings without Job
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) as c FROM bookings WHERE UPPER(status) = 'CONFIRMED'")
                unconverted_bks = cur.fetchone()["c"]
        ex2.metric("Confirmed Bookings Awaiting Job", unconverted_bks, "Pending Conversion")
    except Exception:
        ex2.metric("Confirmed Bookings Awaiting Job", 0)

    # Jobs without containers
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT COUNT(*) as c FROM shipments s
                    WHERE s.status IN ('Proceed', 'In Transit')
                      AND s.id NOT IN (SELECT DISTINCT shipment_id FROM containers)
                """)
                no_ctr_jobs = cur.fetchone()["c"]
        ex3.metric("Active Jobs Missing Containers", no_ctr_jobs, "Container Setup Needed", delta_color="inverse")
    except Exception:
        ex3.metric("Active Jobs Missing Containers", 0)


        with t_audit:
            st.markdown("##### Complete Audit Trail & Timestamped Operator History")
            if logs:
                st.dataframe(pd.DataFrame(logs)[["timestamp", "username", "action", "entity", "entity_id", "details"]], use_container_width=True, hide_index=True)
            else:
                st.info("No recorded security audit logs found for this reference identifier.")