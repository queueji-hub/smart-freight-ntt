"""
Shipment / Job Control management.
Production-ready version
"""

from typing import List, Dict, Any, Optional
from datetime import date
import pandas as pd
import streamlit as st

from database.connection import get_connection
from config import JOB_TYPES

from managers.auth_manager import can_write
from managers.booking_manager import list_bookings
from managers.job_number import generate_job_number


STATUS_OPTIONS = ["Proceed", "Finished", "Closed", "Canceled"]

SIZE_OPTIONS = [
    "1x20'GP",
    "1x40'GP",
    "1x40'HC",
    "1x40'HQ",
    "1x20'OT",
    "1x40'OT",
    "1x20'FR",
    "Other",
]

CARGO_TYPES = ["", "FCL", "LCL", "AIR", "TRUCK"]


# =========================================================
# TABLE INIT
# =========================================================

def _ensure_table():
    """Ensure shipments table exists."""

    with get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS shipments (
                id SERIAL PRIMARY KEY,

                job_no TEXT UNIQUE NOT NULL,
                status TEXT DEFAULT 'Proceed',

                job_type TEXT,
                booking_no TEXT,

                customer_name TEXT,
                shipper TEXT,
                consignee TEXT,
                notify_party TEXT,

                cargo_type TEXT,
                commodity TEXT,

                carrier TEXT,
                m_vessel TEXT,
                feeder TEXT,

                pol TEXT,
                por TEXT,
                pod TEXT,
                final_destination TEXT,
                transhipment_port TEXT,

                container_no TEXT,
                seal_no TEXT,
                container_size TEXT,

                etd DATE,
                eta DATE,
                pick_up_date DATE,
                stuffing_date DATE,
                return_date DATE,

                closing_time TEXT,

                bl_no TEXT,
                invoice_no TEXT,
                dn_no TEXT,

                customer_paid INTEGER DEFAULT 0,

                remark TEXT,

                created_by TEXT,

                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        conn.commit()


# =========================================================
# MAIN RENDER
# =========================================================

def render():
    """Main page."""

    _ensure_table()

    user = st.session_state.get("user", {})
    role = user.get("role", "")
    can_edit = can_write(role, "shipment")

    st.title("📦 Shipment / Job Control")
    st.caption("Freight Forwarder Shipment Management")

    if can_edit:
        tabs = st.tabs([
            "➕ Create Shipment",
            "📋 Shipment List",
            "✏️ Edit Shipment",
        ])

        with tabs[0]:
            _create_form(user)

        with tabs[1]:
            _list_view()

        with tabs[2]:
            _edit_view()

    else:
        _list_view()


# =========================================================
# HELPERS
# =========================================================

def _parse_date(value):
    if not value:
        return None

    if isinstance(value, str):
        try:
            return date.fromisoformat(value)
        except:
            return None

    return value


def _clean_payload(data: Dict[str, Any]) -> Dict[str, Any]:
    """Remove empty values."""

    cleaned = {}

    for k, v in data.items():
        if v == "":
            cleaned[k] = None
        else:
            cleaned[k] = v

    return cleaned


# =========================================================
# CREATE FORM
# =========================================================

def _create_form(user):

    st.subheader("Create New Shipment")

    bookings = list_bookings()

    booking_options = [""] + [b.get("booking_no", "") for b in bookings]

    with st.form("create_shipment_form", clear_on_submit=True):

        col1, col2, col3 = st.columns(3)

        with col1:
            job_type = st.selectbox(
                "Job Type",
                JOB_TYPES,
            )

            booking_no = st.selectbox(
                "Booking No",
                booking_options,
            )

            status = st.selectbox(
                "Status",
                STATUS_OPTIONS,
                index=0,
            )

            cargo_type = st.selectbox(
                "Cargo Type",
                CARGO_TYPES,
            )

        with col2:

            customer_name = st.text_input("Customer")

            shipper = st.text_input("Shipper")

            consignee = st.text_input("Consignee")

            notify_party = st.text_input("Notify Party")

        with col3:

            carrier = st.text_input("Carrier")

            m_vessel = st.text_input("Mother Vessel")

            feeder = st.text_input("Feeder Vessel")

            commodity = st.text_input("Commodity")

        st.divider()

        col4, col5, col6 = st.columns(3)

        with col4:
            pol = st.text_input("POL")
            por = st.text_input("POR")
            pod = st.text_input("POD")

        with col5:
            final_destination = st.text_input("Final Destination")
            transhipment_port = st.text_input("Transhipment Port")

        with col6:
            container_no = st.text_input("Container No")
            seal_no = st.text_input("Seal No")

            container_size = st.selectbox(
                "Container Size",
                SIZE_OPTIONS,
            )

        st.divider()

        col7, col8, col9 = st.columns(3)

        with col7:
            etd = st.date_input("ETD", value=None)
            eta = st.date_input("ETA", value=None)

        with col8:
            pick_up_date = st.date_input("Pick Up Date", value=None)
            stuffing_date = st.date_input("Stuffing Date", value=None)

        with col9:
            return_date = st.date_input("Return Date", value=None)
            closing_time = st.text_input("Closing Time")

        st.divider()

        col10, col11 = st.columns(2)

        with col10:
            bl_no = st.text_input("B/L No")
            invoice_no = st.text_input("Invoice No")

        with col11:
            dn_no = st.text_input("D/N No")

            customer_paid = st.checkbox("Customer Paid")

        remark = st.text_area("Remark", height=120)

        submit = st.form_submit_button("✅ Create Shipment")

        if submit:

            payload = {
                "status": status,
                "job_type": job_type,
                "booking_no": booking_no,
                "customer_name": customer_name,
                "shipper": shipper,
                "consignee": consignee,
                "notify_party": notify_party,
                "cargo_type": cargo_type,
                "commodity": commodity,
                "carrier": carrier,
                "m_vessel": m_vessel,
                "feeder": feeder,
                "pol": pol,
                "por": por,
                "pod": pod,
                "final_destination": final_destination,
                "transhipment_port": transhipment_port,
                "container_no": container_no,
                "seal_no": seal_no,
                "container_size": container_size,
                "etd": etd,
                "eta": eta,
                "pick_up_date": pick_up_date,
                "stuffing_date": stuffing_date,
                "return_date": return_date,
                "closing_time": closing_time,
                "bl_no": bl_no,
                "invoice_no": invoice_no,
                "dn_no": dn_no,
                "customer_paid": 1 if customer_paid else 0,
                "remark": remark,
                "created_by": user.get("username", "system"),
            }

            payload = _clean_payload(payload)

            try:

                job_no = create_shipment(payload)

                st.success(f"Shipment created successfully : {job_no}")

            except Exception as e:
                st.error(f"Create failed : {e}")


# =========================================================
# LIST VIEW
# =========================================================

def _list_view():

    st.subheader("Shipment List")

    rows = list_shipments()

    if not rows:
        st.info("No shipment found.")
        return

    df = pd.DataFrame(rows)

    preferred_cols = [
        "job_no",
        "status",
        "job_type",
        "booking_no",
        "customer_name",
        "carrier",
        "pol",
        "pod",
        "etd",
        "eta",
        "container_no",
        "bl_no",
    ]

    existing_cols = [c for c in preferred_cols if c in df.columns]

    st.dataframe(
        df[existing_cols],
        use_container_width=True,
        hide_index=True,
    )


# =========================================================
# EDIT VIEW
# =========================================================

def _edit_view():

    st.subheader("Edit Shipment")

    rows = list_shipments()

    if not rows:
        st.info("No shipment found.")
        return

    job_nos = [r["job_no"] for r in rows]

    selected_job = st.selectbox(
        "Select Shipment",
        job_nos,
    )

    shipment = get_shipment(selected_job)

    if not shipment:
        st.warning("Shipment not found.")
        return

    with st.form("edit_shipment_form"):

        status = st.selectbox(
            "Status",
            STATUS_OPTIONS,
            index=STATUS_OPTIONS.index(
                shipment.get("status", "Proceed")
            )
        )

        customer_name = st.text_input(
            "Customer",
            value=shipment.get("customer_name", ""),
        )

        carrier = st.text_input(
            "Carrier",
            value=shipment.get("carrier", ""),
        )

        bl_no = st.text_input(
            "B/L No",
            value=shipment.get("bl_no", ""),
        )

        remark = st.text_area(
            "Remark",
            value=shipment.get("remark", ""),
            height=120,
        )

        col1, col2 = st.columns(2)

        with col1:
            update_btn = st.form_submit_button("💾 Update")

        with col2:
            delete_btn = st.form_submit_button("🗑 Delete")

        if update_btn:

            payload = {
                "status": status,
                "customer_name": customer_name,
                "carrier": carrier,
                "bl_no": bl_no,
                "remark": remark,
            }

            try:
                update_shipment(selected_job, payload)

                st.success("Shipment updated successfully.")
                st.rerun()

            except Exception as e:
                st.error(f"Update failed : {e}")

        if delete_btn:

            try:
                delete_shipment(selected_job)

                st.success("Shipment deleted.")
                st.rerun()

            except Exception as e:
                st.error(f"Delete failed : {e}")


# =========================================================
# CRUD
# =========================================================

def create_shipment(data: Dict[str, Any]) -> str:

    _ensure_table()

    job_no = generate_job_number(
        data.get("job_type", "SE")
    )

    data["job_no"] = job_no

    fields = list(data.keys())

    placeholders = ",".join(["%s"] * len(fields))

    columns = ",".join(fields)

    values = [data[f] for f in fields]

    sql = f"""
        INSERT INTO shipments ({columns})
        VALUES ({placeholders})
    """

    with get_connection() as conn:

        conn.execute(sql, tuple(values))

        conn.commit()

    return job_no


def list_shipments(
    job_type: str = None,
    status: str = None,
) -> List[Dict[str, Any]]:

    _ensure_table()

    sql = """
        SELECT *
        FROM shipments
        WHERE 1=1
    """

    params = []

    if job_type:
        sql += " AND job_type=%s"
        params.append(job_type)

    if status:
        sql += " AND status=%s"
        params.append(status)

    sql += " ORDER BY created_at DESC"

    with get_connection() as conn:

        rows = conn.execute(sql, tuple(params)).fetchall()

    return [dict(r) for r in rows]


def get_shipment(job_no: str) -> Optional[Dict[str, Any]]:

    _ensure_table()

    with get_connection() as conn:

        row = conn.execute(
            """
            SELECT *
            FROM shipments
            WHERE job_no=%s
            """,
            (job_no,),
        ).fetchone()

    return dict(row) if row else None


def update_shipment(
    job_no: str,
    data: Dict[str, Any],
) -> bool:

    _ensure_table()

    if not data:
        return False

    sets = [f"{k}=%s" for k in data.keys()]

    params = list(data.values())

    params.append(job_no)

    sql = f"""
        UPDATE shipments
        SET
            {", ".join(sets)},
            updated_at=CURRENT_TIMESTAMP
        WHERE job_no=%s
    """

    with get_connection() as conn:

        conn.execute(sql, tuple(params))

        conn.commit()

    return True


def delete_shipment(job_no: str) -> bool:

    _ensure_table()

    with get_connection() as conn:

        conn.execute(
            "DELETE FROM shipments WHERE job_no=%s",
            (job_no,),
        )

        conn.commit()

    return True


def clone_shipment(
    source_job_no: str
) -> Optional[str]:

    src = get_shipment(source_job_no)

    if not src:
        return None

    clone_data = {
        k: v
        for k, v in src.items()
        if k not in [
            "id",
            "job_no",
            "created_at",
            "updated_at",
            "invoice_no",
        ]
    }

    clone_data["status"] = "Proceed"

    clone_data["remark"] = (
        f"Cloned from {source_job_no}\n"
        + (src.get("remark") or "")
    )

    return create_shipment(clone_data)


# =========================================================
# DASHBOARD
# =========================================================

def get_dashboard_stats() -> Dict[str, Any]:

    _ensure_table()

    sql = """
        SELECT
            COUNT(*) as total,

            SUM(
                CASE
                    WHEN status='Proceed'
                    THEN 1
                    ELSE 0
                END
            ) as proceed,

            SUM(
                CASE
                    WHEN status='Finished'
                    THEN 1
                    ELSE 0
                END
            ) as finished,

            SUM(
                CASE
                    WHEN status='Closed'
                    THEN 1
                    ELSE 0
                END
            ) as closed,

            SUM(
                CASE
                    WHEN status='Canceled'
                    THEN 1
                    ELSE 0
                END
            ) as canceled

        FROM shipments
    """

    with get_connection() as conn:

        row = conn.execute(sql).fetchone()

    return {
        "total": row[0] or 0,
        "proceed": row[1] or 0,
        "finished": row[2] or 0,
        "closed": row[3] or 0,
        "canceled": row[4] or 0,
    }