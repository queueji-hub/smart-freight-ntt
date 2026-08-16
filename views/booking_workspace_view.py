"""Canonical booking workspace helpers. Legacy fields remain readable but are not user-facing."""
from __future__ import annotations

from typing import Any, Dict, Optional
import os
import pandas as pd
import streamlit as st
from datetime import date, timedelta

from core.freight_rules import get_freight_profile, resolve_vessel
from managers.auth_manager import can_write
from managers.booking_manager import create_booking, get_booking, list_bookings, update_booking, can_transition_booking_status, convert_booking_to_job
from managers.customer_manager import list_customers
from managers.master_data_manager import list_sales_users
from managers.tenant_context import get_current_tenant_id
from managers.master_data_crud_manager import list_ports, list_parties
from ui.design_system import page_header, section

CARGO_TYPES = ["FCL", "LCL", "AIR", "TRUCK"]
CONTAINER_TYPES = ["20'GP", "40'GP", "40'HC", "45'HC", "20'OT", "40'OT", "20'FR", "40'FR"]


def _s(v: Any, d: str = "") -> str:
    if v is None:
        return d
    t = str(v).strip()
    return d if t.lower() in {"", "none", "nan", "nat"} else t


def _master():
    customers = list_customers() or []
    sales = list_sales_users() or []
    carriers = list_parties("CARRIER")
    ports = list_ports()
    customer_map = {int(x["id"]): x.get("company_name", str(x["id"])) for x in customers if x.get("id")}
    sales_map = {int(x["id"]): (x.get("full_name") or x.get("username") or str(x["id"])) for x in sales if x.get("id")}
    carrier_map = {int(x["id"]): (x.get("display_name") or x.get("legal_name") or str(x["id"])) for x in carriers if x.get("id")}
    port_map = {int(x["id"]): f"{x.get('port_code')} — {x.get('port_name')}, {x.get('country_name') or ''}".strip(", ") for x in ports if x.get("id")}
    return customer_map, sales_map, carrier_map, port_map


def _pdf(record: Dict[str, Any], key: str):
    if st.button("PDF", key=f"booking_pdf_{key}", type="primary", width="stretch"):
        try:
            from pdf.booking_pdf import generate_booking_pdf
            status = record.get("approval_status") or record.get("status") or "Draft"
            path = generate_booking_pdf(record, approval_status=status)
            with open(path, "rb") as fh:
                st.session_state[f"pdf_{key}"] = fh.read()
                st.session_state[f"pdf_name_{key}"] = os.path.basename(path)
        except TypeError:
            from pdf.booking_pdf import generate_booking_pdf
            path = generate_booking_pdf(record)
            with open(path, "rb") as fh:
                st.session_state[f"pdf_{key}"] = fh.read()
                st.session_state[f"pdf_name_{key}"] = os.path.basename(path)
        except Exception as exc:
            st.error(f"Unable to create Booking PDF: {exc}")
    if st.session_state.get(f"pdf_{key}"):
        st.download_button("Download", st.session_state[f"pdf_{key}"], file_name=st.session_state.get(f"pdf_name_{key}", "booking.pdf"), mime="application/pdf", key=f"dl_{key}", width="stretch")


def _create(user):
    customer_map, sales_map, carrier_map, port_map = _master()
    with st.form("booking_workspace_create"):
        section("Booking Details")
        a, b, c, d = st.columns(4)
        customer_id = a.selectbox("Customer *", list(customer_map), format_func=lambda x: customer_map[x]) if customer_map else None
        sales_id = b.selectbox("Sales", list(sales_map), format_func=lambda x: sales_map[x]) if sales_map else None
        job_type = c.selectbox("Job Type", ["SE", "SI", "AE", "AI", "TE", "TI"])
        booking_date = d.date_input("Booking Date", date.today())
        e, f, g, h = st.columns(4)
        cargo_type = e.selectbox("Cargo Type", CARGO_TYPES)
        carrier_id = f.selectbox("Carrier", list(carrier_map), format_func=lambda x: carrier_map[x]) if carrier_map else None
        pol_id = g.selectbox("POL", list(port_map), format_func=lambda x: port_map[x]) if port_map else None
        pod_id = h.selectbox("POD", list(port_map), format_func=lambda x: port_map[x]) if port_map else None

        section("Routing & Vessel")
        r1, r2, r3, r4 = st.columns(4)
        trans_id = r1.selectbox("Transshipment Port", [None] + list(port_map), format_func=lambda x: "—" if x is None else port_map[x]) if port_map else None
        vessel = r2.text_input("Vessel")
        voyage = r3.text_input("Voyage")
        mother_vessel = r4.text_input("Mother Vessel")
        etd, eta = st.columns(2)
        etd_value = etd.date_input("ETD", date.today())
        eta_value = eta.date_input("ETA", date.today() + timedelta(days=14))

        section("Cargo")
        profile = get_freight_profile({"FCL":"SEA","LCL":"SEA","AIR":"AIR","TRUCK":"TRUCK"}[cargo_type], cargo_type)
        container_summary = ""
        gross_weight = measurement_cbm = chargeable_weight = 0.0
        package_qty = 0
        if profile.show_container_type:
            grid = st.data_editor(pd.DataFrame([{"type":"20'GP","qty":1}]), num_rows="dynamic", hide_index=True,
                column_config={"type": st.column_config.SelectboxColumn("Container Type", options=CONTAINER_TYPES, required=True), "qty": st.column_config.NumberColumn("Qty", min_value=1, step=1)}, key="booking_container_grid")
            parts = []
            for row in grid.to_dict("records"):
                if _s(row.get("type")) and int(row.get("qty") or 0) > 0:
                    parts.append(f"{row['type']} x {int(row['qty'])}")
            container_summary = " | ".join(parts)
            gross_weight = st.number_input("Gross Weight (KG)", min_value=0.0, step=1.0)
        elif profile.show_chargeable_weight:
            gross_weight = st.number_input("Gross Weight (KG)", min_value=0.0, step=1.0)
            chargeable_weight = st.number_input("Chargeable Weight (KG)", min_value=0.0, step=1.0)
            package_qty = st.number_input("Packages", min_value=0, step=1)
        else:
            gross_weight = st.number_input("Gross Weight (KG)", min_value=0.0, step=1.0)
            measurement_cbm = st.number_input("Volume (CBM)", min_value=0.0, step=0.01) if profile.show_cbm else 0.0
            package_qty = st.number_input("Packages", min_value=0, step=1)

        section("Receiving")
        if profile.show_cy:
            c1, c2, c3 = st.columns(3)
            cy_place = c1.text_input("CY Place")
            cy_date = c2.date_input("CY Date", value=None)
            return_place = c3.text_input("Container Return Place")
            return_date = st.date_input("Container Return Date", value=None)
            cfs_place = cfs_date = None
        elif profile.show_cfs:
            c1, c2 = st.columns(2)
            cfs_place = c1.text_input("CFS Place")
            cfs_date = c2.date_input("CFS Date", value=None)
            cy_place = cy_date = return_place = return_date = None
        else:
            cy_place = cy_date = cfs_place = cfs_date = return_place = return_date = None
        remark = st.text_area("Instructions / Remarks")
        save = st.form_submit_button("Save Booking", type="primary", width="stretch")

    if not save:
        return
    errors = []
    if customer_id is None: errors.append("Customer is required.")
    if pol_id is None or pod_id is None: errors.append("POL and POD are required.")
    if eta_value < etd_value: errors.append("ETA cannot be earlier than ETD.")
    if cargo_type == "AIR" and chargeable_weight <= 0: errors.append("Chargeable Weight is required for Air.")
    if cargo_type == "LCL" and measurement_cbm <= 0: errors.append("Volume (CBM) is required for LCL.")
    if cargo_type == "FCL" and not container_summary: errors.append("At least one container is required for FCL.")
    if errors:
        for e in errors: st.error(e)
        return
    payload = {
        "booking_date": booking_date.isoformat(), "job_type": job_type, "customer_id": customer_id,
        "customer_name": customer_map[customer_id], "sales_id": sales_id,
        "sales_person": sales_map.get(sales_id, "") if sales_id else "",
        "carrier_id": carrier_id, "carrier": carrier_map.get(carrier_id, "") if carrier_id else "",
        "pol_id": pol_id, "pol": port_map.get(pol_id, "") if pol_id else "", "pod_id": pod_id,
        "pod": port_map.get(pod_id, "") if pod_id else "", "transhipment_port": port_map.get(trans_id) if trans_id else None,
        "vessel": vessel.strip() or None, "voyage": voyage.strip() or None,
        "m_vessel": mother_vessel.strip() or None, "mother_vessel": mother_vessel.strip() or None,
        "etd": etd_value.isoformat(), "eta": eta_value.isoformat(), "cargo_type": cargo_type,
        "gross_weight": gross_weight or None, "measurement_cbm": measurement_cbm or None,
        "chargeable_weight": chargeable_weight or None, "package_qty": int(package_qty or 0) or None,
        "container_summary": container_summary or None, "cy_place": cy_place, "cy_date": cy_date.isoformat() if cy_date else None,
        "cfs_place": cfs_place, "cfs_date": cfs_date.isoformat() if cfs_date else None,
        "customer_return_date": return_date.isoformat() if return_date else None, "return_place": return_place,
        "remark": remark.strip() or None, "created_by": user.get("username", "system")
    }
    try:
        no = create_booking(payload, user)
        st.success(f"Booking {no} created.")
        st.rerun()
    except Exception as exc:
        st.error(f"Unable to save booking: {exc}")


def _detail(record, user, can_edit):
    no = _s(record.get("booking_no"), "—")
    section("Booking Details")
    top = st.columns(6)
    top[0].metric("Booking No.", no); top[1].metric("Booking Date", _s(record.get("booking_date"), "—")); top[2].metric("Status", _s(record.get("status"), "Draft")); top[3].metric("Customer", _s(record.get("customer_name"), "—")); top[4].metric("ETD", _s(record.get("etd"), "—")); top[5].metric("ETA", _s(record.get("eta"), "—"))
    section("Routing & Vessel")
    cols = st.columns(5)
    cols[0].write(f"**Carrier**\n\n{_s(record.get('carrier'),'—')}")
    cols[1].write(f"**Vessel / Voyage**\n\n{(_s(record.get('vessel')) + ' / ' + _s(record.get('voyage'))).strip(' /') or '—'}")
    cols[2].write(f"**Mother Vessel**\n\n{_s(record.get('m_vessel') or record.get('mother_vessel'),'—')}")
    cols[3].write(f"**Transshipment Port**\n\n{_s(record.get('transhipment_port'),'—')}")
    cols[4].write(f"**POL / POD**\n\n{_s(record.get('pol'),'—')} / {_s(record.get('pod'),'—')}")
    section("Cargo & Receiving")
    profile = get_freight_profile({"FCL":"SEA","LCL":"SEA","AIR":"AIR","TRUCK":"TRUCK"}.get(record.get("cargo_type"), "SEA"), record.get("cargo_type", "LCL"))
    if profile.show_container_type: st.info(_s(record.get("container_summary"), "No containers recorded."))
    else:
        c = st.columns(4); c[0].metric("Packages", _s(record.get("package_qty"), "0")); c[1].metric("Gross Weight", f"{float(record.get('gross_weight') or 0):,.2f} KG"); c[2].metric("Volume / Chargeable", f"{float((record.get('measurement_cbm') if profile.show_cbm else record.get('chargeable_weight')) or 0):,.2f} {'CBM' if profile.show_cbm else 'KG'}"); c[3].metric("Handling", profile.receiving_kind)
    section("Actions")
    a = st.columns(4)
    with a[0]: _pdf(record, no)
    with a[1]:
        if can_edit and st.button("Submit", key=f"sub_{no}") and str(record.get("status","DRAFT")).upper()=="DRAFT":
            ok, reason = can_transition_booking_status("DRAFT", "SUBMITTED")
            if ok: update_booking(no, {"status":"SUBMITTED"}, user.get("tenant_id")); st.rerun()
            else: st.error(reason)
    with a[2]:
        if can_edit and st.button("Confirm", key=f"con_{no}") and str(record.get("status","")).upper()=="SUBMITTED":
            ok, reason = can_transition_booking_status("SUBMITTED", "CONFIRMED")
            if ok: update_booking(no, {"status":"CONFIRMED"}, user.get("tenant_id")); st.rerun()
            else: st.error(reason)
    with a[3]:
        if can_edit and st.button("Convert to Job", key=f"job_{no}") and str(record.get("status","")).upper()=="CONFIRMED":
            convert_booking_to_job(no, user); st.rerun()
    if can_edit:
        with st.expander("Edit Booking", expanded=False):
            with st.form(f"edit_{no}"):
                vessel = st.text_input("Vessel", value=_s(record.get("vessel")))
                voyage = st.text_input("Voyage", value=_s(record.get("voyage")))
                mother = st.text_input("Mother Vessel", value=_s(record.get("m_vessel") or record.get("mother_vessel")))
                trans = st.text_input("Transshipment Port", value=_s(record.get("transhipment_port")))
                save = st.form_submit_button("Save Changes", type="primary")
            if save:
                update_booking(no, {"vessel":vessel.strip() or None,"voyage":voyage.strip() or None,"m_vessel":mother.strip() or None,"mother_vessel":mother.strip() or None,"transhipment_port":trans.strip() or None}, user.get("tenant_id")); st.success("Booking updated."); st.rerun()


def render():
    page_header("booking", status_text="Online")
    user = st.session_state.get("user", {})
    role = str(user.get("role", "")).lower(); can_edit = can_write(role, "booking")
    tenant = user.get("tenant_id") or get_current_tenant_id()
    records = list_bookings(tenant_id=tenant, limit=200) or []
    s, n = st.columns([4,1])
    query = s.text_input("Search bookings", placeholder="Booking, customer, POL, POD, vessel or voyage")
    if n.button("New Booking", type="primary", width="stretch") and can_edit: st.session_state["booking_workspace_new"] = True
    if query.strip():
        q=query.strip().lower(); records=[r for r in records if q in str(r).lower()]
    if st.session_state.get("booking_workspace_new") and can_edit:
        _create(user)
        if st.button("Close", key="close_booking_new"): st.session_state.pop("booking_workspace_new", None); st.rerun()
        return
    section("Bookings")
    st.dataframe(pd.DataFrame([{"Booking No.":_s(r.get("booking_no")),"Booking Date":_s(r.get("booking_date"),"—"),"Customer":_s(r.get("customer_name"),"—"),"Carrier":_s(r.get("carrier"),"—"),"Vessel / Voyage":((_s(r.get("vessel"))+" / "+_s(r.get("voyage"))).strip(" /") or "—"),"Mother Vessel":_s(r.get("m_vessel") or r.get("mother_vessel"),"—"),"ETD":_s(r.get("etd"),"—"),"ETA":_s(r.get("eta"),"—"),"Status":_s(r.get("status"),"—")} for r in records]), hide_index=True, use_container_width=True)
    if records:
        no = st.selectbox("Select Booking", [r["booking_no"] for r in records if r.get("booking_no")])
        record = get_booking(no, tenant)
        if record: _detail(record, user, can_edit)
    else: st.info("No bookings found.")
