"""Dashboard - Real-time KPIs + Active Shipments overview."""
import streamlit as st
import pandas as pd
from typing import Dict, Any

# 1. ปรับปรุงการ Import ให้ถูกต้องและครบถ้วน
from managers.shipment_manager import list_shipments, get_dashboard_stats, _ensure_table
from managers.invoice_manager import get_outstanding_summary
from managers.customer_manager import list_customers

STATUS_COLORS = {
    "Proceed": "#5E6AD2",
    "Finished": "#26B574",
    "Closed": "#62656B",
    "Canceled": "#E5484D",
}

@st.cache_data(ttl=300)
def get_cached_stats():
    return get_dashboard_stats()

@st.cache_data(ttl=60)
def get_cached_customers():
    return list_customers()

def _kpi(col, label, value, sub, color):
    """ฟังก์ชัน helper สำหรับแสดง KPI card"""
    with col:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-label">{label}</div>
            <div class="kpi-value" style="color:{color}">{value}</div>
            <div style="font-size: 0.75rem; color: #62656B; margin-top: 4px;">{sub}</div>
        </div>
        """, unsafe_allow_html=True)

def render():
    # 2. ตรวจสอบตารางฐานข้อมูลก่อนรันทุกครั้ง (ป้องกัน NameError)
    _ensure_table()
    
    user = st.session_state.get("user", {})
    
    st.markdown(f"### 📊 Dashboard")
    st.caption(f"Welcome back, **{user.get('full_name','User')}** · role: `{user.get('role','-')}`")
    
    # CSS Injection
    st.markdown("""
    <style>
    .kpi-card { background: linear-gradient(135deg, #101113 0%, #1A1B1E 100%); border: 1px solid #23252B; border-radius: 10px; padding: 1rem; height: 100%; }
    .kpi-label { font-size: 0.7rem; text-transform: uppercase; letter-spacing: 0.05em; color: #9CA0A8; margin-bottom: 4px; }
    .kpi-value { font-size: 1.6rem; font-weight: 700; font-family: monospace; }
    </style>
    """, unsafe_allow_html=True)
    
    # Fetch Data
    stats = get_cached_stats()
    fin = get_outstanding_summary()
    custs = get_cached_customers()
    
    # Top KPI Cards
    cols = st.columns(5)
    _kpi(cols[0], "Total Jobs", stats.get("total", 0), "all-time", "#5E6AD2")
    _kpi(cols[1], "Proceed", stats.get("proceed", 0), "active jobs", STATUS_COLORS["Proceed"])
    _kpi(cols[2], "Finished", stats.get("finished", 0), "completed", STATUS_COLORS["Finished"])
    _kpi(cols[3], "Customers", len(custs), "active in CRM", "#A855F7")
    _kpi(cols[4], "Outstanding", f"฿{fin.get('outstanding', 0):,.0f}", "unpaid", "#F2994A")
    
    st.markdown("---")
    
    # Main Content
    col_main, col_side = st.columns([2, 1], gap="medium")
    
    with col_main:
        st.markdown("##### 🚢 Recent Active Shipments")
        # ใช้ list_shipments ปกติ (ไม่ต้องใส่ limit หากฟังก์ชันเดิมไม่มี parameter นี้)
        active = list_shipments() 
        if not active:
            st.info("No active shipments.")
        else:
            df = pd.DataFrame(active)
            st.dataframe(df, use_container_width=True, hide_index=True, height=420)
    
    with col_side:
        st.markdown("##### 📈 Status Breakdown")
        for status in ["Proceed", "Finished", "Closed", "Canceled"]:
            val = stats.get(status.lower(), 0)
            color = STATUS_COLORS.get(status, "#FFFFFF")
            st.markdown(f"""
            <div style="border-left: 4px solid {color}; padding: 10px; background:#101113; margin-bottom:8px; border-radius:4px">
                <div style="display:flex; justify-content:space-between;">
                    <span>{status}</span> <strong>{val}</strong>
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        if stats.get("by_type"):
            st.markdown("##### 📦 By Job Type")
            df_type = pd.DataFrame(stats["by_type"])
            st.bar_chart(df_type.set_index(df_type.columns[0]), height=200)