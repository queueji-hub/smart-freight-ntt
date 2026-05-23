import streamlit as st
from datetime import datetime, date
import pandas as pd

from managers.shipment_manager import list_shipments
from managers.container_manager import (
    MILESTONES, MILESTONE_NAMES, MILESTONE_ICONS,
    add_milestone, get_milestones, delete_milestone, get_latest_status,
)
from managers.auth_manager import can_write

def render():
    user = st.session_state.get("user", {})
    role = user.get("role", "")
    can_edit = can_write(role, "shipment")
    
    st.title("🚢 Container Tracking")
    
    # 1. Select Shipment (Filter only Active Jobs)
    ships = [s for s in list_shipments() if s.get('status') not in ['Closed', 'Canceled']]
    if not ships:
        st.info("No active shipments to track.")
        return
    
    options = {f"{s['job_no']} — {s.get('customer_name','')} ({s.get('container_no','-')})": s for s in ships}
    sel_label = st.selectbox("Select shipment", list(options.keys()))
    ship = options[sel_label]
    
    # 2. Header Status
    latest = get_latest_status(ship["id"])
    col1, col2, col3 = st.columns(3)
    col1.metric("Job No.", ship["job_no"])
    col2.metric("Container", ship.get("container_no") or "-")
    col3.metric("Latest Status", latest["milestone_name"] if latest else "Not started")
    
    # Progress bar
    milestones = get_milestones(ship["id"])
    progress = min(len(milestones) / len(MILESTONES), 1.0)
    st.progress(progress, text=f"Route Progress: {int(progress*100)}%")
    
    st.divider()
    
    # 3. Add Milestone Form
    if can_edit:
        with st.expander("➕ Add Milestone", expanded=False):
            # ปุ่มลัดเวลาปัจจุบัน
            if st.button("⏰ Set to Now"):
                st.session_state["m_date"] = date.today()
                st.session_state["m_time"] = datetime.now().time()
            
            mc1, mc2, mc3 = st.columns([2, 1.5, 1])
            with mc1:
                sel_ms = st.selectbox("Milestone", [(c, f"{i} {n}") for c, n, i in MILESTONES], format_func=lambda x: x[1])
            with mc2:
                d = st.date_input("Date", value=st.session_state.get("m_date", date.today()), key="m_date")
                t = st.time_input("Time", value=st.session_state.get("m_time", datetime.now().time()), key="m_time")
            with mc3:
                loc = st.text_input("Location", placeholder="e.g. Bangkok Port")
            
            note = st.text_input("Note")
            
            if st.button("✅ Record Milestone", type="primary", use_container_width=True):
                add_milestone(ship["id"], sel_ms[0], occurred_at=datetime.combine(d, t), 
                              location=loc, note=note, created_by=user.get("username"))
                st.rerun()
    
    # 4. Timeline Display
    st.markdown("##### 📍 Timeline")
    if not milestones:
        st.info("No milestones recorded.")
    else:
        st.markdown("""<style>.timeline-item{display:flex;gap:12px;padding:10px;background:#101113;border-radius:8px;margin-bottom:8px;border-left:3px solid #26B574;}</style>""", unsafe_allow_html=True)
        
        for m in milestones:
            cols = st.columns([10, 1])
            with cols[0]:
                st.markdown(f"""
                <div class="timeline-item">
                    <div style="font-size:1.4rem">{MILESTONE_ICONS.get(m['milestone_code'], '📍')}</div>
                    <div>
                        <div style="font-weight:600">{m['milestone_name']}</div>
                        <div style="font-size:0.75rem; color:#9CA0A8">🕐 {m['occurred_at']} · 📍 {m.get('location') or '-'}</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
            with cols[1]:
                if can_edit and st.button("🗑️", key=f"del_{m['id']}"):
                    delete_milestone(m["id"])
                    st.rerun()