"""Production-facing company Bill of Lading workspace for Phase 30.

The screen mirrors the approved B/L form order: parties -> routing -> cargo ->
freight/terms -> issuance. One Shipment/Job is the consolidation parent and
can contain multiple company-issued B/Ls.
"""
from __future__ import annotations

import os
from datetime import date
from typing import Any, Dict

import pandas as pd
import streamlit as st

from managers.auth_manager import can_write
from managers.bl_consolidation_service import assemble_bl_document_payload
from managers.bl_workflow_service import (
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


def _safe_date_for_ui(value: Any):
    if not value:
        return None
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value)[:10])
    except Exception:
        return None


def _pdf_action(bl: Dict[str, Any]) -> None:
    bl_id = int(bl["id"])
    key = f"bl_v2_{bl_id}"
    if st.button("PDF", key=f"{key}_prepare", type="primary", width="stretch"):
        try:
            from pdf.bl_document_renderer import generate_company_bl_pdf
            payload = assemble_bl_document_payload(bl_id)
            output = generate_company_bl_pdf(payload)
            if not output or not os.path.exists(output):
                raise FileNotFoundError("B/L PDF renderer did not return a valid file.")
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
            file_name=st.session_state.get(f"{key}_name", f"{bl.get('bl_no', bl_id)}.pdf"),
            mime="application/pdf",
            key=f"{key}_download",
            width="stretch",
        )


def _new_form(user: Dict[str, Any]) -> None:
    jobs = list_shipments(limit=200) or []
    job_options = [j.get("job_no") for j in jobs if j.get("job_no")]
    if not job_options:
        st.info("Create a Job first before issuing a B/L.")
        return

    section("Issue New B/L")
    st.caption("One Shipment can contain multiple company B/Ls for consolidation.")
    with st.form("bl_v2_new"):
        job_no = st.selectbox("Shipment / Job", job_options)
        submit = st.form_submit_button("Issue New B/L", type="primary", width="stretch")

    if submit:
        try:
            new_id = create_bl_from_job(job_no, user)
            st.session_state["bl_v2_selected"] = new_id
            st.success("B/L created as Draft.")
            st.rerun()
        except Exception as exc:
            st.error(f"Unable to create B/L: {exc}")


def _edit_form(bl: Dict[str, Any]) -> None:
    """Edit screen laid out in the same order as the approved BL workbook form."""
    bl_id = int(bl["id"])
    with st.expander("B/L Form", expanded=True):
        with st.form(f"bl_v2_edit_{bl_id}"):
            section("Parties")
            p1, p2 = st.columns(2)
            shipper = p1.text_area("Shipper", _s(bl.get("shipper"), ""), height=120)
            consignee = p2.text_area("Consignee", _s(bl.get("consignee"), ""), height=120)
            p3, p4 = st.columns(2)
            notify = p3.text_area("Notify Party", _s(bl.get("notify_party") or "SAME AS CONSIGNEE", ""), height=100)
            delivery_agent = p4.text_area("For Delivery of Goods Please Apply to", _s(bl.get("delivery_agent") or bl.get("place_of_delivery"), ""), height=100)

            section("Routing")
            r1, r2 = st.columns(2)
            pre_carriage = r1.text_input("Pre-Carriage by", _s(bl.get("pre_carriage_by"), ""))
            place_receipt = r2.text_input("Place of Receipt", _s(bl.get("place_of_receipt"), ""))
            r3, r4 = st.columns(2)
            vessel = r3.text_input("Ocean Vessel", _s(bl.get("vessel"), ""))
            voyage = r4.text_input("Voyage No.", _s(bl.get("voyage"), ""))
            r5, r6 = st.columns(2)
            pol = r5.text_input("Port of Loading", _s(bl.get("port_of_loading"), ""))
            pod = r6.text_input("Port of Discharge", _s(bl.get("port_of_discharge"), ""))
            r7, r8 = st.columns(2)
            place_delivery = r7.text_input("Place of Delivery", _s(bl.get("place_of_delivery"), ""))
            final_destination = r8.text_input("Final Destination (For The Merchant's Reference Only)", _s(bl.get("final_destination"), ""))

            section("Cargo")
            c1, c2, c3 = st.columns(3)
            marks = c1.text_area("Marks and Numbers / Container & Seal Numbers", _s(bl.get("marks_numbers"), ""), height=90)
            packages = c2.number_input("No. of Packages", min_value=0, value=int(bl.get("package_qty") or 0), step=1)
            package_type = c3.text_input("Package Type", _s(bl.get("package_type"), ""))
            cargo_desc = st.text_area("Description of Packages and Goods / Packages Forwarded by Shipper", _s(bl.get("description_of_goods"), ""), height=120)
            g1, g2 = st.columns(2)
            gross = g1.number_input("Gross Weight Kgs", min_value=0.0, value=float(bl.get("gross_weight") or 0), step=0.01)
            cbm = g2.number_input("Measurement CBM", min_value=0.0, value=float(bl.get("measurement_cbm") or 0), step=0.001)
            hs_code = st.text_input("HS CODE", _s(bl.get("hs_code"), ""))

            section("Freight and Disbursements")
            f1, f2, f3 = st.columns(3)
            freight_term = f1.selectbox("Freight", ["PREPAID", "COLLECT"], index=0 if str(bl.get("freight_term") or "PREPAID").upper() == "PREPAID" else 1)
            freight_payable = f2.text_input("Freight payable at", _s(bl.get("freight_payable_at"), ""))
            f3.text_input("Rate at KGS/Tons", "")

            section("Issuance")
            i1, i2, i3 = st.columns(3)
            place_issue = i1.text_input("Place of Issue", _s(bl.get("place_of_issue"), "THAILAND"))
            bl_date = i2.date_input("Place and date of issue", value=_safe_date_for_ui(bl.get("bl_date")) or date.today())
            originals = i3.number_input("Number of original B/Ls", min_value=1, value=int(bl.get("number_of_originals") or 3), step=1)
            remarks = st.text_area("Additional Clauses / Remarks", _s(bl.get("remarks") or bl.get("special_instructions"), ""), height=80)

            save = st.form_submit_button("Save B/L", type="primary", width="stretch")

        if save:
            try:
                update_bl(
                    bl_id,
                    {
                        "shipper": shipper.strip(),
                        "consignee": consignee.strip(),
                        "notify_party": notify.strip(),
                        "delivery_agent": delivery_agent.strip(),
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
                        "bl_date": bl_date,
                        "number_of_originals": originals,
                        "remarks": remarks.strip(),
                    },
                )
                st.success("B/L updated.")
                st.rerun()
            except Exception as exc:
                st.error(f"Unable to update B/L: {exc}")


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
            "Shipment": _s(r.get("job_no")),
            "Consol Seq": _s(r.get("consol_seq"), "1"),
            "Shipper": _s(r.get("shipper")),
            "Consignee": _s(r.get("consignee")),
            "POL": _s(r.get("port_of_loading"), "—"),
            "POD": _s(r.get("port_of_discharge"), "—"),
            "Vessel / Voyage": f"{_s(r.get('vessel'), '—')} / {_s(r.get('voyage'), '—')}",
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

    labels = {int(r["id"]): f"{r.get('bl_no')} · {r.get('job_no')} · {r.get('shipper') or 'Shipper pending'}" for r in rows if r.get("id") is not None}
    default = ids.index(st.session_state.get("bl_v2_selected")) if st.session_state.get("bl_v2_selected") in ids else 0
    selected_id = st.selectbox("Select B/L", ids, index=default, format_func=lambda x: labels[x], key="bl_v2_selected_box")
    bl = get_bl(selected_id)
    if not bl:
        st.error("Selected B/L is no longer available.")
        return

    st.session_state["bl_v2_selected"] = selected_id
    approval_status = _s(bl.get("approval_status"), "Draft")
    shipment_bls = list_bls(bl.get("job_no"))

    section("Consolidation")
    st.caption(f"Shipment {_s(bl.get('job_no'))} · multiple company B/Ls can share this shipment.")
    _consol_summary(shipment_bls)

    section("B/L Summary")
    summary = st.columns(5)
    summary[0].metric("B/L No.", _s(bl.get("bl_no")))
    summary[1].metric("Shipment", _s(bl.get("job_no")))
    summary[2].metric("Consol Seq", _s(bl.get("consol_seq"), "1"))
    summary[3].metric("Vessel", _s(bl.get("vessel") or bl.get("mother_vessel")))
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
        st.caption("Official PDF after approval.")

    section("B/L Form Preview")
    preview = st.columns(2)
    with preview[0]:
        st.markdown(f"**Shipper**\n\n{_s(bl.get('shipper'))}")
        st.markdown(f"**Consignee**\n\n{_s(bl.get('consignee'))}")
        st.markdown(f"**Notify Party**\n\n{_s(bl.get('notify_party'), 'SAME AS CONSIGNEE')}")
    with preview[1]:
        st.markdown(f"**B/L No.**\n\n{_s(bl.get('bl_no'))}")
        st.markdown(f"**Ocean Vessel/Voyage No.**\n\n{_s(bl.get('vessel') or bl.get('mother_vessel'))} / {_s(bl.get('voyage'))}")
        st.markdown(f"**Port of Loading / Port of Discharge**\n\n{_s(bl.get('port_of_loading'))} / {_s(bl.get('port_of_discharge'))}")

    if can_edit and approval_status in {"Draft", "Pending Approval"}:
        _edit_form(bl)
