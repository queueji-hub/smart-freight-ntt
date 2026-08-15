"""Production-facing B/L workspace for Phase 30.

Keeps the screen focused on Job-derived B/L data, approval, editing and PDF output.
"""
from __future__ import annotations

import os
from datetime import date
from typing import Any, Dict

import pandas as pd
import streamlit as st

from managers.auth_manager import can_write
from managers.bl_workflow_service import (
    BL_TYPES,
    approve,
    create_bl_from_job,
    get_bl,
    list_bls,
    submit_for_approval,
    update_bl,
)
from managers.document_approval_manager import can_approve
from managers.shipment_manager import list_shipments
from ui.design_system import page_header, section


def _s(value: Any, default: str = "—") -> str:
    text = str(value or "").strip()
    return default if not text or text.lower() in {"none", "nan", "nat"} else text


def _pdf_action(bl: Dict[str, Any]) -> None:
    bl_id = int(bl["id"])
    key = f"bl_v2_{bl_id}"
    if st.button("PDF", key=f"{key}_prepare", type="primary", width="stretch"):
        try:
            from pdf.bl_pdf import generate_bl_pdf
            payload = {
                "bl": {**bl, "approval_status": bl.get("approval_status", "Draft"), "status": bl.get("approval_status", bl.get("status", "Draft"))},
                "job": {},
                "booking": {},
                "containers": [],
            }
            output = generate_bl_pdf(payload)
            if not output or not os.path.exists(output):
                raise FileNotFoundError("B/L PDF generator did not return a valid file.")
            with open(output, "rb") as fh:
                st.session_state[f"{key}_bytes"] = fh.read()
            st.session_state[f"{key}_name"] = os.path.basename(output)
        except Exception as exc:
            st.error(f"Unable to create B/L PDF: {exc}")

    pdf_bytes = st.session_state.get(f"{key}_bytes")
    if pdf_bytes:
        st.download_button(
            "Download",
            pdf_bytes,
            file_name=st.session_state.get(f"{key}_name", f"BL_{bl_id}.pdf"),
            mime="application/pdf",
            key=f"{key}_download",
            width="stretch",
        )


def _new_form(user: Dict[str, Any]) -> None:
    jobs = list_shipments(limit=200) or []
    job_options = [j.get("job_no") for j in jobs if j.get("job_no")]
    if not job_options:
        st.info("Create a Job first before creating a B/L.")
        return

    section("New B/L")
    with st.form("bl_v2_new"):
        job_no = st.selectbox("Job", job_options)
        bl_type = st.selectbox("B/L Type", list(BL_TYPES))
        submit = st.form_submit_button("Create B/L", type="primary", width="stretch")

    if submit:
        try:
            new_id = create_bl_from_job(job_no, bl_type, user)
            st.session_state["bl_v2_selected"] = new_id
            st.success("B/L created as Draft.")
            st.rerun()
        except Exception as exc:
            st.error(f"Unable to create B/L: {exc}")


def _edit_form(bl: Dict[str, Any]) -> None:
    bl_id = int(bl["id"])
    with st.expander("Edit B/L", expanded=True):
        with st.form(f"bl_v2_edit_{bl_id}"):
            c1, c2 = st.columns(2)
            shipper = c1.text_area("Shipper", _s(bl.get("shipper"), ""))
            consignee = c2.text_area("Consignee", _s(bl.get("consignee"), ""))
            c3, c4, c5 = st.columns(3)
            pol = c3.text_input("POL", _s(bl.get("port_of_loading"), ""))
            pod = c4.text_input("POD", _s(bl.get("port_of_discharge"), ""))
            vessel = c5.text_input("Vessel", _s(bl.get("vessel"), ""))
            c6, c7, c8 = st.columns(3)
            voyage = c6.text_input("Voyage", _s(bl.get("voyage"), ""))
            packages = c7.number_input("Packages", min_value=0, value=int(bl.get("package_qty") or 0), step=1)
            gross = c8.number_input("Gross Weight (KG)", min_value=0.0, value=float(bl.get("gross_weight") or 0), step=0.01)
            cbm = st.number_input("Measurement (CBM)", min_value=0.0, value=float(bl.get("measurement_cbm") or 0), step=0.01)
            goods = st.text_area("Description of Goods", _s(bl.get("description_of_goods"), ""))
            save = st.form_submit_button("Save Changes", type="primary", width="stretch")

        if save:
            try:
                update_bl(
                    bl_id,
                    {
                        "shipper": shipper.strip(),
                        "consignee": consignee.strip(),
                        "port_of_loading": pol.strip(),
                        "port_of_discharge": pod.strip(),
                        "vessel": vessel.strip() or None,
                        "voyage": voyage.strip() or None,
                        "package_qty": packages,
                        "gross_weight": gross,
                        "measurement_cbm": cbm,
                        "description_of_goods": goods.strip(),
                    },
                )
                st.success("B/L updated.")
                st.rerun()
            except Exception as exc:
                st.error(f"Unable to update B/L: {exc}")


def render() -> None:
    page_header("bl", status_text="Online")
    user = st.session_state.get("user", {})
    role = str(user.get("role", "")).lower()
    can_edit = can_write(role, "bl")

    rows = list_bls() or []
    top1, top2 = st.columns([4, 1])
    with top1:
        query = st.text_input("Search", placeholder="B/L, Job, Shipper, Consignee, POL or POD", key="bl_v2_search")
    with top2:
        new_bl = st.button("New B/L", type="primary", width="stretch") if can_edit else False

    if query.strip():
        q = query.strip().lower()
        rows = [r for r in rows if q in str(r).lower()]

    section("B/L Ledger")
    display = pd.DataFrame([
        {
            "B/L No.": _s(r.get("bl_no")),
            "Type": _s(r.get("bl_type")),
            "Job": _s(r.get("job_no")),
            "Customer": _s(r.get("customer_name"), "—"),
            "POL": _s(r.get("port_of_loading"), "—"),
            "POD": _s(r.get("port_of_discharge"), "—"),
            "Vessel": _s(r.get("vessel"), "—"),
            "Voyage": _s(r.get("voyage"), "—"),
            "Approval": _s(r.get("approval_status"), "Draft"),
        }
        for r in rows
    ])
    st.dataframe(display, hide_index=True, width="stretch")

    if new_bl:
        _new_form(user)

    ids = [int(r["id"]) for r in rows if r.get("id") is not None]
    if not ids:
        st.info("No B/L records found.")
        return

    labels = {int(r["id"]): f"{r.get('bl_no')} · {r.get('bl_type')} · {r.get('approval_status', 'Draft')}" for r in rows if r.get("id") is not None}
    default = ids.index(st.session_state.get("bl_v2_selected")) if st.session_state.get("bl_v2_selected") in ids else 0
    selected_id = st.selectbox("Select B/L", ids, index=default, format_func=lambda x: labels[x], key="bl_v2_selected_box")
    bl = get_bl(selected_id)
    if not bl:
        st.error("Selected B/L is no longer available.")
        return

    st.session_state["bl_v2_selected"] = selected_id
    approval_status = _s(bl.get("approval_status"), "Draft")

    section("B/L Summary")
    summary = st.columns(5)
    summary[0].metric("B/L No.", _s(bl.get("bl_no")))
    summary[1].metric("Type", _s(bl.get("bl_type")))
    summary[2].metric("Job", _s(bl.get("job_no")))
    summary[3].metric("Vessel", _s(bl.get("vessel")))
    summary[4].metric("Status", approval_status)

    section("Actions")
    actions = st.columns([2, 1, 1, 1])
    with actions[0]:
        _pdf_action(bl)
    with actions[1]:
        if can_edit and approval_status == "Draft":
            if st.button("Submit", key=f"bl_v2_submit_{selected_id}", width="stretch"):
                try:
                    submit_for_approval(selected_id, user)
                    st.rerun()
                except Exception as exc:
                    st.error(str(exc))
    with actions[2]:
        if can_approve("bl", user) and approval_status == "Pending Approval":
            if st.button("Approve", key=f"bl_v2_approve_{selected_id}", type="primary", width="stretch"):
                try:
                    approve(selected_id, user)
                    st.rerun()
                except Exception as exc:
                    st.error(str(exc))
    with actions[3]:
        st.caption("Official PDF only after approval.")

    section("Routing & Parties")
    info = st.columns(4)
    info[0].write(f"**Shipper**\n\n{_s(bl.get('shipper'))}")
    info[1].write(f"**Consignee**\n\n{_s(bl.get('consignee'))}")
    info[2].write(f"**POL / POD**\n\n{_s(bl.get('port_of_loading'))} / {_s(bl.get('port_of_discharge'))}")
    info[3].write(f"**Vessel / Voyage**\n\n{_s(bl.get('vessel'))} / {_s(bl.get('voyage'))}")

    if can_edit and approval_status in {"Draft", "Pending Approval"}:
        _edit_form(bl)
