"""Bill of Lading workspace — Phase 30 UI standard.

Compact document-ledger layout with consistent PDF / Edit / Duplicate actions.
Duplicate always creates a fresh Draft B/L number and never overwrites the source.
"""

import os
import pandas as pd
import streamlit as st

from managers.auth_manager import can_write
from managers.bl_manager import (
    create_bl, list_bls as list_bl, update_bl,
    update_bl_status, list_bl_containers,
    BL_STATUS_FLOW, LOCKED_STATUSES, BL_TYPES, _s, _f, _i,
)
from managers.shipment_manager import list_shipments
from managers.document_duplicate_service import duplicate_bl, get_bl_snapshot
from pdf.bl_pdf import generate_bl_pdf

STATUS_OPTIONS = ["All Statuses", "Draft", "Submitted", "Approved", "Issued", "Surrendered", "Cancelled"]


def _pdf_button(bl_id: int, key_prefix: str = "bl") -> None:
    try:
        payload = get_bl_snapshot(bl_id)
        pdf_path = generate_bl_pdf(payload)
        if pdf_path and os.path.exists(pdf_path):
            with open(pdf_path, "rb") as fh:
                st.download_button(
                    "PDF", fh.read(), file_name=os.path.basename(pdf_path),
                    mime="application/pdf", key=f"{key_prefix}_pdf_{bl_id}",
                    use_container_width=True, type="primary",
                )
    except Exception as exc:
        st.error(f"PDF failed: {exc}")


def render() -> None:
    user = st.session_state.get("user", {})
    can_edit = can_write(str(user.get("role", "")).lower(), "bl")

    st.subheader("Bill of Lading")
    st.caption("HBL / MBL document control, container manifest and PDF")
    tabs = st.tabs(["Ledger", "Workspace", "New B/L"])
    with tabs[0]:
        _ledger(can_edit, user)
    with tabs[1]:
        _workspace(can_edit, user)
    with tabs[2]:
        _create(user, can_edit)


def _ledger(can_edit: bool, user: dict) -> None:
    f1, f2, f3 = st.columns([1, 1, 2])
    bl_type = f1.selectbox("Type", ["All Types"] + list(BL_TYPES), key="bl30_type")
    status = f2.selectbox("Status", STATUS_OPTIONS, key="bl30_status")
    search = f3.text_input("Search", placeholder="B/L, Job, Shipper, Consignee, POL or POD", key="bl30_search")

    try:
        rows = list_bl(status=None if status == "All Statuses" else status) or []
    except Exception as exc:
        st.error(f"Failed to load B/L records: {exc}")
        return
    if bl_type != "All Types":
        rows = [r for r in rows if r.get("bl_type") == bl_type]
    if search.strip():
        q = search.lower().strip()
        rows = [r for r in rows if q in f"{r.get('bl_no')} {r.get('job_no')} {r.get('shipper')} {r.get('consignee')} {r.get('port_of_loading')} {r.get('port_of_discharge')}".lower()]
    if not rows:
        st.info("No B/L records match the selected filters.")
        return

    display = [{
        "B/L No": _s(r.get("bl_no")), "Type": _s(r.get("bl_type")), "Status": _s(r.get("status")),
        "Job": _s(r.get("job_no"), "—"), "Shipper": _s(r.get("shipper"), "—"),
        "Consignee": _s(r.get("consignee"), "—"), "POL": _s(r.get("port_of_loading") or r.get("pol"), "—"),
        "POD": _s(r.get("port_of_discharge") or r.get("pod"), "—"),
        "Vessel / Voyage": f"{_s(r.get('vessel'))} {_s(r.get('voyage'))}".strip() or "—",
    } for r in rows]
    st.dataframe(pd.DataFrame(display), use_container_width=True, hide_index=True)

    st.markdown("### Document Actions")
    ids = [r["id"] for r in rows if r.get("id") is not None]
    labels = {r["id"]: f"{r.get('bl_no')} · {r.get('bl_type')} · {r.get('status')}" for r in rows if r.get("id") is not None}
    target = st.selectbox("Select B/L", ids, format_func=lambda x: labels[x], key="bl30_target")
    rec = next(r for r in rows if r.get("id") == target)
    a1, a2, a3, a4 = st.columns([3, 1, 1, 1])
    a1.caption(f"{rec.get('bl_no')} · Job {rec.get('job_no', '—')} · {rec.get('status', 'Draft')}")
    with a2:
        _pdf_button(target, "bl30_ledger")
    with a3:
        if can_edit and rec.get("status") not in LOCKED_STATUSES:
            if st.button("Edit", key=f"bl30_edit_{target}", use_container_width=True):
                st.session_state["selected_bl_id"] = target
                st.rerun()
        else:
            st.button("Edit", disabled=True, key=f"bl30_edit_disabled_{target}", use_container_width=True)
    with a4:
        if can_edit:
            if st.button("Duplicate", key=f"bl30_dup_{target}", use_container_width=True):
                try:
                    new_id = duplicate_bl(target, user)
                    st.session_state["selected_bl_id"] = new_id
                    st.success(f"Duplicated as B/L ID {new_id} (Draft)")
                    st.rerun()
                except Exception as exc:
                    st.error(f"Duplicate failed: {exc}")


def _workspace(can_edit: bool, user: dict) -> None:
    rows = list_bl() or []
    if not rows:
        st.info("No B/L records available.")
        return
    options = {r["id"]: f"{r.get('bl_no')} · {r.get('bl_type')} · {r.get('status')}" for r in rows}
    ids = list(options)
    default = ids.index(st.session_state["selected_bl_id"]) if st.session_state.get("selected_bl_id") in ids else 0
    selected_id = st.selectbox("Select B/L", ids, index=default, format_func=lambda x: options[x], key="bl30_ws")
    try:
        bl = get_bl_snapshot(selected_id)["bl"]
    except Exception as exc:
        st.error(str(exc))
        return

    st.session_state["selected_bl_id"] = selected_id
    status = _s(bl.get("status"), "Draft")
    editable = can_edit and status not in LOCKED_STATUSES

    st.markdown(f"### {bl.get('bl_no')} <small>· {bl.get('bl_type')} · {status}</small>", unsafe_allow_html=True)
    top1, top2, top3 = st.columns([3, 1, 1])
    with top1:
        next_statuses = BL_STATUS_FLOW.get(status, [])
        if editable and next_statuses:
            for ns in next_statuses:
                if st.button(f"→ {ns}", key=f"bl30_status_{selected_id}_{ns}"):
                    try:
                        update_bl_status(selected_id, ns)
                        st.rerun()
                    except Exception as exc:
                        st.error(str(exc))
        elif status in LOCKED_STATUSES:
            st.caption(f"Locked · {status}")
    with top2:
        _pdf_button(selected_id, "bl30_ws")
    with top3:
        if can_edit:
            if st.button("Duplicate", key=f"bl30_ws_dup_{selected_id}", use_container_width=True):
                try:
                    new_id = duplicate_bl(selected_id, user)
                    st.session_state["selected_bl_id"] = new_id
                    st.rerun()
                except Exception as exc:
                    st.error(f"Duplicate failed: {exc}")

    t1, t2, t3, t4, t5 = st.tabs(["Parties", "Routing", "Cargo", "Containers", "Documents"])
    with st.form(f"bl30_form_{selected_id}"):
        with t1:
            c1, c2 = st.columns(2)
            bl_date = c1.date_input("B/L Date", value=bl.get("bl_date") or None, disabled=not editable)
            place_issue = c2.text_input("Place of Issue", _s(bl.get("place_of_issue"), "BANGKOK, THAILAND"), disabled=not editable)
            shipper = st.text_area("Shipper / Exporter", _s(bl.get("shipper")), disabled=not editable)
            consignee = st.text_area("Consignee", _s(bl.get("consignee")), disabled=not editable)
            notify = st.text_area("Notify Party", _s(bl.get("notify_party")), disabled=not editable)
        with t2:
            c1, c2, c3 = st.columns(3)
            por = c1.text_input("POR", _s(bl.get("place_of_receipt") or bl.get("por")), disabled=not editable)
            pol = c2.text_input("POL", _s(bl.get("port_of_loading") or bl.get("pol")), disabled=not editable)
            pod = c3.text_input("POD", _s(bl.get("port_of_discharge") or bl.get("pod")), disabled=not editable)
            c4, c5, c6 = st.columns(3)
            delivery = c4.text_input("Delivery / Final Destination", _s(bl.get("place_of_delivery") or bl.get("final_destination")), disabled=not editable)
            vessel = c5.text_input("Vessel", _s(bl.get("vessel")), disabled=not editable)
            voyage = c6.text_input("Voyage", _s(bl.get("voyage")), disabled=not editable)
        with t3:
            c1, c2, c3, c4 = st.columns(4)
            freight = c1.selectbox("Freight Term", ["PREPAID", "COLLECT"], index=0 if _s(bl.get("freight_term")) == "PREPAID" else 1, disabled=not editable)
            payable = c2.text_input("Freight Payable At", _s(bl.get("freight_payable_at")), disabled=not editable)
            pkg_qty = c3.number_input("Package Qty", value=_i(bl.get("package_qty") or bl.get("package_quantity")), disabled=not editable)
            pkg_type = c4.text_input("Package Unit", _s(bl.get("package_type"), "PKGS"), disabled=not editable)
            gross = st.number_input("Gross Weight (KG)", value=_f(bl.get("gross_weight")), disabled=not editable)
            cbm = st.number_input("Measurement (CBM)", value=_f(bl.get("measurement_cbm")), disabled=not editable)
            goods = st.text_area("Description of Goods", _s(bl.get("description_of_goods")), disabled=not editable)
            c1, c2 = st.columns(2)
            marks = c1.text_area("Marks & Numbers", _s(bl.get("marks_numbers"), "N/M"), disabled=not editable)
            hs = c2.text_input("HS Code", _s(bl.get("hs_code")), disabled=not editable)
            remarks = st.text_area("Remarks", _s(bl.get("remarks")), disabled=not editable)
            special = st.text_area("Special Instructions", _s(bl.get("special_instructions")), disabled=not editable)
        with t4:
            linked = get_bl_snapshot(selected_id)["containers"]
            if linked:
                st.dataframe(pd.DataFrame([{
                    "Container": _s(c.get("container_no")), "Size": _s(c.get("container_size")),
                    "Type": _s(c.get("container_type")), "Seal": _s(c.get("seal_no"), "—"),
                    "Gross KG": _f(c.get("gross_weight")), "VGM KG": _f(c.get("vgm_kg")),
                } for c in linked]), use_container_width=True, hide_index=True)
            else:
                st.info("No containers linked to this B/L.")
        save = st.form_submit_button("Save Changes", type="primary", use_container_width=True, disabled=not editable)

    with t5:
        from views.document_ui import render_document_section
        render_document_section("HBL" if _s(bl.get("bl_type")) == "HBL" else "MBL", selected_id)

    if save:
        try:
            update_bl(selected_id, {
                "bl_date": bl_date.isoformat() if bl_date else None, "place_of_issue": place_issue,
                "shipper": shipper, "consignee": consignee, "notify_party": notify,
                "place_of_receipt": por, "port_of_loading": pol, "port_of_discharge": pod,
                "place_of_delivery": delivery, "vessel": vessel, "voyage": voyage,
                "freight_term": freight, "freight_payable_at": payable, "package_qty": int(pkg_qty),
                "package_type": pkg_type, "gross_weight": float(gross), "measurement_cbm": float(cbm),
                "description_of_goods": goods, "marks_numbers": marks, "hs_code": hs,
                "remarks": remarks, "special_instructions": special,
            })
            st.success("B/L updated.")
            st.rerun()
        except Exception as exc:
            st.error(f"Save failed: {exc}")


def _create(user: dict, can_edit: bool) -> None:
    if not can_edit:
        st.info("Read-only access.")
        return
    jobs = list_shipments() or []
    job_options = [j["job_no"] for j in jobs if j.get("job_no")]
    if not job_options:
        st.info("Create or convert a Job before creating a B/L.")
        return
    with st.form("bl30_create"):
        c1, c2 = st.columns(2)
        job_no = c1.selectbox("Job", job_options)
        bl_type = c2.selectbox("B/L Type", list(BL_TYPES))
        submitted = st.form_submit_button("Create B/L", type="primary", use_container_width=True)
    if submitted:
        try:
            new_id = create_bl(job_no, bl_type, user)
            st.session_state["selected_bl_id"] = new_id
            st.success(f"B/L created: {new_id}")
            st.rerun()
        except Exception as exc:
            st.error(f"Create failed: {exc}")
