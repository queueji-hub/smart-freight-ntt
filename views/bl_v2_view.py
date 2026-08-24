"""Professional company-issued B/L workspace.

UI order mirrors the approved NATTAYAARAT B/L form:
Parties -> Routing -> Cargo -> Freight/Terms -> Issuance.
One Shipment/Job is the consolidation parent and may contain multiple B/Ls.
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
from managers.master_data_crud_manager import list_parties, list_ports
from managers.shipment_manager import list_shipments
from pdf.bl_document_renderer import resolve_document_title
from ui.design_system import page_header, section


def _s(value: Any, default: str = "") -> str:
    if value is None:
        return default
    text = str(value).strip()
    return default if text.lower() in {"", "none", "nan", "nat"} else text


def _d(value: Any) -> date:
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value)[:10])
    except Exception:
        return date.today()


def _party_options() -> tuple[dict[int, str], dict[int, str]]:
    parties = list_parties(active_only=True) or []
    labels: dict[int, str] = {}
    values: dict[int, str] = {}
    for row in parties:
        if not row.get("id"):
            continue
        pid = int(row["id"])
        display = _s(row.get("display_name") or row.get("legal_name"), str(pid))
        labels[pid] = f"{_s(row.get('party_code'), '-----')} — {display}"
        values[pid] = display
    return labels, values


def _port_options() -> tuple[dict[int, str], dict[int, str]]:
    ports = list_ports(active_only=True) or []
    labels: dict[int, str] = {}
    values: dict[int, str] = {}
    for row in ports:
        if not row.get("id"):
            continue
        pid = int(row["id"])
        name = _s(row.get("port_name"))
        country = _s(row.get("country_name"))
        labels[pid] = f"{_s(row.get('port_code'), '-----')} — {name}, {country}".strip(", ")
        values[pid] = f"{name}, {country}".strip(", ")
    return labels, values


def _render_pdf(bl: Dict[str, Any]) -> None:
    """Generate the exact company B/L renderer from the validated manager payload."""
    bid = int(bl["id"])
    key = f"bl_pdf_{bid}"
    if st.button("PDF", key=f"{key}_make", type="primary", width="stretch"):
        try:
            payload = assemble_bl_document_payload(bid)
            from pdf.bl_document_renderer import generate_company_bl_pdf
            path = generate_company_bl_pdf(payload)
            if not path or not os.path.exists(path):
                raise FileNotFoundError("Company B/L renderer returned no file.")
            with open(path, "rb") as fh:
                st.session_state[f"{key}_bytes"] = fh.read()
                st.session_state[f"{key}_name"] = os.path.basename(path)
        except Exception as exc:
            st.error(f"Unable to create B/L PDF: {exc}")
    if st.session_state.get(f"{key}_bytes"):
        st.download_button(
            "Download B/L",
            st.session_state[f"{key}_bytes"],
            file_name=st.session_state.get(f"{key}_name", f"BL_{bid}.pdf"),
            mime="application/pdf",
            key=f"{key}_download",
            width="stretch",
        )


def _party_selector(label: str, current_text: str, party_labels: dict[int, str], party_values: dict[int, str], key: str):
    lookup = {value.strip().lower(): pid for pid, value in party_values.items() if value}
    current_id = lookup.get(_s(current_text).strip().lower())
    options = list(party_labels)
    if not options:
        return _s(current_text, "")
    selected = st.selectbox(
        label,
        options,
        index=options.index(current_id) if current_id in options else 0,
        format_func=lambda x: party_labels[x],
        key=key,
    )
    manual = st.checkbox("Manual document text", key=f"{key}_manual")
    if manual:
        return st.text_area(f"{label} — Manual", value=_s(current_text, ""), key=f"{key}_manual_value")
    return party_values.get(selected, _s(current_text, ""))


def _edit(bl: Dict[str, Any]) -> None:
    bid = int(bl["id"])
    party_labels, party_values = _party_options()
    port_labels, port_values = _port_options()
    section("Edit Bill of Lading")
    st.caption("The input sequence mirrors the official B/L document: Parties → Routing → Cargo → Freight → Issuance.")
    with st.form(f"bl_form_{bid}"):
        section("01 · Parties & Delivery")
        shipper = _party_selector("Shipper", bl.get("shipper"), party_labels, party_values, f"bl_shipper_{bid}")
        consignee = _party_selector("Consignee", bl.get("consignee"), party_labels, party_values, f"bl_consignee_{bid}")
        notify = _party_selector("Notify Party", bl.get("notify_party"), party_labels, party_values, f"bl_notify_{bid}")
        delivery_agent = st.text_area("For Delivery of Goods Please Apply to", _s(bl.get("delivery_agent"), ""), height=65)

        section("02 · Routing & Vessel")
        a, b = st.columns(2)
        pre_carriage = a.text_input("Pre-Carriage by", _s(bl.get("pre_carriage_by")))
        place_receipt = b.text_input("Place of Receipt", _s(bl.get("place_of_receipt")))
        a, b = st.columns(2)
        vessel = a.text_input("Ocean Vessel", _s(bl.get("vessel")))
        voyage = b.text_input("Voyage No.", _s(bl.get("voyage")))
        a, b = st.columns(2)
        pol_current = next((pid for pid, value in port_values.items() if value.lower() == _s(bl.get("port_of_loading")).lower()), None)
        pod_current = next((pid for pid, value in port_values.items() if value.lower() == _s(bl.get("port_of_discharge")).lower()), None)
        pol_choices = list(port_labels) or [None]
        pod_choices = list(port_labels) or [None]
        pol_id = a.selectbox("Port of Loading", pol_choices, index=pol_choices.index(pol_current) if pol_current in pol_choices else 0, format_func=lambda x: port_labels.get(x, "—"), key=f"bl_pol_{bid}")
        pod_id = b.selectbox("Port of Discharge", pod_choices, index=pod_choices.index(pod_current) if pod_current in pod_choices else 0, format_func=lambda x: port_labels.get(x, "—"), key=f"bl_pod_{bid}")
        a, b = st.columns(2)
        place_delivery = a.text_input("Place of Delivery", _s(bl.get("place_of_delivery")))
        final_destination = b.text_input("Final Destination (For The Merchant's Reference Only)", _s(bl.get("final_destination")))

        section("03 · Cargo & Manifest")
        marks = st.text_area("Marks and Numbers / Container & Seal Numbers", _s(bl.get("marks_numbers"), "N/M"), height=70)
        cargo_desc = st.text_area("Description of Packages and Goods / Packages Forwarded by Shipper", _s(bl.get("description_of_goods")), height=110)
        a, b, c, d = st.columns(4)
        packages = a.number_input("No. of Packages", min_value=0, value=int(bl.get("package_qty") or 0))
        package_type = b.text_input("Package Type", _s(bl.get("package_type"), "PKGS"))
        gross = c.number_input("Gross Weight Kgs", min_value=0.0, value=float(bl.get("gross_weight") or 0), step=0.01)
        cbm = d.number_input("Measurement CBM", min_value=0.0, value=float(bl.get("measurement_cbm") or 0), step=0.001)
        hs_code = st.text_input("HS Code", _s(bl.get("hs_code")))

        section("04 · Freight & Issuance")
        a, b = st.columns(2)
        freight_term = a.selectbox("Freight", ["PREPAID", "COLLECT"], index=0 if _s(bl.get("freight_term"), "PREPAID").upper() == "PREPAID" else 1)
        freight_payable = b.text_input("Freight payable at", _s(bl.get("freight_payable_at")))
        a, b, c = st.columns(3)
        place_issue = a.text_input("Place of Issue", _s(bl.get("place_of_issue"), "BANGKOK, THAILAND"))
        bl_date = b.date_input("B/L Date", _d(bl.get("bl_date")))
        originals = c.number_input("Number of original B/Ls", min_value=0, value=int(bl.get("number_of_originals") or 3), step=1)
        remarks = st.text_area("Remarks", _s(bl.get("remarks")))
        save = st.form_submit_button("Save B/L Data", type="primary", width="stretch")

    if save:
        if pol_id is None or pod_id is None:
            st.error("Port of Loading and Port of Discharge are required.")
            return
        try:
            update_bl(bid, {
                "shipper": shipper.strip(),
                "consignee": consignee.strip(),
                "notify_party": notify.strip(),
                "delivery_agent": delivery_agent.strip(),
                "pre_carriage_by": pre_carriage.strip(),
                "place_of_receipt": place_receipt.strip(),
                "port_of_loading": port_values.get(pol_id, _s(bl.get("port_of_loading"))),
                "port_of_discharge": port_values.get(pod_id, _s(bl.get("port_of_discharge"))),
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
            })
            st.success("B/L data updated.")
            st.rerun()
        except Exception as exc:
            st.error(f"Unable to update B/L: {exc}")


def _new(user: Dict[str, Any]) -> None:
    jobs = list_shipments(limit=200) or []
    job_map = {j.get("job_no"): j for j in jobs if j.get("job_no")}
    if not job_map:
        st.info("No Shipment / Job is available for B/L issuance.")
        return
    with st.form("bl_issue_form"):
        section("Issue New Company B/L")
        job_no = st.selectbox("Parent Shipment / Job", list(job_map), key="bl_new_job")
        job = job_map[job_no]
        st.info(
            f"Carrier: {_s(job.get('carrier'))} · Vessel/Voyage: {_s(job.get('vessel'))} / {_s(job.get('voyage'))} · "
            f"Mother Vessel: {_s(job.get('mother_vessel'))} · POL/POD: {_s(job.get('pol'))} / {_s(job.get('pod'))}"
        )
        issue = st.form_submit_button("Issue Draft B/L", type="primary", width="stretch")
    if issue:
        try:
            bid = create_bl_from_job(job_no, user)
            st.session_state["bl_selected"] = int(bid)
            st.success(f"Draft B/L created for {job_no}.")
            st.rerun()
        except Exception as exc:
            st.error(f"Unable to issue B/L: {exc}")


def _preview(bl: Dict[str, Any]) -> None:
    job = {}
    if bl.get("job_no"):
        try:
            from managers.shipment_manager import get_shipment
            job = get_shipment(bl.get("job_no")) or {}
        except Exception:
            pass
    title = resolve_document_title(bl=bl, job=job)
    section(f"{title.title()} Preview")
    st.caption("Preview uses the same data order and document semantics as the PDF renderer.")
    a, b = st.columns([2, 1])
    with a:
        st.markdown(f"**Shipper**\n\n{_s(bl.get('shipper'))}\n\n**Consignee**\n\n{_s(bl.get('consignee'))}\n\n**Notify Party**\n\n{_s(bl.get('notify_party'))}")
    with b:
        st.markdown(f"**B/L No.** `{_s(bl.get('bl_no'))}`\n\n**For Delivery of Goods Please Apply to**\n\n{_s(bl.get('delivery_agent'))}\n\n**Originals:** {_s(bl.get('number_of_originals'), '3')}")

    routing = pd.DataFrame([{
        "Pre-Carriage by": _s(bl.get("pre_carriage_by")),
        "Place of Receipt": _s(bl.get("place_of_receipt")),
        "Ocean Vessel / Voyage No.": f"{_s(bl.get('vessel'))} {_s(bl.get('voyage'))}".strip(),
        "Port of Loading": _s(bl.get("port_of_loading")),
        "Port of Discharge": _s(bl.get("port_of_discharge")),
        "Place of Delivery": _s(bl.get("place_of_delivery")),
        "Final Destination": _s(bl.get("final_destination")),
    }])
    st.dataframe(routing, hide_index=True, width="stretch")

    cargo = pd.DataFrame([{
        "Marks / Container / Seal": _s(bl.get("marks_numbers")),
        "Packages": f"{_s(bl.get('package_qty'), '0')} {_s(bl.get('package_type'), '')}".strip(),
        "Description": _s(bl.get("description_of_goods")),
        "Gross Weight Kgs": float(bl.get("gross_weight") or 0),
        "Measurement CBM": float(bl.get("measurement_cbm") or 0),
        "HS Code": _s(bl.get("hs_code")),
        "Freight": _s(bl.get("freight_term"), "PREPAID"),
        "Freight Payable At": _s(bl.get("freight_payable_at")),
    }])
    st.dataframe(cargo, hide_index=True, width="stretch")


def render() -> None:
    page_header("bl", status_text="Online")
    user = st.session_state.get("user", {})
    can_edit = can_write(str(user.get("role", "")).lower(), "bl")
    rows = list_bls() or []

    a, b = st.columns([4, 1])
    query = a.text_input("Search B/L", placeholder="B/L, Job, Shipper, Consignee, POL, POD, Vessel or Voyage", key="bl_search")
    if b.button("New B/L", type="primary", width="stretch") and can_edit:
        st.session_state["bl_new"] = True

    if query.strip():
        q = query.strip().lower()
        rows = [r for r in rows if q in str(r).lower()]

    section("Consolidation Overview")
    by_job: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        by_job.setdefault(_s(row.get("job_no"), "—"), []).append(row)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("B/Ls", len(rows))
    c2.metric("Shipments", len(by_job))
    c3.metric("Shippers", len({_s(r.get('shipper')).lower() for r in rows if _s(r.get('shipper'))}))
    c4.metric("CBM", f"{sum(float(r.get('measurement_cbm') or 0) for r in rows):,.3f}")

    section("B/L Register")
    st.dataframe(pd.DataFrame([{
        "B/L No.": _s(r.get("bl_no")),
        "Job": _s(r.get("job_no")),
        "Consol Seq": r.get("consol_seq") or 1,
        "Shipper": _s(r.get("shipper")),
        "Consignee": _s(r.get("consignee")),
        "Vessel / Voyage": f"{_s(r.get('vessel'))} / {_s(r.get('voyage'))}".strip(" /"),
        "POL": _s(r.get("port_of_loading")),
        "POD": _s(r.get("port_of_discharge")),
        "Status": _s(r.get("approval_status"), "Draft"),
    } for r in rows]), hide_index=True, width="stretch")

    if st.session_state.get("bl_new") and can_edit:
        _new(user)
        if st.button("Close New B/L", key="bl_new_close"):
            st.session_state.pop("bl_new", None)
            st.rerun()
        return

    ids = [int(r["id"]) for r in rows if r.get("id") is not None]
    if not ids:
        st.info("No B/L records found.")
        return
    labels = {int(r["id"]): f"{_s(r.get('bl_no'))} · {_s(r.get('job_no'))} · Seq {r.get('consol_seq') or 1}" for r in rows if r.get("id") is not None}
    selected_default = st.session_state.get("bl_selected") if st.session_state.get("bl_selected") in ids else ids[0]
    selected = st.selectbox("Select B/L", ids, index=ids.index(selected_default), format_func=lambda x: labels[x], key="bl_selected_box")
    bl = get_bl(int(selected))
    if not bl:
        st.error("Selected B/L is unavailable.")
        return

    status = _s(bl.get("approval_status"), "Draft")
    section("Document Actions")
    a, b, c, d = st.columns([2, 1, 1, 1])
    with a:
        _render_pdf(bl)
    with b:
        if can_edit and status == "Draft" and st.button("Submit", key=f"bl_submit_{selected}", width="stretch"):
            try:
                submit_for_approval(int(selected), user)
                st.rerun()
            except Exception as exc:
                st.error(str(exc))
    with c:
        if can_approve("bl", user) and status == "Pending Approval" and st.button("Approve", key=f"bl_approve_{selected}", type="primary", width="stretch"):
            try:
                approve(int(selected), user)
                st.rerun()
            except Exception as exc:
                st.error(str(exc))
    with d:
        if can_edit and st.button("Edit", key=f"bl_edit_{selected}", width="stretch"):
            st.session_state["bl_edit"] = int(selected)
            st.rerun()

    if can_edit and st.session_state.get("bl_edit") == int(selected) and status == "Draft":
        _edit(bl)

    _preview(bl)
