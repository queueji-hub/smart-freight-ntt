"""Streamlined Booking workspace for Phase 30.

Presentation-only redesign around existing booking manager APIs. Legacy booking
records remain readable while new entry/edit screens follow canonical freight rules.
"""
from __future__ import annotations

import os
from datetime import date, timedelta
from typing import Any, Dict

import pandas as pd
import streamlit as st

from config import JOB_TYPES
from core.freight_rules import get_freight_profile, resolve_vessel
from managers.auth_manager import can_write
from managers.booking_manager import (
    can_transition_booking_status,
    convert_booking_to_job,
    create_booking,
    get_booking,
    list_bookings,
    update_booking,
)
from managers.customer_manager import list_customers
from managers.master_data_manager import list_distinct_job_values, list_sales_users
from ui.design_system import page_header, section

CARGO_TYPES = ["FCL", "LCL", "AIR", "TRUCK"]
CONTAINER_TYPES = ["20'GP", "40'GP", "40'HC", "45'HC", "20'OT", "40'OT", "20'FR", "40'FR"]


def _s(value: Any, default: str = "") -> str:
    if value is None:
        return default
    value = str(value).strip()
    return default if value.lower() in {"", "none", "nan", "nat"} else value


def _date(value: Any, default: date | None = None) -> date | None:
    if isinstance(value, date):
        return value
    if not value:
        return default
    try:
        return date.fromisoformat(str(value)[:10])
    except (ValueError, TypeError):
        return default


def _load_master_data():
    customers = list_customers() or []
    sales = list_sales_users() or []
    liners = list_distinct_job_values("liner") if "liner" else []
    vessels = list_distinct_job_values("vessel") or []
    ports = list_distinct_job_values("transshipment_port") or []
    return customers, sales, liners, vessels, ports


def _prepare_pdf(record: Dict[str, Any], key_prefix: str) -> None:
    no = _s(record.get("booking_no"), "booking")
    status = _s(record.get("approval_status") or record.get("status"), "Draft")
    try:
        from pdf.booking_pdf import generate_booking_pdf

        path = generate_booking_pdf(record, approval_status=status)
        if path and os.path.exists(path):
            with open(path, "rb") as fh:
                st.session_state[f"{key_prefix}_pdf_bytes"] = fh.read()
            st.session_state[f"{key_prefix}_pdf_name"] = os.path.basename(path)
    except TypeError:
        # Backward-compatible fallback for older generator signatures.
        from pdf.booking_pdf import generate_booking_pdf

        path = generate_booking_pdf(record)
        if path and os.path.exists(path):
            with open(path, "rb") as fh:
                st.session_state[f"{key_prefix}_pdf_bytes"] = fh.read()
            st.session_state[f"{key_prefix}_pdf_name"] = os.path.basename(path)
    except Exception as exc:
        st.error(f"Unable to create PDF: {exc}")


def _render_pdf_action(record: Dict[str, Any], key_prefix: str) -> None:
    if st.button("PDF", key=f"prepare_pdf_{key_prefix}", type="primary", width="stretch"):
        _prepare_pdf(record, key_prefix)
    pdf_bytes = st.session_state.get(f"{key_prefix}_pdf_bytes")
    if pdf_bytes:
        st.download_button(
            "Download",
            data=pdf_bytes,
            file_name=st.session_state.get(f"{key_prefix}_pdf_name", "booking.pdf"),
            mime="application/pdf",
            key=f"download_pdf_{key_prefix}",
            width="stretch",
        )


def _container_rows(existing: str = "") -> list[dict]:
    if not existing:
        return [{"type": "20'GP", "qty": 1}]
    rows: list[dict] = []
    for part in existing.split("|"):
        left, _, right = part.strip().partition("x")
        if left.strip() in CONTAINER_TYPES:
            try:
                qty = int(right.strip()) if right.strip() else 1
            except ValueError:
                qty = 1
            rows.append({"type": left.strip(), "qty": max(qty, 1)})
    return rows or [{"type": "20'GP", "qty": 1}]


def _container_summary(df: pd.DataFrame) -> str:
    values = []
    for row in df.to_dict("records"):
        ctype = _s(row.get("type"))
        try:
            qty = int(row.get("qty") or 0)
        except (TypeError, ValueError):
            qty = 0
        if ctype and qty > 0:
            values.append(f"{ctype} x {qty}")
    return " | ".join(values)


def _create_form(user: Dict[str, Any]):
    customers, sales, liners, vessels, ports = _load_master_data()
    customer_map = {int(c["id"]): c.get("company_name", str(c["id"])) for c in customers if c.get("id")}
    customer_ids = list(customer_map)
    sales_map = {int(u["id"]): (u.get("full_name") or u.get("username") or str(u["id"])) for u in sales if u.get("id")}
    sales_ids = list(sales_map)
    liner_options = [""] + liners
    vessel_options = [""] + vessels
    port_options = [""] + ports

    section("Booking Details")
    with st.form("booking_v2_create_form"):
        customer_id = st.selectbox("Customer *", customer_ids, format_func=lambda x: customer_map[x]) if customer_ids else None
        sales_id = st.selectbox("Sales", sales_ids, format_func=lambda x: sales_map[x]) if sales_ids else None
        job_type = st.selectbox("Job Type *", list(JOB_TYPES.keys()), format_func=lambda x: JOB_TYPES.get(x, x))
        cargo_type = st.selectbox("Cargo Type *", CARGO_TYPES)
        quotation_no = st.text_input("Quotation Ref", placeholder="Optional")

        section("Routing & Vessel")
        pol, transhipment_port, pod = st.columns(3)
        with pol:
            pol_value = st.text_input("POL *")
        with transhipment_port:
            trans_value = st.selectbox("Transshipment Port", port_options)
        with pod:
            pod_value = st.text_input("POD *")

        l_col, v_col, voy_col = st.columns([1.2, 1.4, 1.4])
        with l_col:
            liner_value = st.selectbox("Liner", liner_options)
        with v_col:
            vessel_value = st.selectbox("Vessel (Feeder / Ocean)", vessel_options)
        with voy_col:
            voyage_value = st.text_input("Voyage No.")

        mv_col, mvoy_col = st.columns(2)
        with mv_col:
            mother_value = st.text_input("Mother Vessel")
        with mvoy_col:
            mother_voyage_value = st.text_input("Mother Voyage No.")

        etd_default = date.today()
        eta_default = etd_default + timedelta(days=14)
        etd_col, eta_col = st.columns(2)
        with etd_col:
            etd_value = st.date_input("ETD", etd_default)
        with eta_col:
            eta_value = st.date_input("ETA", eta_default)

        section("Cargo & Equipment")
        profile = get_freight_profile({"FCL": "SEA", "LCL": "SEA", "AIR": "AIR", "TRUCK": "TRUCK"}[cargo_type], cargo_type)
        gross_weight = 0.0
        measurement_cbm = 0.0
        package_qty = 0
        package_unit = "PKGS"
        container_summary = ""

        if profile.show_container_type:
            table = st.data_editor(
                pd.DataFrame([{"type": "20'GP", "qty": 1}]),
                num_rows="dynamic",
                hide_index=True,
                column_config={
                    "type": st.column_config.SelectboxColumn("Container Type", options=CONTAINER_TYPES, required=True),
                    "qty": st.column_config.NumberColumn("Qty", min_value=1, step=1, required=True),
                },
                key="booking_v2_containers",
            )
            container_summary = _container_summary(table)
            gross_weight = st.number_input("Gross Weight (KG)", min_value=0.0, step=1.0)
        elif profile.show_chargeable_weight:
            gross_weight = st.number_input("Gross Weight (KG)", min_value=0.0, step=1.0)
            chargeable = st.number_input("Chargeable Weight (KG)", min_value=0.0, step=1.0)
            package_qty = st.number_input("Packages", min_value=0, step=1)
        else:
            gross_weight = st.number_input("Gross Weight (KG)", min_value=0.0, step=1.0)
            if profile.show_cbm:
                measurement_cbm = st.number_input("Volume (CBM)", min_value=0.0, step=0.01)
            package_qty = st.number_input("Packages", min_value=0, step=1)

        section("Receiving & Notes")
        cy_date = cy_place = cfs_date = cfs_place = return_date = return_place = None
        if profile.show_cy:
            cy1, cy2 = st.columns(2)
            with cy1:
                cy_date = st.date_input("CY Date", value=None)
            with cy2:
                cy_place = st.text_input("CY Place")
            ret1, ret2 = st.columns(2)
            with ret1:
                return_date = st.date_input("Container Return", value=None)
            with ret2:
                return_place = st.text_input("Return Place")
        elif profile.show_cfs:
            cfs1, cfs2 = st.columns(2)
            with cfs1:
                cfs_date = st.date_input("CFS Date", value=None)
            with cfs2:
                cfs_place = st.text_input("CFS Place")

        remark = st.text_area("Remarks")
        submitted = st.form_submit_button("Save Booking", type="primary", width="stretch")

    if submitted:
        errors = []
        if customer_id is None:
            errors.append("Customer is required.")
        if not pol_value.strip():
            errors.append("POL is required.")
        if not pod_value.strip():
            errors.append("POD is required.")
        if eta_value < etd_value:
            errors.append("ETA cannot be earlier than ETD.")
        if profile.show_cbm and measurement_cbm <= 0:
            errors.append("Volume (CBM) is required for this shipment.")
        if profile.show_container_type and not container_summary:
            errors.append("At least one container type is required for FCL.")
        if profile.show_chargeable_weight and chargeable <= 0:
            errors.append("Chargeable Weight is required for Air.")

        if errors:
            for error in errors:
                st.error(error)
            return

        customer_name = customer_map.get(customer_id, "")
        sales_name = sales_map.get(sales_id, "") if sales_id else ""
        payload = {
            "booking_no": None,
            "carrier_booking_no": None,
            "quotation_id": None,
            "quotation_no": quotation_no.strip() or None,
            "job_type": job_type,
            "customer_id": customer_id,
            "customer_name": customer_name,
            "sales_id": sales_id,
            "sales_person": sales_name,
            "pol": pol_value.strip(),
            "pod": pod_value.strip(),
            "transhipment_port": trans_value or None,
            "liner": liner_value or None,
            "vessel": vessel_value or None,
            "voyage": voyage_value.strip() or None,
            "m_vessel": mother_value.strip() or None,
            "mother_vessel": mother_value.strip() or None,
            "m_voyage": mother_voyage_value.strip() or None,
            "mother_voyage": mother_voyage_value.strip() or None,
            "etd": etd_value.isoformat(),
            "eta": eta_value.isoformat(),
            "cargo_type": cargo_type,
            "gross_weight": gross_weight or None,
            "measurement_cbm": measurement_cbm or None,
            "package_qty": int(package_qty or 0) or None,
            "package_unit": package_unit,
            "container_summary": container_summary or None,
            "cy_date": cy_date.isoformat() if cy_date else None,
            "cy_place": cy_place.strip() if cy_place else None,
            "cfs_date": cfs_date.isoformat() if cfs_date else None,
            "cfs_place": cfs_place.strip() if cfs_place else None,
            "customer_return_date": return_date.isoformat() if return_date else None,
            "return_place": return_place.strip() if return_place else None,
            "remark": remark.strip() or None,
            "created_by": user.get("username", "system"),
        }
        try:
            booking_no = create_booking(payload, user)
            st.success(f"Booking {booking_no} created.")
            st.rerun()
        except Exception as exc:
            st.error(f"Unable to save booking: {exc}")


def _render_selected(selected: Dict[str, Any], user: Dict[str, Any], can_edit: bool):
    booking_no = _s(selected.get("booking_no"))
    current_status = _s(selected.get("status"), "DRAFT").upper()
    section("Booking Summary")
    summary = st.columns(5)
    summary[0].metric("Booking No.", booking_no or "—")
    summary[1].metric("Customer", _s(selected.get("customer_name"), "—"))
    summary[2].metric("Status", current_status)
    summary[3].metric("POL", _s(selected.get("pol"), "—"))
    summary[4].metric("POD", _s(selected.get("pod"), "—"))

    section("Routing & Vessel")
    cols = st.columns(5)
    cols[0].write(f"**Liner**\n\n{_s(selected.get('liner'), '—')}")
    cols[1].write(f"**Vessel (Feeder / Ocean)**\n\n{_s(selected.get('vessel'), '—')}")
    cols[2].write(f"**Voyage No.**\n\n{_s(selected.get('voyage'), '—')}")
    m_vessel_val = _s(selected.get('mother_vessel') or selected.get('m_vessel'), '—')
    m_voy_val = _s(selected.get('mother_voyage') or selected.get('m_voyage'), '')
    m_full = f"{m_vessel_val} {m_voy_val}".strip() if m_vessel_val != '—' else '—'
    cols[3].write(f"**Mother Vessel / Voyage**\n\n{m_full}")
    cols[4].write(f"**Transshipment Port**\n\n{_s(selected.get('transhipment_port'), '—')}")

    profile = get_freight_profile(
        selected.get("job_type") if selected.get("job_type") else selected.get("mode", "SEA"),
        selected.get("cargo_type", "LCL"),
    )
    section("Cargo & Equipment")
    if profile.show_container_type:
        st.info(_s(selected.get("container_summary"), "No containers recorded."))
    else:
        cargo_cols = st.columns(4)
        cargo_cols[0].metric("Packages", _s(selected.get("package_qty"), "0"))
        cargo_cols[1].metric("Gross Weight", f"{float(selected.get('gross_weight') or 0):,.2f} KG")
        if profile.show_cbm:
            cargo_cols[2].metric("Volume", f"{float(selected.get('measurement_cbm') or 0):,.2f} CBM")
        elif profile.show_chargeable_weight:
            cargo_cols[2].metric("Chargeable Weight", f"{float(selected.get('chargeable_weight') or 0):,.2f} KG")
        cargo_cols[3].metric("Handling", profile.receiving_kind)

    section("Actions")
    act = st.columns(5)
    with act[0]:
        _render_pdf_action(selected, f"booking_{booking_no}")
    with act[1]:
        if can_edit and st.button("Submit", key=f"submit_{booking_no}", width="stretch") and current_status == "DRAFT":
            ok, reason = can_transition_booking_status(current_status, "SUBMITTED")
            if ok:
                update_booking(booking_no, {"status": "SUBMITTED"}, user.get("tenant_id"))
                st.rerun()
            else:
                st.error(reason)
    with act[2]:
        if can_edit and st.button("Confirm", key=f"confirm_{booking_no}", type="primary", width="stretch") and current_status == "SUBMITTED":
            ok, reason = can_transition_booking_status(current_status, "CONFIRMED")
            if ok:
                update_booking(booking_no, {"status": "CONFIRMED"}, user.get("tenant_id"))
                st.rerun()
            else:
                st.error(reason)
    with act[3]:
        if can_edit and st.button("Convert to Job", key=f"convert_{booking_no}", width="stretch") and current_status == "CONFIRMED":
            try:
                convert_booking_to_job(booking_no, user)
                st.success("Job created from booking.")
                st.rerun()
            except Exception as exc:
                st.error(str(exc))
    with act[4]:
        st.write("")

    if can_edit:
        with st.expander("Edit Booking", expanded=False):
            section("Routing & Transport")
            with st.form(f"edit_booking_{booking_no}"):
                r1, r2, r3 = st.columns(3)
                new_pol = r1.text_input("POL", value=_s(selected.get("pol")))
                new_trans = r2.text_input("Transshipment Port", value=_s(selected.get("transhipment_port")))
                new_pod = r3.text_input("POD", value=_s(selected.get("pod")))

                v1, v2 = st.columns(2)
                new_vessel = v1.text_input("Vessel (Feeder / Ocean)", value=_s(selected.get("vessel")))
                new_voyage = v2.text_input("Voyage No.", value=_s(selected.get("voyage")))

                mv1, mv2 = st.columns(2)
                new_mother = mv1.text_input("Mother Vessel", value=_s(selected.get("mother_vessel") or selected.get("m_vessel")))
                new_mother_voyage = mv2.text_input("Mother Voyage No.", value=_s(selected.get("mother_voyage") or selected.get("m_voyage")))

                new_remark = st.text_area("Remarks", value=_s(selected.get("remark")))
                save = st.form_submit_button("Save Changes", type="primary", width="stretch")
            if save:
                try:
                    update_booking(
                        booking_no,
                        {
                            "pol": new_pol.strip(),
                            "pod": new_pod.strip(),
                            "vessel": new_vessel.strip() or None,
                            "voyage": new_voyage.strip() or None,
                            "m_vessel": new_mother.strip() or None,
                            "mother_vessel": new_mother.strip() or None,
                            "m_voyage": new_mother_voyage.strip() or None,
                            "mother_voyage": new_mother_voyage.strip() or None,
                            "transhipment_port": new_trans.strip() or None,
                            "remark": new_remark.strip() or None,
                        },
                        user.get("tenant_id"),
                    )
                    st.success("Booking updated.")
                    st.rerun()
                except Exception as exc:
                    st.error(f"Unable to modify booking: {exc}")


def render():
    page_header("booking", status_text="Online")
    user = st.session_state.get("user", {})
    role = str(user.get("role", "")).lower()
    can_edit = can_write(role, "booking")
    tenant_id = user.get("tenant_id", "default")

    customers, _sales, _liners, _vessels, _ports = _load_master_data()
    if not customers:
        st.info("No customers available. Add a customer in Master Data first.")

    records = list_bookings(tenant_id=tenant_id, limit=200) or []
    filter_col, action_col = st.columns([4, 1])
    with filter_col:
        query = st.text_input("Search bookings", placeholder="Booking, customer, POL, POD or vessel", key="booking_v2_search")
    with action_col:
        st.write("")
        create_new = st.button("New Booking", type="primary", width="stretch") if can_edit else False

    if query.strip():
        q = query.strip().lower()
        records = [r for r in records if q in str(r).lower()]

    if create_new:
        st.session_state["booking_v2_create_mode"] = True

    if st.session_state.get("booking_v2_create_mode") and can_edit:
        _create_form(user)
        if st.button("Close", key="booking_v2_close_create"):
            st.session_state.pop("booking_v2_create_mode", None)
            st.rerun()
        return

    section("Bookings")
    table = pd.DataFrame([
        {
            "Booking No.": _s(r.get("booking_no")),
            "Customer": _s(r.get("customer_name"), "—"),
            "POL": _s(r.get("pol"), "—"),
            "POD": _s(r.get("pod"), "—"),
            "Vessel": resolve_vessel(r.get("m_vessel"), r.get("vessel")) or "—",
            "ETD": _s(r.get("etd"), "—"),
            "ETA": _s(r.get("eta"), "—"),
            "Status": _s(r.get("status"), "—"),
        }
        for r in records
    ])
    st.dataframe(table, hide_index=True, use_container_width=True)

    if not records:
        st.info("No bookings found.")
        return

    options = [r["booking_no"] for r in records if r.get("booking_no")]
    selected_no = st.selectbox("Choose Booking", options=options, key="booking_v2_selected")
    selected = get_booking(selected_no, tenant_id)
    if selected:
        _render_selected(selected, user, can_edit)
