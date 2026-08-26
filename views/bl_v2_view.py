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
        st.warning("No jobs available to issue B/L or Waybill. Please create a Job first.")
        return

    from managers.bl_workflow_service import detect_transport_mode
    from managers.booking_manager import get_booking

    section("Issue New Company B/L or Waybill")
    
    job_keys = list(jmap)
    target_job = st.session_state.get("target_job_no")
    def_idx = job_keys.index(target_job) if target_job in job_keys else 0

    job_no = st.selectbox("Choose Parent Shipment / Job", job_keys, index=def_idx, key="bl_new_job_select")
    selected_job = jmap.get(job_no, {})
    
    bk_no = selected_job.get("booking_no")
    bk_data = get_booking(bk_no) if bk_no else {}
    
    t_mode, d_type, d_title = detect_transport_mode(job=selected_job, booking=bk_data)

    mode_badge = "✈️ Air Freight" if t_mode == "AIR" else "🚚 Road / Truck Freight" if t_mode == "TRUCK" else "🚢 Sea Freight"
    doc_badge = "✈️ Air Waybill (IATA Standard HAWB)" if t_mode == "AIR" else "🚚 Truck Waybill (FTL / LTL)" if t_mode == "TRUCK" else "🚢 Ocean Bill of Lading"

    c1, c2, c3 = st.columns(3)
    c1.metric("Selected Job", job_no)
    c2.metric("Detected Mode", mode_badge)
    c3.metric("Auto Document Type", doc_badge)

    st.caption(f"**Customer:** {_s(selected_job.get('customer_name'))} · **POL/Origin:** {_s(selected_job.get('pol'))} · **POD/Destination:** {_s(selected_job.get('pod'))} · **Carrier:** {_s(selected_job.get('carrier'))}")

    col_btn1, col_btn2 = st.columns([3, 1])
    with col_btn1:
        if st.button(f"🚀 Issue {d_title.title()} for Job {job_no}", key=f"btn_issue_bl_{job_no}", type="primary", use_container_width=True):
            try:
                bid = create_bl_from_job(job_no, user)
                st.session_state["bl_v2_selected"] = bid
                st.session_state["bl_show_new_form"] = False
                st.success(f"Successfully issued {d_title.title()} for Job {job_no}!")
                st.rerun()
            except Exception as exc:
                st.error(f"Unable to issue document: {exc}")
    with col_btn2:
        if st.button("Cancel", key="btn_cancel_new_bl", use_container_width=True):
            st.session_state["bl_show_new_form"] = False
            st.rerun()


def _edit(bl: Dict[str, Any]) -> None:
    bid = int(bl["id"])
    job = {}
    if bl.get("job_no"):
        try:
            from managers.shipment_manager import get_shipment
            job = get_shipment(bl.get("job_no")) or {}
        except Exception:
            pass
    from pdf.bl_document_renderer import resolve_document_title
    doc_title = resolve_document_title(bl=bl, job=job)
    mode = str(bl.get("transport_mode") or ("AIR" if "AIR" in doc_title else "TRUCK" if "TRUCK" in doc_title else "SEA")).upper()

    section(f"Edit {doc_title.title()}")
    with st.form(f"bl_edit_{bid}"):
        if mode == "AIR":
            st.info("✈️ **Air Waybill Mode (IATA Standard HAWB)** — Pre-filled from Air Job.")
            section("1. Parties & Accounts")
            a, b = st.columns(2)
            shipper = a.text_area("Shipper Name & Address", _s(bl.get("shipper"), ""), height=85)
            consignee = b.text_area("Consignee Name & Address", _s(bl.get("consignee"), ""), height=85)
            c, d = st.columns(2)
            exporter_acct = c.text_input("Shipper / Exporter Account No.", _s(bl.get("exporter_account_no"), ""))
            consignee_acct = d.text_input("Consignee Account No.", _s(bl.get("consignee_account_no"), ""))
            c2, d2 = st.columns(2)
            notify = c2.text_area("Notify Party", _s(bl.get("notify_party"), "SAME AS CONSIGNEE"), height=75)
            accounting_info = d2.text_area("Accounting Information", _s(bl.get("accounting_info"), "FREIGHT PREPAID / ISSUED AS PER AGREEMENT"), height=75)

            section("2. Flight & Routing")
            a, b, c = st.columns(3)
            pol = a.text_input("Airport of Departure", _s(bl.get("airport_departure") or bl.get("port_of_loading"), "BKK / BANGKOK"))
            pod = b.text_input("Airport of Destination", _s(bl.get("airport_destination") or bl.get("port_of_discharge"), "SIN / SINGAPORE"))
            first_carrier = c.text_input("By First Carrier", _s(bl.get("first_carrier"), "THAI AIRWAYS (TG)"))

            a2, b2, c2 = st.columns(3)
            flight_no = a2.text_input("Flight No.", _s(bl.get("flight_no"), "TG 401"))
            flight_date = b2.date_input("Flight Date", _d(bl.get("flight_date") or bl.get("etd")))
            iata_code = c2.text_input("Agent's IATA Code", _s(bl.get("iata_code"), "33-4-7890/0014"))

            section("3. Valuation & Rating Details")
            v1, v2, v3, v4 = st.columns(4)
            currency = v1.selectbox("Currency", ["USD", "THB", "EUR", "JPY", "SGD"], index=0 if str(bl.get("currency") or "USD") == "USD" else 1)
            chgs_code = v2.selectbox("CHGS Code", ["PP", "CC"], index=0 if str(bl.get("chgs_code") or "PP") == "PP" else 1)
            decl_carriage = v3.text_input("Declared Value (Carriage)", _s(bl.get("declared_value_carriage"), "NVD"))
            decl_customs = v4.text_input("Declared Value (Customs)", _s(bl.get("declared_value_customs"), "NCV"))

            section("4. Cargo & Handling")
            a, b, c, d = st.columns(4)
            packages = a.number_input("No. of Pieces RCP", min_value=0, value=int(bl.get("package_qty") or 1))
            package_type = b.text_input("Package Type", _s(bl.get("package_type"), "PKGS"))
            gross = c.number_input("Gross Weight (KG)", min_value=0.0, value=float(bl.get("gross_weight") or 0), step=0.01)
            chargeable_wt = d.number_input("Chargeable Weight (KG)", min_value=0.0, value=float(bl.get("chargeable_weight") or bl.get("gross_weight") or 0), step=0.01)

            rate_class = st.text_input("Rate Class (e.g. Q, N, M)", _s(bl.get("rate_class"), "Q"))
            cargo_desc = st.text_area("Nature and Quantity of Goods (incl. Dimensions / Vol)", _s(bl.get("description_of_goods"), "SAID TO CONTAIN GENERAL CARGO"), height=90)
            
            h1, h2 = st.columns(2)
            handling_info = h1.text_input("Handling Information", _s(bl.get("handling_info"), "NO SPECIAL HANDLING REQUIRED / GENERAL CARGO"))
            sci = h2.text_input("Special Customs Information (SCI)", _s(bl.get("sci"), "TH-EXP"))

            patch_data = {
                "transport_mode": "AIR",
                "doc_type": "AIR_WAYBILL",
                "doc_title": "AIR WAYBILL",
                "shipper": shipper.strip(),
                "consignee": consignee.strip(),
                "exporter_account_no": exporter_acct.strip(),
                "consignee_account_no": consignee_acct.strip(),
                "notify_party": notify.strip(),
                "accounting_info": accounting_info.strip(),
                "airport_departure": pol.strip(),
                "port_of_loading": pol.strip(),
                "airport_destination": pod.strip(),
                "port_of_discharge": pod.strip(),
                "first_carrier": first_carrier.strip(),
                "flight_no": flight_no.strip(),
                "flight_date": flight_date.isoformat(),
                "iata_code": iata_code.strip(),
                "currency": currency,
                "chgs_code": chgs_code,
                "declared_value_carriage": decl_carriage.strip(),
                "declared_value_customs": decl_customs.strip(),
                "package_qty": packages,
                "package_type": package_type.strip(),
                "gross_weight": gross,
                "chargeable_weight": chargeable_wt,
                "rate_class": rate_class.strip(),
                "description_of_goods": cargo_desc.strip(),
                "handling_info": handling_info.strip(),
                "sci": sci.strip(),
            }

        elif mode == "TRUCK":
            st.info("🚚 **Truck Waybill Mode (Single Consignment / FTL / LTL)** — Pre-filled from Truck Job.")
            section("1. Parties & Booking")
            a, b = st.columns(2)
            shipper = a.text_area("Shipper's Name and Address", _s(bl.get("shipper"), ""), height=85)
            consignee = b.text_area("Consignee Name and Address", _s(bl.get("consignee"), ""), height=85)
            c, d = st.columns(2)
            notify = c.text_area("Notify Party", _s(bl.get("notify_party"), "SAME AS CONSIGNEE"), height=75)
            agent = d.text_area("Delivery Agent", _s(bl.get("delivery_agent"), ""), height=75)
            c2, d2 = st.columns(2)
            booking_party = c2.text_input("Booking Party", _s(bl.get("booking_party") or bl.get("shipper"), ""))
            accounting_info = d2.text_input("Accounting Information", _s(bl.get("accounting_info"), "FREIGHT PREPAID / ISSUED AS PER AGREEMENT"))

            section("2. Routing & Vehicle")
            a, b = st.columns(2)
            origin = a.text_input("Origin", _s(bl.get("origin") or bl.get("port_of_loading"), "BANGKOK, THAILAND"))
            destination = b.text_input("Destination", _s(bl.get("destination") or bl.get("port_of_discharge"), "VIENTIANE, LAOS"))

            v1, v2, v3 = st.columns(3)
            move_type = v1.selectbox("Move Type", ["Full Truck Load (FTL)", "Less Truck Load (LTL)", "Single Consignment"], index=0 if "FTL" in str(bl.get("move_type", "FTL")) else 1)
            truck_plate = v2.text_input("Truck Plate No.", _s(bl.get("truck_plate"), ""))
            driver_name = v3.text_input("Driver Name & Phone", f"{_s(bl.get('driver_name'), '')} {_s(bl.get('driver_phone'), '')}".strip())

            section("3. Particulars Furnished by Shipper")
            a, b, c, d = st.columns(4)
            packages = a.number_input("No. of Pieces", min_value=0, value=int(bl.get("package_qty") or 1))
            package_type = b.text_input("Package Type", _s(bl.get("package_type"), "PKGS"))
            gross = c.number_input("Gross Weight (kgs)", min_value=0.0, value=float(bl.get("gross_weight") or 0), step=0.01)
            vol_wt = d.number_input("Vol. Wght (kgs)", min_value=0.0, value=float(bl.get("volumetric_weight") or 0), step=0.01)

            dimension = st.text_input("Dimension (LxWxH)", _s(bl.get("dimension"), "AS PER PACKING LIST"))
            cargo_desc = st.text_area("Description of Goods", _s(bl.get("description_of_goods"), "SAID TO CONTAIN GENERAL MERCHANDISE"), height=90)

            section("4. References & Additional Charges")
            r1, r2 = st.columns(2)
            invoice_details = r1.text_input("Invoice Details", _s(bl.get("invoice_details"), "INV-COMMERCIAL"))
            customer_ref = r2.text_input("Customer Ref #", _s(bl.get("customer_ref_no") or bl.get("job_no"), ""))

            patch_data = {
                "transport_mode": "TRUCK",
                "doc_type": "TRUCK_WAYBILL",
                "doc_title": "TRUCK WAYBILL",
                "shipper": shipper.strip(),
                "consignee": consignee.strip(),
                "notify_party": notify.strip(),
                "delivery_agent": agent.strip(),
                "booking_party": booking_party.strip(),
                "accounting_info": accounting_info.strip(),
                "origin": origin.strip(),
                "port_of_loading": origin.strip(),
                "destination": destination.strip(),
                "port_of_discharge": destination.strip(),
                "move_type": move_type,
                "truck_plate": truck_plate.strip(),
                "driver_name": driver_name.strip(),
                "package_qty": packages,
                "package_type": package_type.strip(),
                "gross_weight": gross,
                "volumetric_weight": vol_wt,
                "dimension": dimension.strip(),
                "description_of_goods": cargo_desc.strip(),
                "invoice_details": invoice_details.strip(),
                "customer_ref_no": customer_ref.strip(),
            }

        else:
            st.info("🚢 **Ocean Bill of Lading Mode** — Standard Maritime B/L with Container Manifest.")
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
            use_attached_sheet = st.checkbox("Print AS PER ATTACHED SHEET for long descriptions", value=bool(bl.get("use_attached_sheet")))

            patch_data = {
                "transport_mode": "SEA",
                "doc_type": "OCEAN_BL",
                "doc_title": "OCEAN BILL OF LADING",
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
                "use_attached_sheet": use_attached_sheet,
            }

        save = st.form_submit_button("Save Document Data", type="primary", width="stretch")

    if save:
        try:
            update_bl(bid, patch_data)
            st.success(f"{doc_title.title()} updated successfully.")
            st.rerun()
        except Exception as exc:
            st.error(f"Unable to modify document: {exc}")


def _preview(bl: Dict[str, Any]) -> None:
    job = {}
    if bl.get("job_no"):
        try:
            from managers.shipment_manager import get_shipment
            job = get_shipment(bl.get("job_no")) or {}
        except Exception:
            pass
    from pdf.bl_document_renderer import resolve_document_title
    doc_title = resolve_document_title(bl=bl, job=job)
    mode = str(bl.get("transport_mode") or ("AIR" if "AIR" in doc_title else "TRUCK" if "TRUCK" in doc_title else "SEA")).upper()

    section(f"{doc_title.title()} Preview")
    
    if mode == "AIR":
        st.caption("✈️ Official IATA Standard House Air Waybill (45-box standard) branded for NATTAYARAAT CO., LTD.")
        p1, p2 = st.columns(2)
        with p1:
            st.markdown(f"**Shipper's Name and Address**\n\n{_s(bl.get('shipper'))}\n\n**Shipper Account:** `{_s(bl.get('exporter_account_no'), '—')}`")
            st.markdown(f"**Consignee's Name and Address**\n\n{_s(bl.get('consignee'))}\n\n**Consignee Account:** `{_s(bl.get('consignee_account_no'), '—')}`")
            st.markdown(f"**Notify Party**\n\n{_s(bl.get('notify_party'), 'SAME AS CONSIGNEE')}")
        with p2:
            st.markdown(f"**HAWB No.** `{_s(bl.get('bl_no'))}`\n\n**Not Negotiable Air Waybill Issued by**\n\n**NATTAYARAAT CO., LTD.**")
            st.markdown(f"**Agent's IATA Code:** `{_s(bl.get('iata_code'), '33-4-7890/0014')}` · **Account No.:** `{_s(bl.get('agent_account_no'), 'BKK-0988')}`")
            st.markdown(f"**Accounting Information:**\n\n{_s(bl.get('accounting_info'))}")

        st.markdown("##### Flight & Routing Matrix")
        st.dataframe(pd.DataFrame([{
            "Airport of Departure": _s(bl.get('airport_departure') or bl.get('port_of_loading')),
            "By First Carrier": _s(bl.get('first_carrier')),
            "Airport of Destination": _s(bl.get('airport_destination') or bl.get('port_of_discharge')),
            "Flight / Date": f"{_s(bl.get('flight_no'))} / {_s(bl.get('flight_date') or bl.get('etd'))}",
            "Currency": _s(bl.get('currency'), 'USD'),
            "CHGS": _s(bl.get('chgs_code'), 'PP'),
            "Declared (Carriage)": _s(bl.get('declared_value_carriage'), 'NVD'),
            "Declared (Customs)": _s(bl.get('declared_value_customs'), 'NCV'),
            "SCI": _s(bl.get('sci'), 'TH-EXP'),
        }]), hide_index=True, width="stretch")

        st.markdown("##### Cargo & Rating Table")
        st.dataframe(pd.DataFrame([{
            "Pieces RCP": _s(bl.get('package_qty'), '1'),
            "Gross Weight (KG)": float(bl.get('gross_weight') or 0),
            "Rate Class": _s(bl.get('rate_class'), 'Q'),
            "Chargeable Weight (KG)": float(bl.get('chargeable_weight') or bl.get('gross_weight') or 0),
            "Rate / Charge": _s(bl.get('rate_charge'), 'AS AGREED'),
            "Total": _s(bl.get('total_charge'), 'AS AGREED'),
            "Nature and Quantity of Goods": _s(bl.get('description_of_goods')),
        }]), hide_index=True, width="stretch")

    elif mode == "TRUCK":
        st.caption("🚚 Official Truck Waybill (Single Consignment, Full Truck Load & Less Truck Load) branded for NATTAYARAAT CO., LTD.")
        p1, p2 = st.columns(2)
        with p1:
            st.markdown(f"**Shipper's Name and Address**\n\n{_s(bl.get('shipper'))}\n\n**Consignee Name and Address**\n\n{_s(bl.get('consignee'))}\n\n**Notify Party**\n\n{_s(bl.get('notify_party'))}")
        with p2:
            st.markdown(f"**TRUCK WAY BILL NUMBER** `{_s(bl.get('truck_waybill_no') or bl.get('bl_no'))}`\n\n**Job Ref No. #** `{_s(bl.get('job_no'))}`\n\n**Issued by:** **NATTAYARAAT CO., LTD.**")
            st.markdown(f"**Delivery Agent:** {_s(bl.get('delivery_agent'))}\n\n**Booking Party:** {_s(bl.get('booking_party'))}")

        st.markdown("##### Transport & Vehicle Details")
        st.dataframe(pd.DataFrame([{
            "Origin": _s(bl.get('origin') or bl.get('port_of_loading')),
            "Destination": _s(bl.get('destination') or bl.get('port_of_discharge')),
            "Move Type": _s(bl.get('move_type'), 'Full Truck Load (FTL)'),
            "Truck Plate": _s(bl.get('truck_plate')),
            "Driver": f"{_s(bl.get('driver_name'))} {_s(bl.get('driver_phone'))}".strip(),
            "Invoice Details": _s(bl.get('invoice_details')),
            "Customer Ref #": _s(bl.get('customer_ref_no')),
        }]), hide_index=True, width="stretch")

        st.markdown("##### Particulars Furnished by Shipper")
        st.dataframe(pd.DataFrame([{
            "No of Pieces": f"{_s(bl.get('package_qty'), '1')} {_s(bl.get('package_type'), 'PKGS')}",
            "Gross Weight (kgs)": float(bl.get('gross_weight') or 0),
            "Vol. Wght (kgs)": float(bl.get('volumetric_weight') or 0),
            "Dimensions": _s(bl.get('dimension')),
            "Description": _s(bl.get('description_of_goods')),
        }]), hide_index=True, width="stretch")

    else:
        st.caption("🚢 Official Ocean Bill of Lading with Maritime Container & Seal Manifest (NATTAYARAAT CO., LTD.).")
        p1, p2 = st.columns(2)
        with p1:
            st.markdown(f"**Shipper**\n\n{_s(bl.get('shipper'))}\n\n**Consignee**\n\n{_s(bl.get('consignee'))}\n\n**Notify Party**\n\n{_s(bl.get('notify_party'))}")
        with p2:
            st.markdown(f"**B/L No.** `{_s(bl.get('bl_no'))}`\n\n**For Delivery of Goods Please Apply to**\n\n{_s(bl.get('delivery_agent'))}")
            st.markdown(f"**Originals:** {_s(bl.get('number_of_originals'), '3 (THREE)')} · **Place & Date:** {_s(bl.get('place_of_issue'))}, {_s(bl.get('bl_date'))}")

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
    query = a.text_input("Search", placeholder="B/L, Job, Shipper, Consignee, Mode, POL or POD", key="bl_v2_search")
    
    if can_edit:
        if b.button("＋ Issue New Document", type="primary", width="stretch", key="btn_toggle_new_bl"):
            st.session_state["bl_show_new_form"] = not st.session_state.get("bl_show_new_form", False)
            st.rerun()

    if st.session_state.get("bl_show_new_form"):
        _new(user)

    if query.strip():
        rows = [r for r in rows if query.strip().lower() in str(r).lower()]

    section("Multi-Modal Waybill & B/L Overview")
    _consol_summary(rows)

    def _badge(r):
        mode = str(r.get("transport_mode") or "").upper()
        if mode == "AIR" or str(r.get("job_type", "")).upper() in ("AE", "AI"):
            return "✈️ Air Waybill"
        elif mode == "TRUCK" or str(r.get("job_type", "")).upper() in ("TE", "TI"):
            return "🚚 Truck Waybill"
        return "🚢 Ocean B/L"

    section("Document Ledger")
    st.dataframe(
        pd.DataFrame([
            {
                "Type": _badge(r),
                "Doc No.": _s(r.get("bl_no")),
                "Job Ref": _s(r.get("job_no")),
                "Seq": r.get("consol_seq") or 1,
                "Shipper": _s(r.get("shipper")),
                "Consignee": _s(r.get("consignee")),
                "Origin / POL": _s(r.get("origin") or r.get("airport_departure") or r.get("port_of_loading")),
                "Destination / POD": _s(r.get("destination") or r.get("airport_destination") or r.get("port_of_discharge")),
                "Carrier / Vessel": _s(r.get("first_carrier") or r.get("truck_plate") or r.get("vessel")),
                "Status": _s(r.get("approval_status"), "Draft"),
            }
            for r in rows
        ]),
        hide_index=True,
        width="stretch",
    )

    ids = [int(r["id"]) for r in rows if r.get("id") is not None]
    if not ids:
        st.info("No documents found.")
        return

    labels = {int(r["id"]): f"{_badge(r)}: {r.get('bl_no')} · {r.get('job_no')} (#{r.get('consol_seq', 1)}) · {r.get('approval_status', 'Draft')}" for r in rows if r.get("id") is not None}
    default = ids.index(st.session_state.get("bl_v2_selected")) if st.session_state.get("bl_v2_selected") in ids else 0
    selected = st.selectbox("Choose Document", ids, index=default, format_func=lambda x: labels[x], key="bl_v2_selected_box")
    bl = get_bl(selected)
    if not bl:
        st.error("Selected document is no longer available.")
        return

    st.session_state["bl_v2_selected"] = selected
    status = _s(bl.get("approval_status"), "Draft")
    mode_label = _badge(bl)

    section("Document Summary")
    m1, m2, m3 = st.columns(3)
    m1.metric("Document No.", _s(bl.get("bl_no")))
    m2.metric("Job Ref", _s(bl.get("job_no")))
    m3.metric("Type & Status", f"{mode_label} ({status})")

    m4, m5, m6 = st.columns(3)
    m4.metric("Consolidation Seq", f"#{bl.get('consol_seq') or 1}")
    m5.metric("Origin / POL", _s(bl.get("origin") or bl.get("airport_departure") or bl.get("port_of_loading")))
    m6.metric("Destination / POD", _s(bl.get("destination") or bl.get("airport_destination") or bl.get("port_of_discharge")))

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
        st.caption(f"PDF auto-routes to {mode_label} template.")

    tabs = st.tabs(["Document Data", "Interactive Preview", "Shipping Instruction (S/I)"])
    with tabs[0]:
        if can_edit and status in {"Draft", "Pending Approval"}:
            _edit(bl)
        else:
            _preview(bl)
    with tabs[1]:
        _preview(bl)
    with tabs[2]:
        section("Shipping Instruction (S/I) for Line / Carrier")
        si_mode_choice = st.radio(
            "S/I Issuance Mode",
            ["Direct Master Document to Customer", "House Document Mode (Nattayaarat Shipper & Overseas Agent Consignee)"],
            index=1,
            key=f"bl_si_mode_choice_{selected}",
            horizontal=True
        )
        si_mode = "hbl" if "House" in si_mode_choice else "direct"
        
        from managers.si_service import assemble_si_payload
        try:
            job_no = bl.get("job_no")
            si_data = assemble_si_payload(job_no, si_mode=si_mode)
            
            p_col1, p_col2 = st.columns(2)
            with p_col1:
                st.markdown(f"**Shipper (on Master)**\n\n{_s(si_data.get('shipper'))}\n\n**Consignee (on Master)**\n\n{_s(si_data.get('consignee'))}")
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

