import streamlit as st
import pandas as pd
from datetime import date

from database.connection import get_connection
from config import JOB_TYPES
from managers.auth_manager import can_write
from managers.job_number import generate_job_number

# =========================================================
# CONSTANTS
# =========================================================
STATUS_OPTIONS = ["Proceed", "Finished", "Closed", "Canceled"]
CARGO_TYPES = ["", "FCL", "LCL", "AIR", "TRUCK"]


# =========================================================
# DB INIT (POSTGRES SAFE)
# =========================================================
def _ensure_table():
    with get_connection() as conn:
        with conn.cursor() as cur:

            cur.execute("""
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

            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_shipments_job_no
                ON shipments(job_no);
            """)

        conn.commit()


# =========================================================
# RENDER
# =========================================================
def render():

    _ensure_table()

    user = st.session_state.get("user", {})
    role = user.get("role", "")
    can_edit = can_write(role, "shipment")

    st.title("📦 Shipment / Job Control")

    tabs = st.tabs(["➕ Create", "📋 List & Batch Edit", "✏️ Single Edit"])

    with tabs[0]:
        _create_form(user, can_edit)

    with tabs[1]:
        _list_view(can_edit)

    with tabs[2]:
        _edit_view(user, can_edit)


# =========================================================
# CREATE
# =========================================================
def _create_form(user, can_edit):

    if not can_edit:
        st.warning("Read-only access")
        return

    with st.form("create_shipment"):

        col1, col2 = st.columns(2)

        with col1:
            job_type = st.selectbox("Job Type", JOB_TYPES)
            customer = st.text_input("Customer *")

        with col2:
            cargo = st.selectbox("Cargo Type", CARGO_TYPES)
            etd = st.date_input("ETD", value=date.today())
            eta = st.date_input("ETA", value=date.today())

        remark = st.text_area("Remark")

        submitted = st.form_submit_button("✅ Create")

        if submitted:

            if not customer:
                st.error("Customer is required")
                return

            if etd and eta and etd > eta:
                st.error("ETD cannot be after ETA")
                return

            job_no = create_shipment({
                "job_type": job_type,
                "customer_name": customer,
                "cargo_type": cargo,
                "etd": etd,
                "eta": eta,
                "remark": remark,
                "created_by": user.get("username")
            })

            st.success(f"Created: {job_no}")


# =========================================================
# LIST
# =========================================================
def _list_view(can_edit):

    rows = list_shipments()

    if not rows:
        st.info("No shipments found")
        return

    df = pd.DataFrame(rows)

    st.subheader("Shipments")

    if can_edit:

        edited = st.data_editor(
            df[["job_no", "status", "customer_name", "etd", "eta"]],
            use_container_width=True,
            hide_index=True
        )

        if st.button("💾 Save Changes"):

            for _, r in edited.iterrows():
                update_shipment(
                    r["job_no"],
                    {"status": r["status"]}
                )

            st.success("Updated!")

    else:
        st.dataframe(df, use_container_width=True)


# =========================================================
# EDIT
# =========================================================
def _edit_view(user, can_edit):

    if not can_edit:
        st.warning("Read-only access")
        return

    rows = list_shipments()

    if not rows:
        st.info("No data")
        return

    job_no = st.selectbox(
        "Select Job",
        [r["job_no"] for r in rows]
    )

    shipment = get_shipment(job_no)

    with st.form("edit_form"):

        status = st.selectbox(
            "Status",
            STATUS_OPTIONS,
            index=STATUS_OPTIONS.index(
                shipment.get("status", "Proceed")
            )
        )

        bl_no = st.text_input(
            "B/L No",
            value=shipment.get("bl_no", "")
        )

        submitted = st.form_submit_button("💾 Update")

        if submitted:

            if status == "Closed" and not bl_no:
                st.error("BL No required before closing")
                return

            update_shipment(job_no, {
                "status": status,
                "bl_no": bl_no,
                "updated_by": user.get("username")
            })

            st.success("Updated!")
            st.rerun()


# =========================================================
# DB FUNCTIONS (POSTGRES FIXED)
# =========================================================
def create_shipment(data):

    job_no = generate_job_number(data.get("job_type", "SE"))
    data["job_no"] = job_no

    cols = ",".join(data.keys())
    placeholders = ",".join(["%s"] * len(data))
    values = tuple(data.values())

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"""
                INSERT INTO shipments ({cols})
                VALUES ({placeholders})
                """,
                values
            )

        conn.commit()

    return job_no


def list_shipments():

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT * FROM shipments
                ORDER BY created_at DESC
            """)
            rows = cur.fetchall()

    return [dict(r) for r in rows]


def get_shipment(job_no):

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT * FROM shipments
                WHERE job_no = %s
            """, (job_no,))
            row = cur.fetchone()

    return dict(row) if row else {}


def update_shipment(job_no, data):

    sets = ", ".join([f"{k}=%s" for k in data.keys()])
    values = list(data.values()) + [job_no]

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"""
                UPDATE shipments
                SET {sets},
                    updated_at = CURRENT_TIMESTAMP
                WHERE job_no = %s
                """,
                values
            )

        conn.commit()