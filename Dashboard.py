"""Smart Freight NTT — Main Console (CRM + Shipment + Finance)."""
import streamlit as st
import pandas as pd
from datetime import date

from config import JOB_TYPES
from database.connection import init_database, get_connection
from managers.shipment_manager import (
    list_shipments, get_shipment, create_shipment,
    update_shipment, delete_shipment,
)
from utils.nav import setup_sidebar

# 1. ต้องเป็นคำสั่งแรกสุดของ Streamlit เสมอ
st.set_page_config(
    page_title="Smart Freight NTT",
    page_icon="🚢",
    layout="wide",
)

# 2. รวมศูนย์ CSS ทั้งหมดไว้ที่นี่ที่เดียว (ซ่อนปุ่ม + ตกแต่งสไตล์ Linear)
st.markdown("""
<style>
/* --- กลุ่มคำสั่งซ่อนปุ่มระบบและแถบเครื่องมือตามต้องการ --- */
div[data-testid="stManageAppButton"] { display: none !important; }
#MainMenu, header { visibility: hidden !important; display: none !important; }

/* --- จัดการเมนู Sidebar หน้าแรก --- */
[data-testid="stSidebarNav"] ul li:first-child {
    display: block !important;
}
[data-testid="stSidebarNav"] ul li:first-child a span:first-child {
    font-size: 0;
}
[data-testid="stSidebarNav"] ul li:first-child a span:first-child::after {
    content: "📊 Dashboard";
    font-size: 14px;
}

/* --- โครงสร้างหน้าจอและสไตล์องค์ประกอบต่างๆ --- */
.block-container { padding-top: 1rem; padding-bottom: 1rem; max-width: 100% !important; }

.kpi-strip {
    display: flex; gap: 24px; padding: 12px 16px;
    background: #08090A; border-bottom: 1px solid #23252B;
    margin: -1rem -1rem 1rem -1rem;
}
.kpi-item { font-size: 0.85rem; }
.kpi-label { color: #9CA0A8; }
.kpi-active { color: #26B574; font-family: monospace; font-weight: 600; }
.kpi-done { color: #F7F8F8; font-family: monospace; font-weight: 600; }
.kpi-count { color: #5E6AD2; font-family: monospace; font-weight: 600; }
.section-title {
    font-size: 0.7rem; text-transform: uppercase;
    letter-spacing: 0.08em; color: #62656B;
    margin-bottom: 8px; font-weight: 600;
}
.status-pill {
    display: inline-block; padding: 2px 8px; border-radius: 4px;
    font-size: 0.7rem; font-weight: 500;
}
.s-draft { background: rgba(98,101,107,0.15); color: #9CA0A8; }
.s-progress { background: rgba(94,106,210,0.15); color: #5E6AD2; }
.s-transit { background: rgba(242,153,74,0.15); color: #F2994A; }
.s-finish { background: rgba(38,181,116,0.15); color: #26B574; }
.s-cancel { background: rgba(229,72,77,0.15); color: #E5484D; }
.s-soc { background: rgba(168,85,247,0.15); color: #A855F7; }
</style>
""", unsafe_allow_html=True)

setup_sidebar()

@st.cache_resource
def _init_db():
    init_database()
    return True

_init_db()

# ===== Calculate KPIs =====
all_rows = list_shipments()
total_jobs = len(all_rows)
in_progress = [r for r in all_rows if r.get("status") == "In-Progress"]
finished = [r for r in all_rows if r.get("status") == "Finished"]

def estimate_fee(row):
    """Estimate fee in THB based on container size."""
    size = (row.get("container_size") or "").upper()
    if "40" in size:
        return 75000
    elif "20" in size:
        return 45000
    return 50000

active_revenue = sum(estimate_fee(r) for r in in_progress)
delivered_revenue = sum(estimate_fee(r) for r in finished)

def fmt_baht(n):
    return f"฿{n:,.0f}"

# ===== KPI Strip =====
st.markdown(f"""
<div class="kpi-strip">
    <div class="kpi-item"><span class="kpi-label">Active </span>
        <span class="kpi-active">{fmt_baht(active_revenue)}</span></div>
    <div class="kpi-item"><span class="kpi-label">Delivered </span>
        <span class="kpi-done">{fmt_baht(delivered_revenue)}</span></div>
    <div class="kpi-item"><span class="kpi-label">Total Jobs </span>
        <span class="kpi-count">{total_jobs}</span></div>
    <div class="kpi-item"><span class="kpi-label">In-Progress </span>
        <span class="kpi-count">{len(in_progress)}</span></div>
    <div class="kpi-item"><span class="kpi-label">Finished </span>
        <span class="kpi-count">{len(finished)}</span></div>
</div>
""", unsafe_allow_html=True)

st.markdown("### ⚡ Smart Freight Console")
st.caption("CRM · Shipment · Finance — รวมในหน้าเดียว")

col_form, col_table = st.columns([1, 2], gap="medium")
status_options = ["In-Progress", "Finished", "Cancelled", "SOC", "On-Hold"]

# ===== Form (LEFT) =====
with col_form:
    edit_id = st.session_state.get("compact_edit_id")
    
    if edit_id:
        st.markdown('<div class="section-title">Edit Job</div>', unsafe_allow_html=True)
        loaded = get_shipment(edit_id) if isinstance(edit_id, str) else None
        if not loaded:
            for r in all_rows:
                if r.get("job_no") == edit_id:
                    loaded = r
                    break
    else:
        st.markdown('<div class="section-title">New Job</div>', unsafe_allow_html=True)
        loaded = None
    
    d = loaded or {}
    
    job_type = st.selectbox(
        "Job Type", list(JOB_TYPES.keys()),
        format_func=lambda k: f"{k} — {JOB_TYPES[k]}",
        index=list(JOB_TYPES.keys()).index(d.get("job_type", "SE"))
            if d.get("job_type") in JOB_TYPES else 0,
        key="cc_job_type",
    )
    customer = st.text_input("Customer", value=d.get("customer_name") or "", key="cc_customer")
    booking_no = st.text_input("Booking No.", value=d.get("booking_no") or "", key="cc_booking")
    
    cc1, cc2 = st.columns(2)
    with cc1:
        pol = st.text_input("POL", value=d.get("pol") or "", key="cc_pol")
    with cc2:
        pod = st.text_input("POD", value=d.get("pod") or "", key="cc_pod")
    
    cc3, cc4 = st.columns(2)
    with cc3:
        carrier = st.text_input("Carrier", value=d.get("carrier") or "", key="cc_carrier")
    with cc4:
        size_options = ["", "1x20'GP", "1x40'GP", "1x40'HC", "1x40'HQ"]
        current_size = d.get("container_size") or ""
        if current_size and current_size not in size_options:
            size_options.append(current_size)
        size = st.selectbox("Container", size_options,
                             index=size_options.index(current_size) if current_size in size_options else 0,
                             key="cc_size")
    
    current_status = d.get("status", "In-Progress")
    status = st.selectbox(
        "Status", status_options,
        index=status_options.index(current_status) if current_status in status_options else 0,
        key="cc_status",
    )
    
    container_no = st.text_input("Container No.", value=d.get("container_no") or "", key="cc_container_no")
    
    etd_val = d.get("etd")
    if isinstance(etd_val, str) and etd_val:
        try:
            etd_val = date.fromisoformat(etd_val)
        except ValueError:
            etd_val = None
    etd = st.date_input("ETD", value=etd_val, key="cc_etd")
    
    remark = st.text_area("Internal Notes", value=d.get("remark") or "", height=80, key="cc_remark")
    
    btn_cols = st.columns([1, 1])
    with btn_cols[0]:
        save_label = "💾 Save Changes" if edit_id else "+ Create Job"
        if st.button(save_label, type="primary", use_container_width=True, key="cc_save"):
            if not customer:
                st.error("Customer required")
            else:
                data = {
                    "job_type": job_type,
                    "booking_no": booking_no,
                    "customer_name": customer,
                    "carrier": carrier,
                    "pol": pol,
                    "pod": pod,
                    "container_size": size,
                    "container_no": container_no,
                    "etd": etd.isoformat() if etd else None,
                    "status": status,
                    "remark": remark,
                }
                if edit_id and loaded:
                    if update_shipment(loaded["job_no"], data):
                        st.success(f"✅ Updated {loaded['job_no']}")
                        st.session_state.pop("compact_edit_id", None)
                        st.rerun()
                else:
                    job_no = create_shipment(data)
                    st.success(f"✅ Created {job_no}")
                    st.rerun()
    
    with btn_cols[1]:
        if edit_id:
            if st.button("🗑️ Clear", use_container_width=True, key="cc_clear"):
                st.session_state.pop("compact_edit_id", None)
                st.rerun()

# ===== Table (RIGHT) =====
with col_table:
    title_col, hint_col = st.columns([3, 2])
    with title_col:
        st.markdown('<div class="section-title">Active Shipments</div>', unsafe_allow_html=True)
    with hint_col:
        st.caption("Click ✏️ to edit · Sidebar = Quotation, Shipments")
    
    fcol1, fcol2 = st.columns([2, 3])
    with fcol1:
        filter_status = st.selectbox(
            "Filter", ["All"] + status_options,
            key="cc_filter", label_visibility="collapsed",
        )
    with fcol2:
        search = st.text_input("Search", placeholder="Job No / Customer / Container...",
                               key="cc_search", label_visibility="collapsed")
    
    filtered = all_rows
    if filter_status != "All":
        filtered = [r for r in filtered if r.get("status") == filter_status]
    if search and search.strip():
        s = search.strip().lower()
        filtered = [
            r for r in filtered
            if s in (r.get("job_no") or "").lower()
            or s in (r.get("customer_name") or "").lower()
            or s in (r.get("container_no") or "").lower()
        ]
    
    if not filtered:
        st.info("No matching shipments")
    else:
        for r in filtered[:50]:
            status = r.get("status", "In-Progress")
            status_class = {
                "In-Progress": "s-progress",
                "Finished": "s-finish",
                "Cancelled": "s-cancel",
                "SOC": "s-soc",
                "On-Hold": "s-transit",
            }.get(status, "s-draft")
            
            row_cols = st.columns([1.5, 2.5, 1.5, 1.2, 1, 1.5, 0.6])
            row_cols[0].markdown(f"<code style='font-size:0.8rem;color:#5E6AD2'>{r.get('job_no','')}</code>", unsafe_allow_html=True)
            row_cols[1].markdown(f"<span style='font-size:0.85rem'>{(r.get('customer_name') or '—')[:30]}</span>", unsafe_allow_html=True)
            row_cols[2].markdown(f"<span style='font-size:0.75rem;color:#9CA0A8'>{r.get('pol','?') or '?'} → {r.get('pod','?') or '?'}</span>", unsafe_allow_html=True)
            row_cols[3].markdown(f"<span class='status-pill {status_class}'>{status}</span>", unsafe_allow_html=True)
            row_cols[4].markdown(f"<span style='font-size:0.75rem;color:#62656B;font-family:monospace'>{r.get('container_size','') or ''}</span>", unsafe_allow_html=True)
            row_cols[5].markdown(f"<span style='font-size:0.75rem;color:#62656B'>{(r.get('remark') or '—')[:35]}</span>", unsafe_allow_html=True)
            with row_cols[6]:
                if st.button("✏️", key=f"edit_{r['id']}", help="Edit"):
                    st.session_state["compact_edit_id"] = r["job_no"]
                    st.rerun()
        
        if len(filtered) > 50:
            st.caption(f"แสดง 50 จาก {len(filtered)} รายการ")

# ===== Bottom: Status counts =====
st.markdown("---")
st.markdown('<div class="section-title">Status Breakdown</div>', unsafe_allow_html=True)
bcols = st.columns(5)
status_counts = {s: 0 for s in status_options}
for r in all_rows:
    s = r.get("status", "In-Progress")
    if s in status_counts:
        status_counts[s] += 1

status_meta = [
    ("In-Progress", "🟡", "#F2994A"),
    ("Finished", "🟢", "#26B574"),
    ("Cancelled", "🔴", "#E5484D"),
    ("SOC", "🟣", "#A855F7"),
    ("On-Hold", "🔵", "#5E6AD2"),
]
for i, (name, emoji, color) in enumerate(status_meta):
    with bcols[i]:
        st.markdown(f"""
        <div style="border:1px solid #23252B;border-radius:8px;padding:12px;background:#101113">
            <div style="font-size:0.7rem;color:#9CA0A8;text-transform:uppercase;letter-spacing:0.05em">
                {emoji} {name}
            </div>
            <div style="font-size:1.5rem;font-weight:600;color:{color};margin-top:4px">
                {status_counts[name]}
            </div>
        </div>
        """, unsafe_allow_html=True)