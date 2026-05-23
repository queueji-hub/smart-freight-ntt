"""Dashboard - Real-time KPIs + Active Shipments overview."""
import streamlit as st
import pandas as pd
from datetime import date, timedelta

from managers.shipment_manager import list_shipments, get_dashboard_stats
from managers.invoice_manager import get_outstanding_summary
from managers.customer_manager import list_customers


STATUS_COLORS = {
    "Proceed": "#5E6AD2",
    "Finished": "#26B574",
    "Closed": "#62656B",
    "Canceled": "#E5484D",
}


def render():
    user = st.session_state.get("user", {})
    
    st.markdown(f"### 📊 Dashboard")
    st.caption(f"Welcome back, **{user.get('full_name','User')}** · "
               f"role: `{user.get('role','-')}`")
    
    # ===== Inject CSS =====
    st.markdown("""
    <style>
    .kpi-card {
        background: linear-gradient(135deg, #101113 0%, #1A1B1E 100%);
        border: 1px solid #23252B;
        border-radius: 10px;
        padding: 1rem 1.25rem;
        height: 100%;
    }
    .kpi-label { font-size: 0.7rem; text-transform: uppercase;
                 letter-spacing: 0.05em; color: #9CA0A8; margin-bottom: 4px; }
    .kpi-value { font-size: 1.6rem; font-weight: 700; font-family: monospace; }
    .kpi-sub { font-size: 0.75rem; color: #62656B; margin-top: 4px; }
    .status-pill {
        display: inline-block; padding: 2px 8px; border-radius: 4px;
        font-size: 0.7rem; font-weight: 500;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # ===== Top KPI cards =====
    stats = get_dashboard_stats()
    fin = get_outstanding_summary()
    customers = list_customers()
    
    cols = st.columns(5)
    _kpi(cols[0], "Total Jobs", stats["total"], "all-time", "#5E6AD2")
    _kpi(cols[1], "Proceed", stats["proceed"], "active jobs", STATUS_COLORS["Proceed"])
    _kpi(cols[2], "Finished", stats["finished"], "completed", STATUS_COLORS["Finished"])
    _kpi(cols[3], "Customers", len(customers), "active in CRM", "#A855F7")
    _kpi(cols[4], "Outstanding", f"฿{fin['outstanding']:,.0f}",
         "unpaid invoices", "#F2994A")
    
    st.markdown("---")
    
    # ===== Two-column: Active Shipments + Status Breakdown =====
    col_main, col_side = st.columns([2, 1], gap="medium")
    
    with col_main:
        st.markdown("##### 🚢 Recent Active Shipments")
        active = list_shipments(status="Proceed", limit=15)
        
        if not active:
            st.info("No active shipments. Create one in the Shipment module.")
        else:
            df = pd.DataFrame(active)
            display_cols = ["job_no", "customer_name", "pol", "pod",
                            "carrier", "etd", "status"]
            display_cols = [c for c in display_cols if c in df.columns]
            st.dataframe(df[display_cols], use_container_width=True,
                hide_index=True, height=420,
                column_config={
                    "job_no": "Job No.",
                    "customer_name": "Customer",
                    "pol": "POL", "pod": "POD",
                    "carrier": "Carrier", "etd": "ETD",
                    "status": "Status",
                })
    
    with col_side:
        st.markdown("##### 📈 Status Breakdown")
        status_data = [
            ("Proceed", stats["proceed"], STATUS_COLORS["Proceed"]),
            ("Finished", stats["finished"], STATUS_COLORS["Finished"]),
            ("Closed", stats["closed"], STATUS_COLORS["Closed"]),
            ("Canceled", stats["canceled"], STATUS_COLORS["Canceled"]),
        ]
        for name, count, color in status_data:
            st.markdown(f"""
            <div style="border:1px solid #23252B;border-radius:8px;
                        padding:10px 14px;margin-bottom:8px;background:#101113">
                <div style="display:flex;justify-content:space-between;
                            align-items:center">
                    <span style="color:{color};font-weight:600">{name}</span>
                    <span style="font-size:1.4rem;font-weight:700;
                                 font-family:monospace;color:{color}">
                        {count}
                    </span>
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        # Job type breakdown
        st.markdown("##### 📦 By Job Type")
        if stats["by_type"]:
            df_type = pd.DataFrame(stats["by_type"])
            df_type.columns = ["Type", "Count"]
            st.bar_chart(df_type.set_index("Type"), height=220)
    
    # ===== Bottom: Monthly trend =====
    if stats["by_month"]:
        st.markdown("---")
        st.markdown("##### 📅 Monthly Job Volume (by ETD)")
        df_month = pd.DataFrame(stats["by_month"])
        df_month.columns = ["Month", "Jobs"]
        st.line_chart(df_month.set_index("Month"), height=240)


def _kpi(col, label, value, sub, color):
    with col:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-label">{label}</div>
            <div class="kpi-value" style="color:{color}">{value}</div>
            <div class="kpi-sub">{sub}</div>
        </div>
        """, unsafe_allow_html=True)
def get_dashboard_stats() -> Dict[str, Any]:
    """Aggregated stats for dashboard KPIs."""
    _ensure_table()
    with get_connection() as conn:
        # ปรับ SQL ให้ได้ชื่อคอลัมน์ตรงกับ Key ที่ Dashboard เรียกใช้
        query = """
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN status = 'Proceed' THEN 1 ELSE 0 END) as proceed,
                SUM(CASE WHEN status = 'Finished' THEN 1 ELSE 0 END) as finished,
                SUM(CASE WHEN status = 'Closed' THEN 1 ELSE 0 END) as closed,
                SUM(CASE WHEN status = 'Canceled' THEN 1 ELSE 0 END) as canceled
            FROM shipments
        """
        result = conn.execute(query).fetchone()
        
    # แปลงเป็น Dictionary ให้สอดคล้องกับ Dashboard View
    if hasattr(result, 'keys'):
        return dict(result)
    else:
        # กรณี result เป็น Tuple
        return {
            'total': result[0] or 0,
            'proceed': result[1] or 0,
            'finished': result[2] or 0,
            'closed': result[3] or 0,
            'canceled': result[4] or 0
        }