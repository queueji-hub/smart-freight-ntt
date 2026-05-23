import streamlit as st
import pandas as pd
from typing import Dict, Any, Optional
from datetime import date
from database.connection import get_connection
from config import JOB_TYPES
from managers.auth_manager import can_write
from managers.booking_manager import list_bookings
from managers.job_number import generate_job_number

# Constants
STATUS_OPTIONS = ["Proceed", "Finished", "Closed", "Canceled"]
SIZE_OPTIONS = ["1x20'GP", "1x40'GP", "1x40'HC", "1x40'HQ", "1x20'OT", "1x40'OT", "1x20'FR", "Other"]
CARGO_TYPES = ["", "FCL", "LCL", "AIR", "TRUCK"]

def _ensure_table():
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS shipments (
                id SERIAL PRIMARY KEY,
                job_no TEXT UNIQUE NOT NULL,
                status TEXT DEFAULT 'Proceed',
                job_type TEXT,
                booking_no TEXT,
                customer_name TEXT,
                shipper TEXT,
                consignee TEXT,
                cargo_type TEXT,
                carrier TEXT,
                pol TEXT,
                pod TEXT,
                etd DATE,
                eta DATE,
                bl_no TEXT,
                invoice_no TEXT,
                customer_paid INTEGER DEFAULT 0,
                remark TEXT,
                created_by TEXT,
                updated_by TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_shipments_job_no ON shipments(job_no);")
        conn.commit()

def render():
    _ensure_table()
    user = st.session_state.get("user", {})
    can_edit = can_write(user.get("role", ""), "shipment")

    st.title("📦 Shipment / Job Control")
    
    tabs = st.tabs(["➕ Create", "📋 List & Batch Edit", "✏️ Single Edit"])

    with tabs[0]:
        _create_form(user)
    with tabs[1]:
        _list_view()
    with tabs[2]:
        _edit_view(user)

def _create_form(user):
    with st.form("create_shipment_form"):
        col1, col2 = st.columns(2)
        with col1:
            job_type = st.selectbox("Job Type", JOB_TYPES)
            customer = st.text_input("Customer *")
        with col2:
            cargo = st.selectbox("Cargo Type", CARGO_TYPES)
            etd = st.date_input("ETD", value=None)
            eta = st.date_input("ETA", value=None)

        remark = st.text_area("Remark")
        if st.form_submit_button("✅ Create"):
            if not customer:
                st.error("Customer is required")
            elif etd and eta and etd > eta:
                st.error("ETD cannot be after ETA")
            else:
                payload = {"job_type": job_type, "customer_name": customer, "etd": etd, "eta": eta, "remark": remark, "created_by": user.get("username")}
                job_no = create_shipment(payload)
                st.success(f"Created {job_no}")

def _list_view():
    rows = list_shipments()
    if not rows: return
    df = pd.DataFrame(rows)
    
    st.write("Edit Status directly in the table below:")
    edited_df = st.data_editor(df[["job_no", "status", "customer_name", "etd", "eta"]], 
                               hide_index=True, use_container_width=True)
    
    if st.button("💾 Save Batch Changes"):
        for _, row in edited_df.iterrows():
            update_shipment(row["job_no"], {"status": row["status"]})
        st.success("Batch updated!")

def _edit_view(user):
    rows = list_shipments()
    if not rows: return
    job_no = st.selectbox("Select Job to Edit", [r["job_no"] for r in rows])
    shipment = get_shipment(job_no)
    
    with st.form("edit_shipment_form"):
        status = st.selectbox("Status", STATUS_OPTIONS, index=STATUS_OPTIONS.index(shipment.get("status", "Proceed")))
        bl_no = st.text_input("B/L No", value=shipment.get("bl_no", ""))
        
        if st.form_submit_button("💾 Update"):
            if status == "Closed" and not bl_no:
                st.error("Please enter B/L No before Closing")
            else:
                update_shipment(job_no, {"status": status, "bl_no": bl_no, "updated_by": user.get("username")})
                st.success("Updated!")
                st.rerun()

# --- DB FUNCTIONS ---
def create_shipment(data):
    job_no = generate_job_number(data.get("job_type", "SE"))
    data["job_no"] = job_no
    cols = ",".join(data.keys())
    vals = tuple(data.values())
    with get_connection() as conn:
        conn.execute(f"INSERT INTO shipments ({cols}) VALUES ({','.join(['?']*len(data))})", vals)
        conn.commit()
    return job_no

def list_shipments():
    with get_connection() as conn:
        return [dict(r) for r in conn.execute("SELECT * FROM shipments ORDER BY created_at DESC").fetchall()]

def get_shipment(job_no):
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM shipments WHERE job_no=?", (job_no,)).fetchone()
        return dict(row) if row else {}

def update_shipment(job_no, data):
    sets = [f"{k}=?" for k in data.keys()]
    vals = list(data.values()) + [job_no]
    with get_connection() as conn:
        conn.execute(f"UPDATE shipments SET {', '.join(sets)}, updated_at=CURRENT_TIMESTAMP WHERE job_no=?", vals)
        conn.commit()