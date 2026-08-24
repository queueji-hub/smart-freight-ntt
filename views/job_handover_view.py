"""Sales handover workspace: convert approved quotations into Jobs without re-keying."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from managers.auth_manager import can_write
from managers.job_handover_service import handover_quotation_to_job
from managers.quotation_manager import list_quotations
from ui.design_system import page_header, section


def render() -> None:
    page_header("handover", status_text="Online")
    user = st.session_state.get("user", {})
    role = str(user.get("role", "")).lower()
    if not can_write(role, "shipment"):
        st.warning("Job handover is restricted to authorized Sales and Operations users.")
        return

    rows = list_quotations() or []
    approved = [
        r for r in rows
        if str(r.get("approval_status") or "").strip().lower() in {"approved", "accepted"}
        or str(r.get("status") or "").strip().lower() in {"approved", "accepted"}
    ]

    section("Approved Quotations")
    st.dataframe(
        pd.DataFrame([
            {
                "Quotation No.": r.get("quotation_no"),
                "Issue Date": r.get("quotation_date"),
                "Customer": r.get("customer_name"),
                "POL": r.get("pol"),
                "POD": r.get("pod"),
                "Status": r.get("approval_status") or r.get("status"),
            }
            for r in approved
        ]),
        hide_index=True,
        width="stretch",
    )

    if not approved:
        st.info("No approved quotations are ready for Operations handover.")
        return

    options = [str(r.get("quotation_no")) for r in approved if r.get("quotation_no")]
    selected = st.selectbox("Quotation", options, key="handover_quotation")
    record = next((r for r in approved if str(r.get("quotation_no")) == selected), approved[0])

    section("Handover Preview")
    a, b, c = st.columns(3)
    with a:
        st.metric("Customer", record.get("customer_name") or "—")
    with b:
        st.metric("Route", f"{record.get('pol') or '—'} → {record.get('pod') or '—'}")
    with c:
        st.metric("Service", record.get("service_type") or record.get("job_type") or "—")

    st.caption("The approved quotation becomes the operational Job reference. Customer, sales, route and commercial context are carried forward without re-keying.")
    if st.button("Create Job from Approved Quotation", type="primary", width="stretch", key=f"handover_{selected}"):
        try:
            job_no = handover_quotation_to_job(selected, user)
            st.success(f"Job {job_no} is ready for Operations.")
        except Exception as exc:
            st.error(str(exc))
