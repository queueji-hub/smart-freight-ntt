"""Streamlined Booking workspace for Phase 30.

Supports dynamic transport modes:
- Sea Freight - CY/CY (FCL)
- Sea Freight - CFS/CFS (LCL)
- Air Freight
- Truck / Cross-Border Freight
"""
from __future__ import annotations

import os
from datetime import date, timedelta
from typing import Any, Dict, List

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
from managers.master_data_manager import list_distinct_job_values
from ui.design_system import page_header, section

CONTAINER_TYPES = ["20'GP", "40'GP", "40'HC", "45'HC", "20'OT", "40'OT", "20'FR", "40'FR", "20'RF", "40'RF", "20'Tank", "40'Tank"]
PACKAGE_TYPES = ["Cartons", "Pallets", "Wooden Cases", "Crates", "Bags", "Drums", "Rolls", "Boxes", "Packages", "Pieces", "Units", "Bulk"]
TRUCK_TYPES = ["4-Wheel Truck (4W)", "6-Wheel Truck (6W)", "10-Wheel Truck (10W)", "Trailer 20'", "Trailer 40'", "Flatbed", "Box Truck (ตู้ทึบ)", "Reefer Truck (ตู้เย็น)", "Lowbed"]

MODE_CONFIG = {
    "SEA_FCL": {
        "label": "🌊 Sea Freight - CY/CY (FCL - เต็มตู้คอนเทนเนอร์)",
        "mode": "SEA",
        "cargo_type": "FCL",
        "service_term": "CY/CY",
        "carrier_label": "Shipping Line / Liner (สายเรือ)",
        "carrier_placeholder": "e.g. ONE, MSC, COSCO, MAERSK, EVERGREEN, RCL, SITC, WAN HAI...",
        "pol_label": "POL / Port of Loading (ท่าเรือต้นทาง) *",
        "pol_placeholder": "e.g. Laem Chabang, Bangkok, PAT...",
        "ts_label": "Transshipment Port (ท่าถ่ายลำ / VIA - ถ้ามี)",
        "ts_placeholder": "e.g. Singapore, Port Klang, Busan, Hong Kong...",
        "pod_label": "POD / Port of Discharge (ท่าเรือปลายทาง) *",
        "pod_placeholder": "e.g. Tokyo, Shanghai, Los Angeles, Hamburg, Rotterdam...",
    },
    "SEA_LCL": {
        "label": "🌊 Sea Freight - CFS/CFS (LCL - รวมตู้ / สินค้าไม่เต็มตู้)",
        "mode": "SEA",
        "cargo_type": "LCL",
        "service_term": "CFS/CFS",
        "carrier_label": "Co-loader / Consolidator / Liner (ผู้ให้บริการรวมตู้ / สายเรือ)",
        "carrier_placeholder": "e.g. Vanguard Logistics, ECU Worldwide, Allcargo, RCL, Schenker...",
        "pol_label": "POL / Port of Loading (ท่าเรือต้นทาง) *",
        "pol_placeholder": "e.g. Bangkok CFS, Laem Chabang CFS, PAT CFS...",
        "ts_label": "Transshipment Port (ท่าถ่ายลำ / VIA - ถ้ามี)",
        "ts_placeholder": "e.g. Singapore, Busan, Hong Kong...",
        "pod_label": "POD / Port of Discharge (ท่าเรือปลายทาง) *",
        "pod_placeholder": "e.g. Tokyo, Singapore, Busan, Los Angeles...",
    },
    "AIR": {
        "label": "✈️ Air Freight (การขนส่งทางอากาศ)",
        "mode": "AIR",
        "cargo_type": "AIR",
        "service_term": "AIR",
        "carrier_label": "Airline / Air Carrier (สายการบิน)",
        "carrier_placeholder": "e.g. Thai Airways (TG), Emirates (EK), Qatar Airways (QR), Singapore Airlines (SQ)...",
        "pol_label": "AOD / Airport of Departure (สนามบินต้นทาง) *",
        "pol_placeholder": "e.g. BKK - Suvarnabhumi, DMK, HKT...",
        "ts_label": "Transshipment Airport (สนามบินเปลี่ยนเครื่อง - ถ้ามี)",
        "ts_placeholder": "e.g. SIN, DXB, DOH, HKG, ICN...",
        "pod_label": "AOA / Airport of Arrival (สนามบินปลายทาง) *",
        "pod_placeholder": "e.g. NRT - Tokyo, LAX, FRA, LHR, PVG, JFK...",
    },
    "TRUCK": {
        "label": "🚚 Truck / Cross-Border Freight (การขนส่งทางบก / รถบรรทุกข้ามแดน)",
        "mode": "TRUCK",
        "cargo_type": "TRUCK",
        "service_term": "DOOR-TO-DOOR",
        "carrier_label": "Transporter / Trucking Co. (ผู้ให้บริการขนส่งทางรถ)",
        "carrier_placeholder": "e.g. NTT Logistics, SCG Logistics, Flash, DHL Supply Chain...",
        "pol_label": "Place of Origin / Factory (สถานที่รับสินค้า / โรงงาน) *",
        "pol_placeholder": "e.g. Factory Samut Prakan, Bangna KM.19...",
        "ts_label": "Border Customs Checkpoint (ด่านศุลกากรชายแดน - ถ้ามี)",
        "ts_placeholder": "e.g. ด่านสะเดา, ด่านมุกดาหาร, ด่านหนองคาย, ด่านอรัญประเทศ, ด่านแม่สอด...",
        "pod_label": "Place of Destination (สถานที่ส่งมอบปลายทาง) *",
        "pod_placeholder": "e.g. Vientiane Laos, Phnom Penh Cambodia, Yangon Myanmar, Kuala Lumpur...",
    },
}


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
    from managers.master_data_crud_manager import list_parties
    from managers.salesperson_manager import list_salespersons
    
    parties_cust = list_parties("CUSTOMER", active_only=True) or []
    legacy_cust = list_customers() or []
    customer_dict = {}
    for r in parties_cust:
        cid = int(r["id"])
        cname = r.get("display_name") or r.get("legal_name") or str(cid)
        customer_dict[cid] = {"id": cid, "company_name": f"{r.get('party_code')} — {cname}"}
    for r in legacy_cust:
        cid = int(r["id"])
        if cid not in customer_dict:
            cname = r.get("display_name") or r.get("company_name") or str(cid)
            customer_dict[cid] = {"id": cid, "company_name": f"{r.get('customer_code', '')} — {cname}".strip(" —")}
    customers = list(customer_dict.values())

    sales_list = list_salespersons(active_only=True) or []
    sales = [{"id": s.get("id"), "username": s.get("name"), "full_name": f"{s.get('sales_code')} — {s.get('name')}".strip(" —")} for s in sales_list]

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
        from pdf.booking_pdf import generate_booking_pdf

        path = generate_booking_pdf(record)
        if path and os.path.exists(path):
            with open(path, "rb") as fh:
                st.session_state[f"{key_prefix}_pdf_bytes"] = fh.read()
            st.session_state[f"{key_prefix}_pdf_name"] = os.path.basename(path)
    except Exception as exc:
        st.error(f"Unable to create PDF: {exc}")


def _render_pdf_action(record: Dict[str, Any], key_prefix: str) -> None:
    if st.button("📄 Export PDF", key=f"prepare_pdf_{key_prefix}", type="primary", width="stretch"):
        _prepare_pdf(record, key_prefix)
    pdf_bytes = st.session_state.get(f"{key_prefix}_pdf_bytes")
    if pdf_bytes:
        st.download_button(
            "⬇️ Download PDF",
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

    section("1. Transport Mode & Service Selection (เลือกรูปแบบการขนส่ง)")
    mode_options = list(MODE_CONFIG.keys())
    selected_mode_key = st.radio(
        "Transport Mode (รูปแบบการขนส่ง)",
        mode_options,
        format_func=lambda k: MODE_CONFIG[k]["label"],
        horizontal=True,
        key="booking_create_mode_radio",
    )
    mcfg = MODE_CONFIG[selected_mode_key]
    mode = mcfg["mode"]
    cargo_type = mcfg["cargo_type"]
    service_term = mcfg["service_term"]

    with st.form("booking_v2_create_form"):
        section("2. Booking General Information")
        c1, c2, c3 = st.columns(3)
        with c1:
            customer_id = st.selectbox("Customer * (ลูกค้า)", customer_ids, format_func=lambda x: customer_map[x]) if customer_ids else None
        with c2:
            sales_id = st.selectbox("Sales Person (พนักงานขาย)", sales_ids, format_func=lambda x: sales_map[x]) if sales_ids else None
        with c3:
            job_type_opts = ["SE", "SI"] if mode == "SEA" else (["AE", "AI"] if mode == "AIR" else ["TE", "TI"])
            job_type = st.selectbox("Job Type * (ประเภทงาน)", job_type_opts, format_func=lambda x: JOB_TYPES.get(x, x))

        b1, b2 = st.columns(2)
        with b1:
            carrier_ref_label = "Carrier Booking No. * (เลขที่บุ๊คกิ้งสายเรือ)" if mode == "SEA" and cargo_type == "FCL" else (
                "Co-loader Booking No. * (เลขที่บุ๊คกิ้งผู้รวบรวมตู้)" if mode == "SEA" and cargo_type == "LCL" else (
                    "Airline Booking / MAWB No. * (เลขที่บุ๊คกิ้งสายการบิน)" if mode == "AIR" else "Waybill / Truck Booking Ref *"
                )
            )
            carrier_booking_no = st.text_input(carrier_ref_label, placeholder="e.g. ONEYBK123456 / TG-987654 / WB-8899")
        with b2:
            quotation_no = st.text_input("Quotation Ref (อ้างอิงใบเสนอราคา)", placeholder="e.g. QT-2608-0001 (Optional)")

        sh1, sh2, sh3 = st.columns(3)
        with sh1:
            shipper = st.text_input("Shipper (ผู้ส่งสินค้า - ไม่บังคับ)")
        with sh2:
            consignee = st.text_input("Consignee (ผู้รับสินค้า - ไม่บังคับ)")
        with sh3:
            notify_party = st.text_input("Notify Party (ผู้รับแจ้งเมื่อถึงปลายทาง - ถ้ามี)")

        section("3. Routing & Schedule")
        r1, r2, r3, r4 = st.columns(4)
        with r1:
            pol_value = st.text_input(mcfg["pol_label"], placeholder=mcfg["pol_placeholder"])
        with r2:
            trans_value = st.text_input(mcfg["ts_label"], placeholder=mcfg["ts_placeholder"])
        with r3:
            pod_value = st.text_input(mcfg["pod_label"], placeholder=mcfg["pod_placeholder"])
        with r4:
            final_dest = st.text_input("Place of Delivery / Final Destination (ปลายทางสุดท้าย)", placeholder="Optional")

        l_col, v_col, voy_col = st.columns(3)
        with l_col:
            carrier_value = st.text_input(mcfg["carrier_label"], placeholder=mcfg["carrier_placeholder"])
        
        # Mode-specific routing & carrier details
        mother_value = ""
        mother_voyage_value = ""
        flight_no = ""
        flight_date_val = None
        mawb_no = ""
        hawb_no = ""
        truck_type_val = ""
        truck_plate_val = ""
        driver_name_val = ""
        driver_phone_val = ""
        loading_date_val = None
        delivery_date_val = None

        if mode == "SEA":
            with v_col:
                vessel_value = st.text_input("Feeder Vessel / Ocean Vessel (ชื่อเรือ)", placeholder="e.g. EVER GIVEN / SITC NINGBO")
            with voy_col:
                voyage_value = st.text_input("Voyage No. (เที่ยวเรือ)", placeholder="e.g. 0123N")

            if cargo_type == "FCL":
                mv_col, mvoy_col = st.columns(2)
                with mv_col:
                    mother_value = st.text_input("Mother Vessel (เรือแม่ / ต่อเที่ยว - ถ้ามี)", placeholder="e.g. COSCO SHIPPING TAURUS")
                with mvoy_col:
                    mother_voyage_value = st.text_input("Mother Voyage No. (เที่ยวเรือแม่)", placeholder="e.g. 0456W")
        elif mode == "AIR":
            with v_col:
                flight_no = st.text_input("Flight No. (เที่ยวบิน)", placeholder="e.g. TG910 / EK384")
                vessel_value = flight_no
            with voy_col:
                flight_date_val = st.date_input("Flight Date (วันที่เที่ยวบิน)", value=date.today())
                voyage_value = flight_date_val.isoformat() if flight_date_val else ""

            af1, af2 = st.columns(2)
            with af1:
                mawb_no = st.text_input("Master AWB No. (MAWB)", placeholder="e.g. 217-12345678")
            with af2:
                hawb_no = st.text_input("House AWB No. (HAWB)", placeholder="e.g. HAWB-001234")
        elif mode == "TRUCK":
            with v_col:
                truck_type_val = st.selectbox("Truck Type (ประเภทรถ)", TRUCK_TYPES)
                vessel_value = truck_type_val
            with voy_col:
                truck_plate_val = st.text_input("Truck Plate No. (ทะเบียนหัว/หาง)", placeholder="e.g. 70-1234 กทม / 71-5678")
                voyage_value = truck_plate_val

            tr1, tr2 = st.columns(2)
            with tr1:
                driver_name_val = st.text_input("Driver Name (ชื่อคนขับ)", placeholder="e.g. นายสมชาย ใจดี")
            with tr2:
                driver_phone_val = st.text_input("Driver Mobile (เบอร์โทรคนขับ)", placeholder="e.g. 081-234-5678")

        etd_default = date.today()
        eta_default = etd_default + timedelta(days=14 if mode == "SEA" else (3 if mode == "AIR" else 5))
        etd_col, eta_col = st.columns(2)
        with etd_col:
            etd_value = st.date_input("ETD / Departure Date (วันที่ออก)", etd_default)
        with eta_col:
            eta_value = st.date_input("ETA / Arrival Date (วันที่ถึง)", eta_default)

        section("4. Cargo Specifications & Equipment")
        gross_weight = 0.0
        measurement_cbm = 0.0
        chargeable_weight = 0.0
        package_qty = 0
        package_unit = "PKGS"
        container_summary = ""
        commodity = st.text_input("Commodity / Cargo Description (ชื่อสินค้า/รายละเอียด)", placeholder="e.g. General Cargo, Auto Parts, Garments...")

        if mode == "SEA" and cargo_type == "FCL":
            st.write("**Equipment Details (ตารางประเภทและจำนวนตู้คอนเทนเนอร์)**")
            table = st.data_editor(
                pd.DataFrame([{"type": "40'HC", "qty": 1}]),
                num_rows="dynamic",
                hide_index=True,
                column_config={
                    "type": st.column_config.SelectboxColumn("Container Type (ประเภทตู้)", options=CONTAINER_TYPES, required=True),
                    "qty": st.column_config.NumberColumn("Qty (จำนวนตู้)", min_value=1, step=1, required=True),
                },
                key="booking_v2_fcl_containers",
            )
            container_summary = _container_summary(table)
            w1, w2 = st.columns(2)
            with w1:
                gross_weight = st.number_input("Gross Weight (KG) - น้ำหนักรวมสินค้า", min_value=0.0, step=1.0, value=0.0)
            with w2:
                measurement_cbm = st.number_input("Volume (CBM) - ปริมาตร (ไม่บังคับสำหรับ FCL)", min_value=0.0, step=0.01, value=0.0)
        elif mode == "SEA" and cargo_type == "LCL":
            cg1, cg2, cg3, cg4 = st.columns(4)
            with cg1:
                package_qty = st.number_input("Package Qty (จำนวนหีบห่อ) *", min_value=1, step=1, value=1)
            with cg2:
                package_unit = st.selectbox("Package Unit (หน่วยหีบห่อ)", PACKAGE_TYPES)
            with cg3:
                gross_weight = st.number_input("Gross Weight (KG) *", min_value=0.0, step=1.0, value=100.0)
            with cg4:
                measurement_cbm = st.number_input("Volume (CBM) * (จำเป็นสำหรับ LCL)", min_value=0.01, step=0.01, value=1.0)
        elif mode == "AIR":
            ag1, ag2, ag3, ag4 = st.columns(4)
            with ag1:
                package_qty = st.number_input("Package Qty (จำนวนหีบห่อ) *", min_value=1, step=1, value=1)
            with ag2:
                package_unit = st.selectbox("Package Unit (หน่วยหีบห่อ)", PACKAGE_TYPES)
            with ag3:
                gross_weight = st.number_input("Gross Weight (KG) *", min_value=0.0, step=0.1, value=50.0)
            with ag4:
                measurement_cbm = st.number_input("Volume (CBM)", min_value=0.0, step=0.001, value=0.300)

            ch_col, _ = st.columns(2)
            with ch_col:
                calc_ch_wt = max(gross_weight, measurement_cbm * 167.0)
                chargeable_weight = st.number_input("Chargeable Weight (KG) *", min_value=0.0, step=0.1, value=float(calc_ch_wt))
        elif mode == "TRUCK":
            tg1, tg2, tg3, tg4 = st.columns(4)
            with tg1:
                package_qty = st.number_input("Package Qty (จำนวนหีบห่อ)", min_value=0, step=1, value=1)
            with tg2:
                package_unit = st.selectbox("Package Unit (หน่วยหีบห่อ)", PACKAGE_TYPES)
            with tg3:
                gross_weight = st.number_input("Gross Weight (KG)", min_value=0.0, step=1.0, value=0.0)
            with tg4:
                measurement_cbm = st.number_input("Volume (CBM)", min_value=0.0, step=0.01, value=0.0)

        section("5. Receiving & Depot Cut-off Schedule")
        cy_date = cy_place = cfs_date = cfs_place = return_date = return_place = None
        if mode == "SEA" and cargo_type == "FCL":
            cy1, cy2 = st.columns(2)
            with cy1:
                cy_place = st.text_input("CY Return Terminal / Depot (ลานคืนตู้หนัก / ท่าเทียบเรือ)", placeholder="e.g. Laem Chabang Terminal B4, B3, C1, PAT...")
            with cy2:
                cy_date = st.date_input("CY Cut-off Date (วันปิดรับตู้หนักที่ท่าเรือ)", value=None)

            ret1, ret2 = st.columns(2)
            with ret1:
                return_place = st.text_input("Empty Container Pickup Depot (ลานรับตู้เปล่า)", placeholder="e.g. LAT KRABANG ICD, PAT DEPOT, SIAM CONTAINER...")
            with ret2:
                return_date = st.date_input("Container Return Free Time (วันกำหนดคืนตู้)", value=None)
        elif mode == "SEA" and cargo_type == "LCL":
            cfs1, cfs2 = st.columns(2)
            with cfs1:
                cfs_place = st.text_input("CFS Receiving Warehouse (คลังรับสินค้า CFS)", placeholder="e.g. PAT CFS WAREHOUSE, LCB CFS DEPOT, SCHENKER CFS...")
            with cfs2:
                cfs_date = st.date_input("CFS Cut-off Date (วันปิดรับสินค้า CFS เข้าคลัง)", value=None)
        elif mode == "AIR":
            air1, air2 = st.columns(2)
            with air1:
                cfs_place = st.text_input("Cargo Acceptance Terminal (คลังรับสินค้าสนามบิน)", placeholder="e.g. TG Cargo Terminal Suvarnabhumi, BFS Cargo...")
            with air2:
                cfs_date = st.date_input("Airport Cargo Cut-off Date (วันปิดรับสินค้าที่สนามบิน)", value=None)
        elif mode == "TRUCK":
            trk1, trk2 = st.columns(2)
            with trk1:
                loading_date_val = st.date_input("Loading Date (วันนัดรับสินค้า/ขึ้นของ)", value=etd_default)
            with trk2:
                delivery_date_val = st.date_input("Delivery Date (วันนัดส่งสินค้า/ส่งมอบ)", value=eta_default)

        freight_term = st.selectbox("Freight Term", ["", "Prepaid", "Collect"])
        remark = st.text_area("Remarks & Special Instructions (หมายเหตุและคำสั่งปฏิบัติการ)", placeholder="ระบุเงื่อนไขพิเศษ เช่น ต้องคลุมผ้าใบ, คุมอุณหภูมิ, วางซ้อนไม่ได้...")
        submitted = st.form_submit_button("💾 Save Booking Confirmation", type="primary", width="stretch")

    if submitted:
        errors = []
        if customer_id is None:
            errors.append("Customer is required (กรุณาเลือกลูกค้า).")
        if not pol_value.strip():
            errors.append("Origin / POL is required (กรุณาระบุต้นทาง).")
        if not pod_value.strip():
            errors.append("Destination / POD is required (กรุณาระบุปลายทาง).")
        if eta_value < etd_value:
            errors.append("ETA cannot be earlier than ETD (วันถึงต้องไม่อยู่ก่อนวันออก).")
        if mode == "SEA" and cargo_type == "FCL" and not container_summary:
            errors.append("At least one container type is required for FCL (กรุณาระบุประเภทตู้สำหรับ FCL).")
        if mode == "SEA" and cargo_type == "LCL" and measurement_cbm <= 0:
            errors.append("Volume (CBM) is required for LCL (กรุณาระบุปริมาตร CBM สำหรับ LCL).")
        if mode == "AIR" and chargeable_weight <= 0:
            errors.append("Chargeable Weight is required for Air (กรุณาระบุน้ำหนัก Chargeable Weight สำหรับ Air).")

        if errors:
            for error in errors:
                st.error(error)
            return

        customer_name = customer_map.get(customer_id, "")
        sales_name = sales_map.get(sales_id, "") if sales_id else ""

        payload = {
            "booking_no": None,
            "carrier_booking_no": carrier_booking_no.strip() or None,
            "quotation_id": None,
            "quotation_no": quotation_no.strip() or None,
            "job_type": job_type,
            "mode": mode,
            "service_term": service_term,
            "service_type": service_term,
            "customer_id": customer_id,
            "customer_name": customer_name,
            "sales_id": sales_id,
            "sales_person": sales_name,
            "shipper": shipper.strip() or None,
            "consignee": consignee.strip() or None,
            "notify_party": notify_party.strip() or None,
            "pol": pol_value.strip(),
            "pod": pod_value.strip(),
            "final_destination": final_dest.strip() or None,
            "transhipment_port": trans_value.strip() or None,
            "liner": carrier_value.strip() or None,
            "carrier": carrier_value.strip() or None,
            "vessel": vessel_value.strip() or None,
            "voyage": voyage_value.strip() or None,
            "m_vessel": mother_value.strip() or None,
            "mother_vessel": mother_value.strip() or None,
            "m_voyage": mother_voyage_value.strip() or None,
            "mother_voyage": mother_voyage_value.strip() or None,
            "flight_no": flight_no.strip() or None,
            "flight_date": flight_date_val.isoformat() if flight_date_val else None,
            "mawb_no": mawb_no.strip() or None,
            "hawb_no": hawb_no.strip() or None,
            "truck_type": truck_type_val or None,
            "truck_plate": truck_plate_val.strip() or None,
            "driver_name": driver_name_val.strip() or None,
            "driver_phone": driver_phone_val.strip() or None,
            "loading_date": loading_date_val.isoformat() if loading_date_val else None,
            "delivery_date": delivery_date_val.isoformat() if delivery_date_val else None,
            "etd": etd_value.isoformat(),
            "eta": eta_value.isoformat(),
            "cargo_type": cargo_type,
            "gross_weight": gross_weight or None,
            "measurement_cbm": measurement_cbm or None,
            "chargeable_weight": chargeable_weight or None,
            "package_qty": int(package_qty or 0) or None,
            "package_unit": package_unit,
            "container_summary": container_summary or None,
            "commodity": commodity.strip() or None,
            "freight_term": freight_term or None,
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
            st.session_state.pop("booking_v2_create_mode", None)
            st.session_state["booking_v2_selected"] = booking_no
            st.success(f"🎉 Booking {booking_no} created successfully.")
            st.rerun()
        except Exception as exc:
            st.error(f"Unable to save booking: {exc}")


def _render_selected(selected: Dict[str, Any], user: Dict[str, Any], can_edit: bool):
    booking_no = _s(selected.get("booking_no"))
    current_status = _s(selected.get("status"), "DRAFT").upper()
    mode = _s(selected.get("mode") or ("AIR" if "AE" in str(selected.get("job_type")) or "AI" in str(selected.get("job_type")) else ("TRUCK" if "TE" in str(selected.get("job_type")) or "TI" in str(selected.get("job_type")) else "SEA")))
    cargo_type = _s(selected.get("cargo_type"), "FCL" if mode == "SEA" else mode)

    section(f"Booking Control Center: {booking_no}")
    summary = st.columns(5)
    summary[0].metric("Booking No.", booking_no or "—")
    summary[1].metric("Carrier Booking Ref", _s(selected.get("carrier_booking_no") or selected.get("mawb_no"), "—"))
    summary[2].metric("Customer", _s(selected.get("customer_name"), "—"))
    summary[3].metric("Mode / Term", f"{mode} ({_s(selected.get('service_term') or cargo_type)})")
    summary[4].metric("Status", current_status)

    section("Routing & Transport Execution")
    cols = st.columns(5)
    if mode == "SEA":
        cols[0].write(f"**Liner / Carrier**\n\n{_s(selected.get('liner') or selected.get('carrier'), '—')}")
        cols[1].write(f"**Feeder Vessel / Voy**\n\n{_s(selected.get('vessel'), '—')} {_s(selected.get('voyage'), '')}".strip())
        cols[2].write(f"**Mother Vessel / Voy**\n\n{_s(selected.get('mother_vessel') or selected.get('m_vessel'), '—')} {_s(selected.get('mother_voyage') or selected.get('m_voyage'), '')}".strip())
        cols[3].write(f"**POL ➔ POD**\n\n{_s(selected.get('pol'), '—')} ➔ {_s(selected.get('pod'), '—')}")
        cols[4].write(f"**Transshipment Port**\n\n{_s(selected.get('transhipment_port'), '—')}")
    elif mode == "AIR":
        cols[0].write(f"**Airline**\n\n{_s(selected.get('carrier') or selected.get('liner'), '—')}")
        cols[1].write(f"**Flight No / Date**\n\n{_s(selected.get('flight_no') or selected.get('vessel'), '—')}")
        cols[2].write(f"**MAWB / HAWB**\n\n{_s(selected.get('mawb_no') or selected.get('carrier_booking_no'), '—')} / {_s(selected.get('hawb_no'), '—')}")
        cols[3].write(f"**AOD ➔ AOA**\n\n{_s(selected.get('pol'), '—')} ➔ {_s(selected.get('pod'), '—')}")
        cols[4].write(f"**Transshipment Airport**\n\n{_s(selected.get('transhipment_port'), '—')}")
    else:
        cols[0].write(f"**Transporter**\n\n{_s(selected.get('carrier') or selected.get('liner'), '—')}")
        cols[1].write(f"**Truck Plate**\n\n{_s(selected.get('truck_plate') or selected.get('voyage'), '—')}")
        cols[2].write(f"**Driver & Mobile**\n\n{_s(selected.get('driver_name'), '—')} ({_s(selected.get('driver_phone'), '—')})")
        cols[3].write(f"**Route & Border**\n\n{_s(selected.get('pol'), '—')} ➔ {_s(selected.get('pod'), '—')}")
        cols[4].write(f"**Border Checkpoint**\n\n{_s(selected.get('transhipment_port'), '—')}")

    section("Cargo & Receiving Schedule")
    if mode == "SEA" and cargo_type == "FCL":
        c_col1, c_col2 = st.columns([1.5, 2])
        with c_col1:
            st.info(f"📦 **Containers:** {_s(selected.get('container_summary'), 'No containers specified')}")
            st.metric("Gross Weight", f"{float(selected.get('gross_weight') or 0):,.2f} KG")
        with c_col2:
            sc1, sc2 = st.columns(2)
            sc1.write(f"**CY Terminal:**\n\n{_s(selected.get('cy_place'), '—')}")
            sc1.write(f"**CY Cut-off Date:**\n\n{_s(selected.get('cy_date'), '—')}")
            sc2.write(f"**Empty Pickup Depot:**\n\n{_s(selected.get('return_place'), '—')}")
            sc2.write(f"**Container Return Free Time:**\n\n{_s(selected.get('customer_return_date'), '—')}")
    elif mode == "SEA" and cargo_type == "LCL":
        cargo_cols = st.columns(4)
        cargo_cols[0].metric("Packages", f"{_s(selected.get('package_qty'), '0')} {_s(selected.get('package_unit'), 'PKGS')}")
        cargo_cols[1].metric("Gross Weight", f"{float(selected.get('gross_weight') or 0):,.2f} KG")
        cargo_cols[2].metric("Volume (CBM)", f"{float(selected.get('measurement_cbm') or 0):,.2f} CBM")
        cargo_cols[3].metric("CFS Cut-off", _s(selected.get("cfs_date"), "—"))
        st.write(f"**CFS Receiving Warehouse:** {_s(selected.get('cfs_place'), '—')}")
    elif mode == "AIR":
        air_cols = st.columns(4)
        air_cols[0].metric("Packages", f"{_s(selected.get('package_qty'), '0')} {_s(selected.get('package_unit'), 'PKGS')}")
        air_cols[1].metric("Gross Weight", f"{float(selected.get('gross_weight') or 0):,.2f} KG")
        air_cols[2].metric("Chargeable Weight", f"{float(selected.get('chargeable_weight') or 0):,.2f} KG")
        air_cols[3].metric("Airport Cut-off", _s(selected.get("cfs_date"), "—"))
        st.write(f"**Airport Cargo Terminal:** {_s(selected.get('cfs_place'), '—')}")
    else:
        trk_cols = st.columns(4)
        trk_cols[0].metric("Packages", f"{_s(selected.get('package_qty'), '0')} {_s(selected.get('package_unit'), 'PKGS')}")
        trk_cols[1].metric("Gross Weight", f"{float(selected.get('gross_weight') or 0):,.2f} KG")
        trk_cols[2].metric("Loading Date", _s(selected.get("loading_date") or selected.get("etd"), "—"))
        trk_cols[3].metric("Delivery Date", _s(selected.get("delivery_date") or selected.get("eta"), "—"))

    section("Action Toolbar")
    act = st.columns(5)
    with act[0]:
        _render_pdf_action(selected, f"booking_{booking_no}")
    with act[1]:
        if can_edit and st.button("📤 Submit", key=f"submit_{booking_no}", width="stretch", help="ส่งบุ๊คกิ้งเพื่อยืนยัน") and current_status == "DRAFT":
            ok, reason = can_transition_booking_status(current_status, "SUBMITTED")
            if ok:
                update_booking(booking_no, {"status": "SUBMITTED"}, user.get("tenant_id"))
                st.success("Booking status changed to SUBMITTED.")
                st.rerun()
            else:
                st.error(reason)
    with act[2]:
        if can_edit and st.button("✅ Confirm", key=f"confirm_{booking_no}", type="secondary", width="stretch", help="ยืนยันบุ๊คกิ้ง (พร้อมเปิด Job)") and current_status in {"SUBMITTED", "DRAFT"}:
            ok, reason = can_transition_booking_status(current_status, "CONFIRMED")
            if not ok and current_status == "DRAFT":
                update_booking(booking_no, {"status": "SUBMITTED"}, user.get("tenant_id"))
                ok, reason = can_transition_booking_status("SUBMITTED", "CONFIRMED")
            if ok:
                update_booking(booking_no, {"status": "CONFIRMED"}, user.get("tenant_id"))
                st.success("Booking CONFIRMED!")
                st.rerun()
            else:
                st.error(reason)
    with act[3]:
        if can_edit and st.button("🚀 Convert to Job", key=f"convert_{booking_no}", type="primary", width="stretch", help="เปิด Job จากข้อมูล Booking นี้") and current_status in {"CONFIRMED", "SUBMITTED", "DRAFT"}:
            try:
                if current_status != "CONFIRMED":
                    update_booking(booking_no, {"status": "SUBMITTED"}, user.get("tenant_id"))
                    update_booking(booking_no, {"status": "CONFIRMED"}, user.get("tenant_id"))
                job_no = convert_booking_to_job(booking_no, user)
                st.success(f"🎉 Job {job_no} created successfully from Booking {booking_no}.")
                st.session_state["current_navigation"] = "job_control"
                st.query_params["page"] = "job_control"
                st.rerun()
            except Exception as exc:
                st.error(str(exc))
    with act[4]:
        st.write("")

    if can_edit:
        with st.expander("✏️ Edit Booking Details & Transport Schedule", expanded=False):
            section("Edit Transport & Schedule")
            with st.form(f"edit_booking_{booking_no}"):
                c_bno_col, _ = st.columns(2)
                new_carrier_bno = c_bno_col.text_input("Carrier Booking No. / Reference No.", value=_s(selected.get("carrier_booking_no")))

                r1, r2, r3 = st.columns(3)
                new_pol = r1.text_input("Origin / POL (ต้นทาง)", value=_s(selected.get("pol")))
                new_trans = r2.text_input("Transshipment Port / Airport / Border (ถ่ายลำ/ด่าน)", value=_s(selected.get("transhipment_port")))
                new_pod = r3.text_input("Destination / POD (ปลายทาง)", value=_s(selected.get("pod")))

                l1, v1, v2 = st.columns(3)
                new_liner = l1.text_input("Liner / Airline / Transporter (ผู้ให้บริการ)", value=_s(selected.get("liner") or selected.get("carrier")))
                new_vessel = v1.text_input("Vessel / Flight No / Truck Type", value=_s(selected.get("vessel")))
                new_voyage = v2.text_input("Voyage No / Flight Date / Plate No", value=_s(selected.get("voyage")))

                if mode == "SEA" and cargo_type == "FCL":
                    mv1, mv2 = st.columns(2)
                    new_mother = mv1.text_input("Mother Vessel (เรือแม่)", value=_s(selected.get("mother_vessel") or selected.get("m_vessel")))
                    new_mother_voyage = mv2.text_input("Mother Voyage No. (เที่ยวเรือแม่)", value=_s(selected.get("mother_voyage") or selected.get("m_voyage")))
                    
                    sc1, sc2 = st.columns(2)
                    new_cy_place = sc1.text_input("CY Return Terminal (ลานคืนตู้หนัก)", value=_s(selected.get("cy_place")))
                    new_return_place = sc2.text_input("Empty Pickup Depot (ลานรับตู้เปล่า)", value=_s(selected.get("return_place")))
                else:
                    new_mother = _s(selected.get("mother_vessel") or selected.get("m_vessel"))
                    new_mother_voyage = _s(selected.get("mother_voyage") or selected.get("m_voyage"))
                    new_cy_place = _s(selected.get("cy_place"))
                    new_return_place = _s(selected.get("return_place"))

                new_remark = st.text_area("Remarks (หมายเหตุ)", value=_s(selected.get("remark")))
                save = st.form_submit_button("💾 Save Changes", type="primary", width="stretch")
            if save:
                try:
                    update_booking(
                        booking_no,
                        {
                            "carrier_booking_no": new_carrier_bno.strip() or None,
                            "pol": new_pol.strip(),
                            "pod": new_pod.strip(),
                            "liner": new_liner.strip() or None,
                            "carrier": new_liner.strip() or None,
                            "vessel": new_vessel.strip() or None,
                            "voyage": new_voyage.strip() or None,
                            "m_vessel": new_mother.strip() or None,
                            "mother_vessel": new_mother.strip() or None,
                            "m_voyage": new_mother_voyage.strip() or None,
                            "mother_voyage": new_mother_voyage.strip() or None,
                            "transhipment_port": new_trans.strip() or None,
                            "cy_place": new_cy_place.strip() or None,
                            "return_place": new_return_place.strip() or None,
                            "remark": new_remark.strip() or None,
                        },
                        user.get("tenant_id"),
                    )
                    st.success("Booking updated successfully.")
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
        query = st.text_input("🔍 Search bookings", placeholder="Search by Booking No, Carrier Booking, Customer, POL, POD, or Vessel/Flight...", key="booking_v2_search")
    with action_col:
        st.write("")
        create_new = st.button("➕ New Booking", type="primary", width="stretch") if can_edit else False

    if query.strip():
        q = query.strip().lower()
        records = [r for r in records if q in str(r).lower()]

    if create_new:
        st.session_state["booking_v2_create_mode"] = True

    if st.session_state.get("booking_v2_create_mode") and can_edit:
        _create_form(user)
        if st.button("❌ Close Form & Return to List", key="booking_v2_close_create", width="stretch"):
            st.session_state.pop("booking_v2_create_mode", None)
            st.rerun()
        return

    section("Bookings Registry")
    table = pd.DataFrame([
        {
            "Booking No.": _s(r.get("booking_no")),
            "Carrier Booking": _s(r.get("carrier_booking_no") or r.get("mawb_no"), "—"),
            "Customer": _s(r.get("customer_name"), "—"),
            "Mode": f"{_s(r.get('mode'), 'SEA')} ({_s(r.get('service_term') or r.get('cargo_type'), 'FCL')})",
            "POL / Origin": _s(r.get("pol"), "—"),
            "POD / Dest": _s(r.get("pod"), "—"),
            "Vessel / Flight / Vehicle": resolve_vessel(r.get("mother_vessel") or r.get("m_vessel"), r.get("vessel") or r.get("flight_no")) or "—",
            "ETD": _s(r.get("etd"), "—"),
            "ETA": _s(r.get("eta"), "—"),
            "Status": _s(r.get("status"), "—").upper(),
        }
        for r in records
    ])
    st.dataframe(table, hide_index=True, width="stretch")

    if not records:
        st.info("No bookings found. Click '➕ New Booking' to create one.")
        return

    options = [r["booking_no"] for r in records if r.get("booking_no")]
    selected_target = st.session_state.get("booking_v2_selected")
    sel_idx = 0
    if selected_target and selected_target in options:
        sel_idx = options.index(selected_target)

    selected_no = st.selectbox("Select Booking to Manage / Inspect / Print", options=options, index=sel_idx, key="booking_v2_selected_box")
    st.session_state["booking_v2_selected"] = selected_no
    selected = get_booking(selected_no, tenant_id)
    if selected:
        _render_selected(selected, user, can_edit)
