"""Production-facing company Bill of Lading workspace for Phase 30.

The screen mirrors the approved B/L form order: parties -> routing -> cargo ->
freight/terms -> issuance. One Shipment/Job is the consolidation parent and
can contain multiple company-issued B/Ls.
"""
from __future__ import annotations

import os
from datetime import date
from typing import Any, Dict, List
import pandas as pd
import streamlit as st

from managers.auth_manager import can_write
from managers.bl_consolidation_service import assemble_bl_document_payload
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


def _s(v: Any, default: str = "—") -> str:
    x = str(v or "").strip()
    return default if not x or x.lower() in {"none", "nan", "nat"} else x


def _d(v: Any) -> date:
    if isinstance(v, date):
        return v
    try:
        return date.fromisoformat(str(v)[:10])
    except Exception:
        return date.today()


def _pdf(bl: Dict[str, Any]) -> None:
    """Generate the official B/L from the persisted SSOT payload.

    Do not assemble a partial UI payload here: the PDF engine resolves the
    linked Job, Booking and container manifest from the B/L record itself.
    This keeps PDF output consistent with the production document engine.
    """
    bid = int(bl["id"])
    key = f"bl_v2_{bid}"
    if st.button("PDF", key=f"{key}_make", type="primary", width="stretch"):
        try:
            from pdf.bl_pdf import generate_bl_pdf
            path = generate_bl_pdf(bid)
            if not path or not os.path.exists(path):
                raise FileNotFoundError("B/L PDF generator returned no file.")
            with open(path, "rb") as fh:
                st.session_state[f"{key}_bytes"] = fh.read()
            st.session_state[f"{key}_name"] = os.path.basename(path)
        except Exception as exc:
            st.error(f"Unable to create B/L PDF: {exc}")
    if st.session_state.get(f"{key}_bytes"):
        st.download_button(
            "Download",
            st.session_state[f"{key}_bytes"],
            file_name=st.session_state.get(f"{key}_name", f"BL_{bid}.pdf"),
            mime="application/pdf",
            key=f"{key}_dl",
            width="stretch",
        )


def _consol_summary(rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    total_bl = len(rows)
    shippers = len({str(r.get("shipper") or "").strip().lower() for r in rows if str(r.get("shipper") or "").strip()})
    total_pkg = sum(float(r.get("package_qty") or 0) for r in rows)
    total_cbm = sum(float(r.get("measurement_cbm") or 0) for r in rows)
    c = st.columns(4)
    c[0].metric("B/Ls in Shipment", total_bl)
    c[1].metric("Shippers", shippers)
    c[2].metric("Packages", f"{total_pkg:,.0f}")
    c[3].metric("CBM", f"{total_cbm:,.3f}")


def _new(user: Dict[str, Any]) -> None:
    jobs = list_shipments(limit=200) or []
    jmap = {j.get("job_no"): j for j in jobs if j.get("job_no")}
    if not jmap:
        st.warning("No jobs available to issue B/L.")
        return
    section("Issue New Company B/L")
    with st.form("bl_v2_new"):
        job_no = st.selectbox("Choose Parent Shipment / Job", list(jmap))
        selected_job = jmap.get(job_no, {})
        st.caption(f"Carrier: {_s(selected_job.get('carrier'))} · POL: {_s(selected_job.get('pol'))} · POD: {_s(selected_job.get('pod'))}")
        issued = st.form_submit_button("Issue B/L", type="primary", width="stretch")
    if issued:
        try:
            bid = create_bl_from_job(job_no, user)
            st.session_state["bl_v2_selected"] = bid
            st.success(f"Company B/L issued for Job {job_no}.")
            st.rerun()
        except Exception as exc:
            st.error(f"Unable to issue B/L: {exc}")


def _edit(bl: Dict[str, Any]) -> None:
    bid = int(bl["id"])
    section("Edit Bill of Lading")
    with st.form(f"bl_edit_{bid}"):
        section("Parties & Contacts")
        a, b = st.columns(2)
        shipper = a.text_area("Shipper", _s(bl.get("shipper"), ""), height=85)
        consignee = b.text_area("Consignee", _s(bl.get("consignee"), ""), height=85)
        c, d = st.columns(2)
        notify = c.text_area("Notify Party", _s(bl.get("notify_party"), ""), height=75)
        agent = d.text_area("Delivery Agent", _s(bl.get("delivery_agent"), ""), height=75)

        section("Routing & Transport")
        a, b = st.columns(2)
        pre_carriage = a.text_input("Pre-Carriage by", _s(bl.get("pre_carriage_by"), ""))
        place_receipt = b.text_input("Place of Receipt", _s(bl.get("place_of_receipt"), ""))
        a, b = st.columns(2)
        vessel = a.text_input("Ocean Vessel", _s(bl.get("vessel"), ""))
        voyage = b.text_input("Voyage No.", _s(bl.get("voyage"), ""))
        a, b = st.columns(2)
        pol = a.text_input("Port of Loading", _s(bl.get("port_of_loading"), ""))
        pod = b.text_input("Port of Discharge", _s(bl.get("port_of_discharge"), ""))
        a, b = st.columns(2)
        place_delivery = a.text_input("Place of Delivery", _s(bl.get("place_of_delivery"), ""))
        final_destination = b.text_input("Final Destination (For The Merchant's Reference Only)", _s(bl.get("final_destination"), ""))

        section("Cargo & Manifest")
        marks = st.text_area("Marks and Numbers / Container & Seal Numbers", _s(bl.get("marks_numbers"), "N/M"), height=75)
        cargo_desc = st.text_area("Description of Packages and Goods / Packages Forwarded by Shipper", _s(bl.get("description_of_goods"), ""), height=100)
        a, b, c, d = st.columns(4)
        packages = a.number_input("No. of Packages", min_value=0, value=int(bl.get("package_qty") or 0))
        package_type = b.text_input("Package Type", _s(bl.get("package_type"), "PKGS"))
        gross = c.number_input("Gross Weight Kgs", min_value=0.0, value=float(bl.get("gross_weight") or 0), step=0.01)
        cbm = d.number_input("Measurement CBM", min_value=0.0, value=float(bl.get("measurement_cbm") or 0), step=0.001)
        hs_code = st.text_input("HS Code", _s(bl.get("hs_code"), ""))

        section("Freight & Issuance")
        a, b = st.columns(2)
        freight_term = a.selectbox("Freight", ["PREPAID", "COLLECT"], index=0 if str(bl.get("freight_term") or "PREPAID").upper() == "PREPAID" else 1)
        freight_payable = b.text_input("Freight payable at", _s(bl.get("freight_payable_at"), ""))
        a, b, c = st.columns(3)
        place_issue = a.text_input("Place of Issue", _s(bl.get("place_of_issue"), "BANGKOK, THAILAND"))
        bl_date = b.date_input("B/L Date", _d(bl.get("bl_date")))
        originals = c.number_input("Number of original B/Ls", min_value=0, value=int(bl.get("number_of_originals") or 3), step=1)
        remarks = st.text_area("Remarks", _s(bl.get("remarks"), ""))

        save = st.form_submit_button("Save B/L Data", type="primary", width="stretch")
    if save:
        try:
            update_bl(
                bid,
                {
                    "shipper": shipper.strip(),
                    "consignee": consignee.strip(),
                    "notify_party": notify.strip(),
                    "delivery_agent": agent.strip(),
                    "pre_carriage_by": pre_carriage.strip(),
                    "place_of_receipt": place_receipt.strip(),
                    "port_of_loading": pol.strip(),
                    "port_of_discharge": pod.strip(),
                    "place_of_delivery": place_delivery.strip(),
                    "final_destination": final_destination.strip(),
                    "vessel": vessel.strip() or None,
                    "voyage": voyage.strip() or None,
                    "marks_numbers": marks.strip(),
                    "package_qty": packages,
                    "package_type": package_type.strip(),
                    "description_of_goods": cargo_desc.strip(),
                    "gross_weight": gross,
                    "measurement_cbm": cbm,
                    "hs_code": hs_code.strip(),
                    "freight_term": freight_term,
                    "freight_payable_at": freight_payable.strip(),
                    "place_of_issue": place_issue.strip(),
                    "bl_date": bl_date.isoformat(),
                    "number_of_originals": originals,
                    "remarks": remarks.strip(),
                },
            )
            st.success("B/L updated.")
            st.rerun()
        except Exception as exc:
            st.error(f"Unable to modify B/L: {exc}")


def _preview(bl: Dict[str, Any]) -> None:
    section("Ocean Bill of Lading Preview")
    st.caption("Field layout mirrors the official Ocean Bill of Lading form (NATTAYAARAT CO., LTD.).")
    
    # Header & Parties
    p1, p2 = st.columns(2)
    with p1:
        st.markdown(f"**Shipper**\n\n{_s(bl.get('shipper'))}\n\n**Consignee**\n\n{_s(bl.get('consignee'))}\n\n**Notify Party**\n\n{_s(bl.get('notify_party'))}")
    with p2:
        st.markdown(f"**B/L No.** `{_s(bl.get('bl_no'))}`\n\n**For Delivery of Goods Please Apply to**\n\n{_s(bl.get('delivery_agent'))}")
        st.markdown(f"**Originals:** {_s(bl.get('number_of_originals'), '3 (THREE)')} · **Place & Date:** {_s(bl.get('place_of_issue'))}, {_s(bl.get('bl_date'))}")

    # Routing Grid
    st.markdown("##### Routing & Transport")
    st.dataframe(pd.DataFrame([{
        "Pre-Carriage by": _s(bl.get('pre_carriage_by')),
        "Place of Receipt": _s(bl.get('place_of_receipt')),
        "Ocean Vessel / Voyage No.": f"{_s(bl.get('vessel'))} {_s(bl.get('voyage'))}".strip() or "—",
        "Port of Loading": _s(bl.get('port_of_loading')),
        "Port of Discharge": _s(bl.get('port_of_discharge')),
        "Place of Delivery": _s(bl.get('place_of_delivery')),
        "Final Destination": _s(bl.get('final_destination')),
    }]), hide_index=True, width="stretch")

    # Cargo Grid
    st.markdown("##### Cargo Specifications & Manifest")
    st.dataframe(pd.DataFrame([{
        "Marks and Numbers / Container & Seal Numbers": _s(bl.get('marks_numbers')),
        "No. of Packages": f"{_s(bl.get('package_qty'), '0')} {_s(bl.get('package_type'), '')}",
        "Description of Packages and Goods": _s(bl.get('description_of_goods')),
        "Gross Weight Kgs": float(bl.get('gross_weight') or 0),
        "Measurement CBM": float(bl.get('measurement_cbm') or 0),
        "HS Code": _s(bl.get('hs_code')),
        "Freight": _s(bl.get('freight_term')),
        "Freight Payable At": _s(bl.get('freight_payable_at')),
    }]), hide_index=True, width="stretch")

    if bl.get("remarks") or bl.get("special_instructions"):
        st.markdown(f"**Remarks:** {_s(bl.get('remarks'), '')}  \n**Special Instructions:** {_s(bl.get('special_instructions'), '')}")


def render() -> None:
    page_header("bl", status_text="Online")
    user = st.session_state.get("user", {})
    can_edit = can_write(str(user.get("role", "")).lower(), "bl")
    rows = list_bls() or []

    a, b = st.columns([4, 1])
    query = a.text_input("Search", placeholder="B/L, Job, Shipper, Consignee, POL or POD", key="bl_v2_search")
    new = b.button("New B/L", type="primary", width="stretch") if can_edit else False

    if query.strip():
        rows = [r for r in rows if query.strip().lower() in str(r).lower()]

    section("B/L Consolidation Overview")
    _consol_summary(rows)

    section("B/L Ledger")
    st.dataframe(
        pd.DataFrame([
            {
                "B/L No.": _s(r.get("bl_no")),
                "Job": _s(r.get("job_no")),
                "Seq": r.get("consol_seq") or 1,
                "Shipper": _s(r.get("shipper")),
                "Consignee": _s(r.get("consignee")),
                "POL": _s(r.get("port_of_loading")),
                "POD": _s(r.get("port_of_discharge")),
                "Vessel / Voyage": f"{_s(r.get('vessel'))} / {_s(r.get('voyage'))}",
                "Status": _s(r.get("approval_status"), "Draft"),
            }
            for r in rows
        ]),
        hide_index=True,
        width="stretch",
    )

    if new:
        _new(user)

    ids = [int(r["id"]) for r in rows if r.get("id") is not None]
    if not ids:
        st.info("No B/L records found.")
        return

    labels = {int(r["id"]): f"{r.get('bl_no')} · {r.get('job_no')} (#{r.get('consol_seq', 1)}) · {r.get('approval_status', 'Draft')}" for r in rows if r.get("id") is not None}
    default = ids.index(st.session_state.get("bl_v2_selected")) if st.session_state.get("bl_v2_selected") in ids else 0
    selected = st.selectbox("Choose B/L", ids, index=default, format_func=lambda x: labels[x], key="bl_v2_selected_box")
    bl = get_bl(selected)
    if not bl:
        st.error("Selected B/L is no longer available.")
        return

    st.session_state["bl_v2_selected"] = selected
    status = _s(bl.get("approval_status"), "Draft")

    section("B/L Summary")
    m = st.columns(6)
    m[0].metric("B/L No.", _s(bl.get("bl_no")))
    m[1].metric("Job", _s(bl.get("job_no")))
    m[2].metric("Seq", bl.get("consol_seq") or 1)
    m[3].metric("POL", _s(bl.get("port_of_loading")))
    m[4].metric("POD", _s(bl.get("port_of_discharge")))
    m[5].metric("Status", status)

    section("Actions")
    a, b, c, d = st.columns([2, 1, 1, 1])
    with a:
        _pdf(bl)
    with b:
        if can_edit and status == "Draft" and st.button("Submit", key=f"bl_submit_{selected}", width="stretch"):
            try:
                submit_for_approval(selected, user)
                st.rerun()
            except Exception as exc:
                st.error(str(exc))
    with c:
        if can_approve("bl", user) and status == "Pending Approval" and st.button("Approve", key=f"bl_approve_{selected}", type="primary", width="stretch"):
            try:
                approve(selected, user)
                st.rerun()
            except Exception as exc:
                st.error(str(exc))
    with d:
        st.caption("PDF follows the approved Ocean B/L layout.")

    tabs = st.tabs(["B/L Data", "Document Preview", "Shipping Instruction (S/I)"])
    with tabs[0]:
        if can_edit and status in {"Draft", "Pending Approval"}:
            _edit(bl)
        else:
            _preview(bl)
    with tabs[1]:
        _preview(bl)
    with tabs[2]:
        section("Shipping Instruction (S/I) for Shipping Line")
        si_mode_choice = st.radio(
            "S/I Issuance Mode",
            ["Direct B/L (Direct Master B/L to Customer)", "Agent B/L (HBL Mode — Agent Shipper & Nattayaarat Consignee)"],
            index=1,
            key=f"bl_si_mode_choice_{selected}",
            horizontal=True
        )
        si_mode = "hbl" if "Agent B/L" in si_mode_choice else "direct"
        
        from managers.si_service import assemble_si_payload
        try:
            job_no = bl.get("job_no")
            si_data = assemble_si_payload(job_no, si_mode=si_mode)
            
            p_col1, p_col2 = st.columns(2)
            with p_col1:
                st.markdown(f"**Shipper (on MBL)**\n\n{_s(si_data.get('shipper'))}\n\n**Consignee (on MBL)**\n\n{_s(si_data.get('consignee'))}")
            with p_col2:
                st.markdown(f"**Notify Party**\n\n{_s(si_data.get('notify_party'))}\n\n**Carrier Booking No.** `{_s(si_data.get('carrier_booking_no'))}`\n\n**Mode:** `{si_data['si_mode_label']}`")
            
            si_key = f"bl_si_{selected}_{si_mode}"
            if st.button("Generate Shipping Instruction PDF", key=f"{si_key}_btn", type="primary"):
                from pdf.si_pdf import generate_si_pdf
                si_path = generate_si_pdf(si_data)
                if si_path and os.path.exists(si_path):
                    with open(si_path, "rb") as fh:
                        st.session_state[f"{si_key}_bytes"] = fh.read()
                    st.session_state[f"{si_key}_name"] = os.path.basename(si_path)
            
            if st.session_state.get(f"{si_key}_bytes"):
                st.download_button(
                    "Download Shipping Instruction PDF",
                    st.session_state[f"{si_key}_bytes"],
                    file_name=st.session_state.get(f"{si_key}_name", f"SI_{job_no}.pdf"),
                    mime="application/pdf",
                    key=f"{si_key}_dl",
                    type="primary"
                )
        except Exception as exc:
            st.error(f"Unable to load S/I: {exc}")
