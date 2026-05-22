"""Container Tracking view - timeline + milestone management."""
import streamlit as st
from datetime import datetime, date
import pandas as pd

from managers.shipment_manager import list_shipments, get_shipment
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
    st.caption("Real-time milestone tracking · Container movement timeline")
    
    # Select shipment
    ships = list_shipments()
    if not ships:
        st.info("No shipments to track. Create one in the Shipment module.")
        return
    
    options = {f"{s['job_no']} — {s.get('customer_name','') or '—'} "
               f"({s.get('container_no','—')})": s for s in ships[:200]}
    
    sel_label = st.selectbox("Select shipment", list(options.keys()),
                              key="track_sel")
    ship = options[sel_label]
    
    # Header info
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Job No.", ship["job_no"])
    with col2:
        st.metric("Container", ship.get("container_no") or "—")
    with col3:
        st.metric("Route",
            f"{ship.get('pol','?')} → {ship.get('pod','?')}")
    with col4:
        latest = get_latest_status(ship["id"])
        cur_status = latest["milestone_name"] if latest else "Not started"
        st.metric("Latest Status", cur_status)
    
    st.markdown("---")
    
    # Add milestone form
    if can_edit:
        with st.expander("➕ Add Milestone", expanded=False):
            mc1, mc2, mc3 = st.columns([2, 1.5, 1])
            with mc1:
                ms_options = [(c, f"{i} {n}") for c, n, i in MILESTONES]
                sel_ms = st.selectbox("Milestone", ms_options,
                    format_func=lambda x: x[1], key="track_ms")
                code = sel_ms[0]
            with mc2:
                date_val = st.date_input("Date", value=date.today(),
                                           key="track_date")
                time_val = st.time_input("Time", value=datetime.now().time(),
                                           key="track_time")
            with mc3:
                location = st.text_input("Location", key="track_loc",
                    placeholder="e.g. Bangkok Port")
            
            note = st.text_input("Note (optional)", key="track_note")
            
            if st.button("✅ Record Milestone", type="primary",
                          use_container_width=True):
                occurred = datetime.combine(date_val, time_val)
                add_milestone(
                    ship["id"], code, occurred_at=occurred,
                    location=location, note=note,
                    created_by=user.get("username")
                )
                st.success(f"Recorded: {MILESTONE_NAMES[code]}")
                st.rerun()
    
    # Timeline display
    st.markdown("##### 📍 Timeline")
    milestones = get_milestones(ship["id"])
    
    if not milestones:
        st.info("No milestones recorded yet.")
    else:
        # Render timeline as styled cards
        st.markdown("""
        <style>
        .timeline-item {
            display:flex; gap:12px; padding:10px 14px;
            background:#101113; border:1px solid #23252B;
            border-radius:8px; margin-bottom:8px;
            border-left: 3px solid #26B574;
        }
        .ts-icon { font-size: 1.4rem; }
        .ts-content { flex: 1; }
        .ts-name { font-weight: 600; font-size: 0.95rem; }
        .ts-meta { font-size: 0.75rem; color: #9CA0A8; margin-top: 2px; }
        .ts-note { font-size: 0.8rem; color: #62656B; margin-top: 4px; }
        </style>
        """, unsafe_allow_html=True)
        
        for m in milestones:
            icon = MILESTONE_ICONS.get(m["milestone_code"], "📍")
            occurred = m.get("occurred_at", "")
            location = m.get("location") or ""
            note = m.get("note") or ""
            
            cols = st.columns([10, 1])
            with cols[0]:
                st.markdown(f"""
                <div class="timeline-item">
                    <div class="ts-icon">{icon}</div>
                    <div class="ts-content">
                        <div class="ts-name">{m['milestone_name']}</div>
                        <div class="ts-meta">
                            🕐 {occurred} {' · 📍 ' + location if location else ''}
                            {' · by ' + (m.get('created_by') or '') if m.get('created_by') else ''}
                        </div>
                        {f'<div class="ts-note">📝 {note}</div>' if note else ''}
                    </div>
                </div>
                """, unsafe_allow_html=True)
            with cols[1]:
                if can_edit:
                    if st.button("🗑️", key=f"del_ms_{m['id']}",
                                  help="Delete milestone"):
                        delete_milestone(m["id"])
                        st.rerun()
