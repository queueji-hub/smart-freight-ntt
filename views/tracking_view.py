import streamlit as st
import pandas as pd

from managers.shipment_manager import list_shipments
from config import JOB_TYPES

def render():
    st.markdown("<p style='color: #38BDF8; font-weight: 700; font-size: 13px; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 2px;'>Operations Command Center</p>", unsafe_allow_html=True)
    st.markdown("<h2 style='margin-top: 0px; font-weight: 800; color:#F8FAFC;'>🚢 Vessel & Cargo Tracking</h2>", unsafe_allow_html=True)
    st.caption("Live Cargo Monitoring — Global Shipment Visibility & Status Tracking.")

    # Fetch shipments
    with st.spinner("Fetching global shipment routing..."):
        shipments = list_shipments()

    if not shipments:
        st.info("No active shipments found in the pipeline.")
        return

    df = pd.DataFrame(shipments)

    # Search & Filter
    col1, col2 = st.columns([3, 1])
    with col1:
        search = st.text_input("🔍 Search by Job No, Booking No, BL No, or Customer", placeholder="e.g. SE2026...")
    with col2:
        status_filter = st.selectbox("Status Filter", options=["All"] + list(df['status'].unique()) if 'status' in df.columns else ["All"])

    # Apply filters
    if search:
        search = search.lower()
        mask = (
            df['job_no'].str.lower().str.contains(search, na=False) |
            df['booking_no'].str.lower().str.contains(search, na=False) |
            df['bl_no'].str.lower().str.contains(search, na=False) |
            df['customer_name'].str.lower().str.contains(search, na=False)
        )
        df = df[mask]

    if status_filter != "All":
        df = df[df['status'] == status_filter]

    if df.empty:
        st.warning("No tracking records match the current filters.")
        return

    # Modern Enterprise UI Presentation
    column_mapping = {
        "job_no": "Job ID",
        "status": "Status",
        "job_type": "Type",
        "customer_name": "Customer",
        "pol": "POL",
        "pod": "POD",
        "etd": "ETD",
        "eta": "ETA",
        "carrier": "Carrier",
        "bl_no": "BL Number"
    }

    display_cols = [col for col in df.columns if col in column_mapping]
    df_display = df[display_cols].rename(columns=column_mapping)

    st.dataframe(df_display, use_container_width=True, hide_index=True)

    st.markdown("---")
    st.markdown("##### 📍 Shipment Milestones")
    selected_job = st.selectbox("Select Job ID to view routing details", options=df['job_no'].tolist())

    if selected_job:
        job_data = df[df['job_no'] == selected_job].iloc[0]
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Status", job_data['status'])
        c2.metric("ETD (Departure)", str(job_data['etd']))
        c3.metric("ETA (Arrival)", str(job_data['eta']))
        c4.metric("Carrier", job_data['carrier'])
        
        st.info("💡 Note: Direct API integrations with port terminals and carriers for live ETA/ATA tracking will be enabled in the next major patch.")