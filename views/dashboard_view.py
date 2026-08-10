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
    st.markdown("<h2 style='margin-top: 0px; font-weight: 800; color:#F8FAFC;'>🚢 FreightFlow Enterprise Control Tower</h2>", unsafe_allow_html=True)
    
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
    st.markdown("<h3 style='font-size:18px; color:#F1F5F9; font-weight:700; margin-bottom:12px;'>🗼 Master Operational Control Tower</h3>", unsafe_allow_html=True)
    st.caption("Real-Time Operational Pipeline Intelligence across Quotations, Bookings, Jobs, Containers, B/Ls, Schedule, and Exception Monitoring.")

    # Data Fetching via Central Dashboard Manager
    try:
        from managers.dashboard_manager import get_operational_control_tower_stats
        tower_stats = get_operational_control_tower_stats()
    except Exception as e:
        st.error(f"Failed to load operational control tower stats: {e}")
        tower_stats = {}

    q_s = tower_stats.get("quotation", {})
    b_s = tower_stats.get("booking", {})
    j_s = tower_stats.get("job", {})
    c_s = tower_stats.get("container", {})
    bl_s = tower_stats.get("bl", {})
    sch_s = tower_stats.get("schedule", {})
    ex_s = tower_stats.get("exceptions", {})

    # ---------------------------------------------------------
    # 1. CORE MODULE METRICS GRID
    # ---------------------------------------------------------
    st.markdown("<h4 style='font-size:15px; color:#38BDF8; font-weight:700; margin-top:10px;'>📊 Pipeline Volume & Lifecycle Statuses</h4>", unsafe_allow_html=True)
    m1, m2, m3, m4, m5 = st.columns(5)

    with m1:
        st.metric("Commercial Quotations", q_s.get("total", 0), f"Active: {q_s.get('active', 0)} | Converted: {q_s.get('converted', 0)}")
    with m2:
        st.metric("Freight Bookings", b_s.get("total", 0), f"Confirmed: {b_s.get('confirmed', 0)} | Rev: {b_s.get('revised', 0)}")
    with m3:
        st.metric("Master Jobs", j_s.get("total", 0), f"Proceed: {j_s.get('proceed', 0)} | In Transit: {j_s.get('in_transit', 0)}")
    with m4:
        st.metric("Containers Manifested", c_s.get("total_containers", 0), f"Jobs w/ Ctr: {c_s.get('jobs_with_containers', 0)}")
    with m5:
        st.metric("Bill of Ladings (B/L)", bl_s.get("total", 0), f"Issued: {bl_s.get('issued', 0)} | Draft: {bl_s.get('draft', 0)}")

    st.markdown("<div style='margin: 15px 0;'></div>", unsafe_allow_html=True)

    # ---------------------------------------------------------
    # 2. DATE & SCHEDULE CONTROL
    # ---------------------------------------------------------
    st.markdown("<h4 style='font-size:15px; color:#38BDF8; font-weight:700;'>📅 Date Control & Schedule Monitoring</h4>", unsafe_allow_html=True)
    d1, d2, d3, d4, d5, d6 = st.columns(6)

    d1.metric("ETD Departure Today", sch_s.get("etd_today", 0), "POL Departure")
    d2.metric("ETD Next 7 Days", sch_s.get("etd_7d", 0), "Upcoming Departures")
    d3.metric("ETD Next 14 Days", sch_s.get("etd_14d", 0), "Two-Week Schedule")
    d4.metric("ETA Arrival Today", sch_s.get("eta_today", 0), "POD Arrival")
    d5.metric("ETA Next 7 Days", sch_s.get("eta_7d", 0), "Upcoming Arrivals")
    d6.metric("Overdue ETA Alerts", sch_s.get("overdue_eta", 0), "- Attention Needed", delta_color="inverse")

    st.markdown("<div style='margin: 15px 0;'></div>", unsafe_allow_html=True)

    # ---------------------------------------------------------
    # 3. EXCEPTION MONITORING (WARNING BOTTLENECKS)
    # ---------------------------------------------------------
    st.markdown("<h4 style='font-size:15px; color:#EF4444; font-weight:700;'>⚠️ Operational Exception & Warning Monitor</h4>", unsafe_allow_html=True)
    ex1, ex2, ex3, ex4 = st.columns(4)

    ex1.metric("Confirmed Booking w/o Job", ex_s.get("unconverted_confirmed_booking", 0), "Pending Job Conversion", delta_color="inverse")
    ex2.metric("Active Jobs w/o Container", ex_s.get("job_without_container", 0), "Container Setup Needed", delta_color="inverse")
    ex3.metric("Active Jobs w/o B/L", ex_s.get("job_without_bl", 0), "B/L Draft Needed", delta_color="inverse")
    ex4.metric("Jobs Missing ETD/ETA", ex_s.get("missing_etd", 0) + ex_s.get("missing_eta", 0), "Routing Date Missing", delta_color="inverse")