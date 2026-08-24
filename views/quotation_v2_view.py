"""Streamlined, agile Quotation workspace for SME Logistics (5-10 users)."""
from __future__ import annotations

import os
from datetime import date, timedelta
from typing import Any, Dict, List, Optional

import pandas as pd
import streamlit as st

from config import DEFAULT_TERMS, JOB_TYPES
from managers.auth_manager import can_write
from managers.customer_master_manager import list_customers
from managers.salesperson_manager import list_salespersons
from managers.charge_master_manager import list_charges
from managers.master_data_crud_manager import list_parties, list_ports
from managers.quotation_manager import duplicate_quotation, get_quotation_by_no, list_quotations
from managers.quotation_ssot_service import create_quotation_ssot, update_quotation_ssot, delete_quotation_ssot, set_quotation_status_ssot
from managers.job_handover_service import handover_quotation_to_job
from ui.design_system import page_header, section

MODE_OPTIONS = ["SEA", "AIR", "ROAD", "RAIL", "MULTIMODAL"]
SERVICE_OPTIONS = ["", "FCL", "LCL", "AIR", "FTL", "LTL", "DOOR-TO-DOOR", "PORT-TO-PORT"]
INCOTERM_OPTIONS = ["", "EXW", "FCA", "FOB", "CFR", "CIF", "DAP", "DPU", "DDP", "DDU"]
PACKAGE_TYPE_OPTIONS = ["", "Cartons", "Pallets", "Wooden Cases", "Crates", "Bags", "Drums", "Rolls", "Boxes", "Packages", "Pieces", "Units"]

MODE_CONFIG = {
    "SEA": {
        "label": "Sea Freight (การขนส่งทางทะเล)",
        "pol_label": "POL / Port of Loading (ท่าเรือต้นทาง) *",
        "pol_placeholder": "e.g. THBKK — Bangkok, THLCH — Laem Chabang, SGSIN — Singapore",
        "pod_label": "POD / Port of Discharge (ท่าเรือปลายทาง) *",
        "pod_placeholder": "e.g. SGSIN — Singapore, USLAX — Los Angeles, CNSHA — Shanghai, NLRTM — Rotterdam",
        "carrier_label": "Shipping Line / Ocean Liner (สายเรือ)",
        "carrier_placeholder": "e.g. ONE, Evergreen, Maersk, Cosco, MSC, CMA CGM, Yang Ming",
        "container_types": ["", "20'GP", "40'GP", "40'HC", "45'HC", "20'RF", "40'RF", "20'OT", "40'OT", "20'FR", "40'FR", "LCL"],
        "default_container": "20'GP",
        "default_desc": "Ocean Freight",
        "default_unit": "CONTAINER",
    },
    "AIR": {
        "label": "Air Freight (การขนส่งทางอากาศ)",
        "pol_label": "AOD / Airport of Departure (สนามบินต้นทาง) *",
        "pol_placeholder": "e.g. BKK — Suvarnabhumi Airport, DMK — Don Mueang, CNPVG — Shanghai Pudong",
        "pod_label": "AOA / Airport of Arrival (สนามบินปลายทาง) *",
        "pod_placeholder": "e.g. SIN — Singapore Changi, NRT — Tokyo Narita, FRA — Frankfurt, LAX — Los Angeles",
        "carrier_label": "Airline (สายการบิน)",
        "carrier_placeholder": "e.g. TG — Thai Airways, SQ — Singapore Airlines, EK — Emirates, CX — Cathay Pacific",
        "container_types": ["", "Loose Cargo / Air Freight", "ULD — PMC Pallet", "ULD — PAG Pallet", "ULD — AKE Container", "Courier Box"],
        "default_container": "Loose Cargo / Air Freight",
        "default_desc": "Air Freight",
        "default_unit": "KG",
    },
    "ROAD": {
        "label": "Road / Trucking (การขนส่งทางบก/รถบรรทุก)",
        "pol_label": "Place of Loading / Pick-up (สถานที่รับสินค้า/ต้นทาง) *",
        "pol_placeholder": "e.g. Bangkok Factory, Lat Krabang ICD, Sadao Border, Nong Khai",
        "pod_label": "Place of Delivery / Destination (สถานที่ส่งสินค้า/ปลายทาง) *",
        "pod_placeholder": "e.g. Vientiane Laos, Poipet Cambodia, Bukit Kayu Hitam, Chiang Mai",
        "carrier_label": "Trucking Company / Haulier (บริษัทรถบรรทุก/หัวลาก)",
        "carrier_placeholder": "e.g. SCG Logistics, Flash, Kerry Express, Local Haulier",
        "container_types": ["", "4-Wheeler Truck (4 ล้อ)", "6-Wheeler Truck (6 ล้อ)", "10-Wheeler Truck (10 ล้อ)", "Trailer 20ft (หางลาก)", "Trailer 40ft (หางลาก)", "Lowbed Trailer", "Flatbed", "LTL (Less Truckload)"],
        "default_container": "Trailer 40ft (หางลาก)",
        "default_desc": "Trucking / Transport",
        "default_unit": "TRIP",
    },
    "RAIL": {
        "label": "Rail Freight (การขนส่งทางราง)",
        "pol_label": "Origin Rail Station (สถานีรถไฟต้นทาง) *",
        "pol_placeholder": "e.g. Lat Krabang ICD Rail Station, Nong Khai Station",
        "pod_label": "Destination Rail Station (สถานีรถไฟปลายทาง) *",
        "pod_placeholder": "e.g. Thanaleng Station (Laos), Vientiane South, Kunming (China)",
        "carrier_label": "Rail Operator (ผู้ให้บริการขนส่งทางราง)",
        "carrier_placeholder": "e.g. State Railway of Thailand (SRT), Lao-China Railway",
        "container_types": ["", "20'GP Rail Container", "40'GP Rail Container", "40'HC Rail Container", "Wagon"],
        "default_container": "40'HC Rail Container",
        "default_desc": "Rail Freight",
        "default_unit": "CONTAINER",
    },
    "MULTIMODAL": {
        "label": "Multimodal Transport (การขนส่งต่อเนื่องหลายรูปแบบ)",
        "pol_label": "Place of Origin / Receipt (สถานที่รับของต้นทาง) *",
        "pol_placeholder": "e.g. Factory origin, Port of departure",
        "pod_label": "Place of Final Delivery (สถานที่ส่งของปลายทาง) *",
        "pod_placeholder": "e.g. Destination warehouse, Final port/border",
        "carrier_label": "Primary Carrier / Operator (ผู้ให้บริการหลัก)",
        "carrier_placeholder": "e.g. Multimodal Freight Operator",
        "container_types": ["", "20'GP", "40'GP", "40'HC", "45'HC", "Trailer", "LCL", "Air / Sea Combo"],
        "default_container": "40'HC",
        "default_desc": "Multimodal Freight",
        "default_unit": "CONTAINER",
    }
}


def _s(value: Any, default: str = "") -> str:
    if value is None:
        return default
    value = str(value).strip()
    return default if value.lower() in {"", "none", "nan", "nat"} else value


def _date(value: Any, fallback: date) -> date:
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value)[:10])
    except (ValueError, TypeError):
        return fallback


def _prepare_pdf(record: Dict[str, Any], items: list[dict]) -> None:
    qno = _s(record.get("quotation_no"), "quotation")
    try:
        from pdf.quotation_pdf import generate_quotation_pdf
        path = generate_quotation_pdf(record, items)
        if path and os.path.exists(path):
            with open(path, "rb") as fh:
                st.session_state[f"quotation_pdf_{qno}"] = fh.read()
                st.session_state[f"quotation_pdf_name_{qno}"] = os.path.basename(path)
    except Exception as exc:
        st.error(f"Unable to create PDF: {exc}")


def _render_pdf(record: Dict[str, Any], items: list[dict]) -> None:
    qno = _s(record.get("quotation_no"), "quotation")
    if st.button("📄 Generate PDF", key=f"qv2_prepare_pdf_{qno}", type="primary", width="stretch"):
        _prepare_pdf(record, items)
    payload = st.session_state.get(f"quotation_pdf_{qno}")
    if payload:
        st.download_button("⬇️ Download PDF", data=payload, file_name=st.session_state.get(f"quotation_pdf_name_{qno}", f"{qno}.pdf"), mime="application/pdf", key=f"qv2_download_pdf_{qno}", width="stretch")


def _master_data():
    # 1. Pull customers from Business Parties with role CUSTOMER + legacy customer master
    parties_cust = list_parties("CUSTOMER", active_only=True) or []
    legacy_cust = list_customers() or []
    
    customer_dict: Dict[int, Dict[str, Any]] = {}
    customer_map: Dict[int, str] = {}
    
    for r in parties_cust:
        cid = int(r["id"])
        cname = r.get("display_name") or r.get("legal_name") or str(cid)
        pcode = str(r.get("party_code") or f"C{cid:04d}")
        customer_dict[cid] = {
            "id": cid,
            "customer_code": pcode,
            "company_name": r.get("legal_name") or cname,
            "display_name": cname,
            "tax_id": r.get("tax_id") or "",
            "branch_no": r.get("branch_no") or "00000",
            "contact_person": r.get("contact_person") or "",
            "tel": r.get("phone") or "",
            "email": r.get("email") or "",
            "address": r.get("billing_address") or "",
            "billing_address": r.get("billing_address") or "",
            "credit_limit": r.get("credit_limit") or 0.0,
            "credit_currency": r.get("credit_currency") or "THB",
            "credit_days": r.get("credit_days") or 30,
            "payment_term_code": r.get("payment_term_code") or "Net 30",
        }
        customer_map[cid] = f"{pcode} — {cname}"
        
    for r in legacy_cust:
        cid = int(r["id"])
        if cid not in customer_dict:
            cname = r.get("display_name") or r.get("company_name") or str(cid)
            pcode = str(r.get("customer_code") or f"C{cid:04d}")
            customer_dict[cid] = r
            customer_map[cid] = f"{pcode} — {cname}"

    # 2. Pull real salespersons from Salesperson Master
    sales_list = list_salespersons(active_only=True) or []
    sales_map: Dict[Any, str] = {}
    for s in sales_list:
        sid = s.get("id")
        scode = str(s.get("sales_code") or "").strip()
        sname = str(s.get("name") or "").strip()
        sales_map[sid] = f"{scode} — {sname}".strip(" —") if scode else sname

    # 3. Master carriers, ports, charges
    carriers = list_parties("CARRIER", active_only=True) or []
    ports = list_ports(active_only=True) or []
    charges = list_charges(active_only=True) or []
    
    carrier_map = {int(r["id"]): f"{r.get('party_code')} — {r.get('display_name') or r.get('legal_name')}" for r in carriers if r.get("id")}
    port_map = {int(r["id"]): f"{r.get('port_code')} — {r.get('port_name')}, {r.get('country_name') or ''}" for r in ports if r.get("id")}
    
    charge_map = {}
    for r in charges:
        code = str(r.get("charge_code") or "").strip().upper()
        if code:
            charge_map[code] = r
            
    return customer_map, customer_dict, sales_map, carrier_map, port_map, charge_map


def _item_editor(charge_map: Dict[str, Any], existing: List[Dict[str, Any]] = None, mode: str = "SEA", key: str = "qv2_items_editor") -> List[Dict[str, Any]]:
    mcfg = MODE_CONFIG.get(mode, MODE_CONFIG["SEA"])
    default_u = mcfg.get("default_unit", "CONTAINER")
    default_d = mcfg.get("default_desc", "Freight / Service Charge")
    
    rows = []
    for item in (existing or []):
        desc = _s(item.get("description"))
        code = _s(item.get("charge_code")).upper()
        if not desc and code:
            desc = charge_map.get(code, {}).get("description") or code
        
        qty = float(item.get("quantity") if item.get("quantity") is not None else 1.0)
        rate = float(item.get("unit_rate") if item.get("unit_rate") is not None else (item.get("price") or 0.0))
        unit = _s(item.get("unit") or item.get("basis"), default_u).upper()
        currency = _s(item.get("currency"), "USD").upper()
        
        rows.append({
            "description": desc or default_d,
            "unit": unit,
            "currency": currency,
            "quantity": qty,
            "unit_rate": rate,
            "price": qty * rate,
            "remark": _s(item.get("remark")),
        })

    if not rows:
        rows = [{
            "description": default_d,
            "unit": default_u,
            "currency": "USD",
            "quantity": 1.0,
            "unit_rate": 0.0,
            "price": 0.0,
            "remark": "",
        }]

    df = pd.DataFrame(rows)
    edited = st.data_editor(
        df,
        num_rows="dynamic",
        hide_index=True,
        width="stretch",
        column_config={
            "description": st.column_config.TextColumn("Description (รายการค่าบริการ / ค่าระวาง - เว้นว่างได้)", required=False, width="large"),
            "unit": st.column_config.TextColumn("Unit (หน่วย เช่น CONTAINER, CBM, TRIP, KG, PALLET)", default=default_u, required=False, width="small"),
            "currency": st.column_config.TextColumn("Curr (สกุลเงิน เช่น USD, THB, EUR, CNY)", default="USD", required=False, width="small"),
            "quantity": st.column_config.NumberColumn("Qty (จำนวน)", min_value=0.0, step=0.01, format="%.2f", width="small"),
            "unit_rate": st.column_config.NumberColumn("Unit Rate (ราคา/หน่วย)", min_value=0.0, step=0.01, format="%.2f", width="small"),
            "price": st.column_config.NumberColumn("Total Amount", disabled=True, format="%.2f", width="medium"),
            "remark": st.column_config.TextColumn("Remark (หมายเหตุ)", width="medium"),
        },
        key=key,
    )

    output = []
    for row in edited.to_dict("records"):
        desc = _s(row.get("description"))
        qty = float(row.get("quantity") if row.get("quantity") is not None else 0.0)
        rate = float(row.get("unit_rate") if row.get("unit_rate") is not None else 0.0)
        unit = _s(row.get("unit"), default_u).upper()
        currency = _s(row.get("currency"), "USD").upper()

        # If description is empty BUT user entered rate, qty, unit, or curr
        if not desc:
            if rate > 0 or qty > 0 or row.get("unit") or row.get("currency") or row.get("remark"):
                desc = default_d
            else:
                continue

        # Auto-derive charge_code behind the scenes
        code = "CHG"
        desc_upper = desc.upper()
        if "OCEAN" in desc_upper or "SEA" in desc_upper or "OFR" in desc_upper:
            code = "OFR"
        elif "AIR" in desc_upper or "AFR" in desc_upper:
            code = "AIR"
        elif "TERMINAL" in desc_upper or "THC" in desc_upper:
            code = "THC"
        elif "DOC" in desc_upper or "DOCUMENT" in desc_upper:
            code = "DOC"
        elif "CUSTOM" in desc_upper or "CLEARANCE" in desc_upper or "DUTY" in desc_upper:
            code = "CUS"
        elif "TRUCK" in desc_upper or "HAULAGE" in desc_upper or "TRANSPORT" in desc_upper:
            code = "TRK"
        elif "STORAGE" in desc_upper or "WAREHOUSE" in desc_upper:
            code = "STG"
        elif "DEMURRAGE" in desc_upper or "DETENTION" in desc_upper:
            code = "DEM"
        elif len(desc.split()[0]) <= 5 and desc.split()[0].isalnum():
            code = desc.split()[0].upper()

        output.append({
            "charge_code": code,
            "description": desc,
            "basis": unit,
            "quantity": qty,
            "unit": unit,
            "currency": currency,
            "unit_rate": rate,
            "price": qty * rate,
            "amount": qty * rate,
            "remark": _s(row.get("remark")),
        })
    return output


def _create_form(user: Dict[str, Any]):
    customer_map, customer_dict, sales_map, carrier_map, port_map, charge_map = _master_data()
    today = date.today()

    section("1. General & Customer Details (เลือกคู่ค้า/ลูกค้าและโหมดขนส่ง)")
    
    # Header selectors that trigger auto-fill and mode adaptation
    h1, h2 = st.columns([2, 2])
    with h1:
        cust_keys = list(customer_map)
        selected_cust_id = st.selectbox(
            "Customer * (เลือกลูกค้าจาก Business Parties)",
            cust_keys,
            format_func=lambda x: customer_map[x],
            key="qv2_new_customer_select"
        ) if cust_keys else None
    with h2:
        selected_mode = st.selectbox(
            "Transport Mode * (โหมดการขนส่ง - ปรับเปลี่ยนตามโหมด)",
            MODE_OPTIONS,
            key="qv2_new_mode_select"
        )

    mcfg = MODE_CONFIG.get(selected_mode, MODE_CONFIG["SEA"])
    cust_info = customer_dict.get(selected_cust_id, {}) if selected_cust_id else {}

    with st.form("quotation_v2_create_form"):
        c1, c2, c3 = st.columns(3)
        with c1:
            attention = st.text_input("Attention (ผู้ติดต่อ)", value=_s(cust_info.get("contact_person")), key="qv2_new_att")
            tel = st.text_input("Telephone (เบอร์โทร)", value=_s(cust_info.get("tel") or cust_info.get("phone")), key="qv2_new_tel")
        with c2:
            sales_keys = list(sales_map)
            sales_id = st.selectbox(
                "Salesperson * (เลือกพนักงานขาย)",
                sales_keys,
                format_func=lambda x: sales_map[x],
                key="qv2_new_sales"
            ) if sales_keys else None
            customer_email = st.text_input("Customer Email (อีเมล)", value=_s(cust_info.get("email")), key="qv2_new_email")
        with c3:
            job_type = st.selectbox("Job Type * (ประเภทงาน)", list(JOB_TYPES.keys()), format_func=lambda x: JOB_TYPES.get(x, x), key="qv2_new_job")
            payment_term = st.text_input("Payment Terms (เงื่อนไขการชำระ)", value=_s(cust_info.get("payment_term_code") or "Net 30"), key="qv2_new_pay")

        d1, d2 = st.columns(2)
        with d1:
            issue_date = st.date_input("Issue Date (วันที่ออก)", today, key="qv2_new_issue")
        with d2:
            valid_until = st.date_input("Valid Until (ใช้ได้ถึง)", today + timedelta(days=30), key="qv2_new_valid")

        # Auto-populated Customer Billing Address
        default_addr = _s(cust_info.get("billing_address") or cust_info.get("address"))
        customer_address = st.text_area("Customer Address (ที่อยู่ลูกค้า - ดึงจากฐานข้อมูล Business Party อัตโนมัติ)", value=default_addr, height=70, key="qv2_new_addr")

        # Non-mandatory Shipper & Consignee
        sh1, sh2 = st.columns(2)
        with sh1:
            shipper = st.text_area("Shipper (ผู้ส่งสินค้า - ไม่บังคับ)", height=68, placeholder="ระบุชื่อบริษัท / ที่อยู่ของ Shipper (ถ้ามี)", key="qv2_new_shp")
        with sh2:
            consignee = st.text_area("Consignee (ผู้รับสินค้า - ไม่บังคับ)", height=68, placeholder="ระบุชื่อบริษัท / ที่อยู่ของ Consignee (ถ้ามี)", key="qv2_new_csg")

        section(f"2. Routing & Carrier ({mcfg['label']})")
        r1, r2, r3, r4 = st.columns(4)
        with r1:
            service_type = st.selectbox("Service Type (บริการ)", SERVICE_OPTIONS, key="qv2_new_serv")
        with r2:
            pol = st.text_input(mcfg["pol_label"], placeholder=mcfg["pol_placeholder"], key="qv2_new_pol")
        with r3:
            pod = st.text_input(mcfg["pod_label"], placeholder=mcfg["pod_placeholder"], key="qv2_new_pod")
        with r4:
            incoterm = st.selectbox("Incoterm", INCOTERM_OPTIONS, key="qv2_new_inco")

        r5, r6, r7, r8 = st.columns(4)
        with r5:
            origin = st.text_input("Place of Origin / Receipt (ต้นทางรับของ)", key="qv2_new_orig")
        with r6:
            destination = st.text_input("Place of Destination / Delivery (ปลายทางส่งของ)", key="qv2_new_dest")
        with r7:
            carrier = st.text_input(mcfg["carrier_label"], placeholder=mcfg["carrier_placeholder"], key="qv2_new_carr")
        with r8:
            freight_term = st.selectbox("Freight Term", ["", "Prepaid", "Collect"], key="qv2_new_frt")

        section("3. Cargo Specifications (ข้อมูลสินค้า & บรรจุภัณฑ์)")
        g1, g2, g3 = st.columns(3)
        with g1:
            commodity = st.text_input("Commodity (ชื่อสินค้า)", key="qv2_new_comm")
            hs_code = st.text_input("HS Code", key="qv2_new_hs")
        with g2:
            cont_opts = mcfg.get("container_types", [""])
            container_type = st.selectbox("Equipment / Container / Vehicle (ประเภทตู้/รถ)", cont_opts, key="qv2_new_cont_type")
            container_qty = st.number_input("Equipment Qty (จำนวนตู้/คัน)", min_value=0.0, step=1.0, value=1.0 if container_type and container_type != "LCL" else 0.0, format="%.2f", key="qv2_new_cont_qty")
        with g3:
            package_type = st.selectbox("Package Type (บรรจุภัณฑ์)", PACKAGE_TYPE_OPTIONS, key="qv2_new_pkg_type")
            package_qty = st.number_input("Package Qty (จำนวนหีบห่อ)", min_value=0.0, step=0.01, value=0.0, format="%.2f", key="qv2_new_pkg_qty")

        w1, w2, w3 = st.columns(3)
        with w1:
            weight_kg = st.number_input("Gross Weight (KG)", min_value=0.0, step=0.01, format="%.2f", key="qv2_new_wt")
        with w2:
            volume_cbm = st.number_input("Volume (CBM)", min_value=0.0, step=0.001, format="%.3f", key="qv2_new_cbm")
        with w3:
            is_dg = st.checkbox("Dangerous Goods (สินค้าอันตราย / DG)", value=False, key="qv2_new_dg")

        section("4. Pricing & Selling Charges (รายการค่าใช้จ่ายและราคาขาย)")
        st.caption(f"💡 รายการเสนอราคาสำหรับ {selected_mode} Freight (ใส่ Unit, Curr, Qty, Unit Rate ได้อย่างอิสระ Description เว้นว่างได้)")
        items_df = _item_editor(charge_map, mode=selected_mode, key="qv2_items_create_table")

        if items_df:
            totals_by_curr = {}
            for item in items_df:
                curr = item.get("currency", "USD")
                totals_by_curr[curr] = totals_by_curr.get(curr, 0.0) + float(item.get("price") or 0.0)
            st.write("**Total Summary:** " + " | ".join([f"**{tot:,.2f} {curr}**" for curr, tot in totals_by_curr.items()]))

        section("5. Terms & Remarks (เงื่อนไขและหมายเหตุ)")
        subject = st.text_input("Quotation Subject (หัวข้อ)", value=f"{selected_mode} Freight Quotation - {cust_info.get('company_name', '')}", key="qv2_new_subj")
        terms = st.text_area("Terms & Conditions (ข้อกำหนดและเงื่อนไข)", value=DEFAULT_TERMS, height=100, key="qv2_new_terms")

        submitted = st.form_submit_button("💾 Save Quotation as Draft", type="primary", width="stretch")

    if submitted:
        errors = []
        if selected_cust_id is None:
            errors.append("Customer is required (กรุณาเลือกลูกค้า).")
        if valid_until < issue_date:
            errors.append("Valid Until cannot be earlier than Issue Date (วันหมดอายุต้องไม่อยู่ก่อนวันที่ออก).")
        if not items_df:
            errors.append("Please enter at least 1 pricing charge line (กรุณาระบุอย่างน้อย 1 รายการค่าใช้จ่าย).")

        if errors:
            for error in errors:
                st.error(error)
            return

        final_addr = customer_address.strip() or _s(cust_info.get("billing_address") or cust_info.get("address"))

        payload = {
            "job_type": job_type,
            "customer_id": selected_cust_id,
            "customer_name": cust_info.get("display_name") or cust_info.get("company_name") or str(selected_cust_id),
            "customer_address": final_addr,
            "shipper": shipper.strip() or None,
            "consignee": consignee.strip() or None,
            "sales_id": sales_id,
            "salesperson": sales_map.get(sales_id, "") if sales_id else "",
            "attention": attention.strip(),
            "tel": tel.strip(),
            "customer_email": customer_email.strip(),
            "quotation_date": issue_date.isoformat(),
            "validity_date": valid_until.isoformat(),
            "payment_term": payment_term.strip(),
            "carrier": carrier.strip() or None,
            "pol": pol.strip() or None,
            "pod": pod.strip() or None,
            "origin": origin.strip(),
            "destination": destination.strip(),
            "mode": selected_mode,
            "service_type": service_type,
            "incoterm": incoterm,
            "freight_term": freight_term,
            "commodity": commodity.strip() or None,
            "hs_code": hs_code.strip() or None,
            "container_type": container_type,
            "container_quantity": container_qty,
            "package_type": package_type,
            "quantity": package_qty,
            "weight_kg": weight_kg,
            "volume_cbm": volume_cbm,
            "is_dg": is_dg,
            "subject": subject.strip() or None,
            "terms_conditions": terms.strip(),
            "status": "Draft",
        }
        try:
            qno = create_quotation_ssot(payload, items_df)
            st.session_state.pop("qv2_create", None)
            st.session_state["qv2_selected"] = qno
            st.success(f"🎉 Quotation {qno} created successfully!")
            st.rerun()
        except Exception as exc:
            st.error(f"Unable to save quotation: {exc}")


def _render_edit_form(selected: Dict[str, Any], user: Dict[str, Any]):
    qno = _s(selected.get("quotation_no"))
    customer_map, customer_dict, sales_map, carrier_map, port_map, charge_map = _master_data()
    today = date.today()

    cur_cust = selected.get("customer_id")
    cust_keys = list(customer_map)
    cust_idx = cust_keys.index(cur_cust) if cur_cust in cust_keys else 0

    sales_keys = list(sales_map)
    cur_sales = selected.get("sales_id")
    sales_idx = sales_keys.index(cur_sales) if cur_sales in sales_keys else 0

    job_keys = list(JOB_TYPES.keys())
    cur_job = selected.get("job_type")
    job_idx = job_keys.index(cur_job) if cur_job in job_keys else 0

    cur_mode = selected.get("mode") or "SEA"
    mode_idx = MODE_OPTIONS.index(cur_mode) if cur_mode in MODE_OPTIONS else 0
    mcfg = MODE_CONFIG.get(cur_mode, MODE_CONFIG["SEA"])

    cur_serv = selected.get("service_type")
    serv_idx = SERVICE_OPTIONS.index(cur_serv) if cur_serv in SERVICE_OPTIONS else 0

    cur_inco = selected.get("incoterm")
    inco_idx = INCOTERM_OPTIONS.index(cur_inco) if cur_inco in INCOTERM_OPTIONS else 0

    cont_opts = mcfg.get("container_types", [""])
    cur_cont = selected.get("container_type")
    cont_type_idx = cont_opts.index(cur_cont) if cur_cont in cont_opts else 0

    cur_pkg = selected.get("package_type")
    pkg_type_idx = PACKAGE_TYPE_OPTIONS.index(cur_pkg) if cur_pkg in PACKAGE_TYPE_OPTIONS else 0

    curr_addr = _s(selected.get("customer_address"))
    if not curr_addr and cur_cust in customer_dict:
        c_item = customer_dict[cur_cust]
        curr_addr = _s(c_item.get("billing_address") or c_item.get("address"))

    issue_date_val = _date(selected.get("quotation_date"), today)
    valid_until_val = _date(selected.get("validity_date"), issue_date_val + timedelta(days=30))

    with st.form(f"quotation_v2_edit_{qno}"):
        section("1. Quotation Details")
        c1, c2, c3 = st.columns(3)
        with c1:
            customer_id = st.selectbox("Customer * (ลูกค้า)", cust_keys, index=cust_idx, format_func=lambda x: customer_map[x], key=f"edit_cust_{qno}") if cust_keys else None
            attention = st.text_input("Attention (ผู้ติดต่อ)", value=_s(selected.get("attention")), key=f"edit_att_{qno}")
            tel = st.text_input("Telephone (เบอร์โทร)", value=_s(selected.get("tel")), key=f"edit_tel_{qno}")
        with c2:
            sales_id = st.selectbox("Salesperson * (เลือกพนักงานขาย)", sales_keys, index=sales_idx, format_func=lambda x: sales_map[x], key=f"edit_sales_{qno}") if sales_keys else None
            customer_email = st.text_input("Customer Email (อีเมล)", value=_s(selected.get("customer_email")), key=f"edit_email_{qno}")
            payment_term = st.text_input("Payment Terms", value=_s(selected.get("payment_term"), "Net 30"), key=f"edit_pay_{qno}")
        with c3:
            job_type = st.selectbox("Job Type *", job_keys, index=job_idx, format_func=lambda x: JOB_TYPES.get(x, x), key=f"edit_job_{qno}")
            issue_date = st.date_input("Issue Date", issue_date_val, key=f"edit_issue_{qno}")
            valid_until = st.date_input("Valid Until", valid_until_val, key=f"edit_valid_{qno}")

        customer_address = st.text_area("Customer Address (ที่อยู่ลูกค้า)", value=curr_addr, height=70, key=f"edit_addr_{qno}")

        sh1, sh2 = st.columns(2)
        with sh1:
            shipper = st.text_area("Shipper (ผู้ส่งสินค้า - ไม่บังคับ)", value=_s(selected.get("shipper")), height=68, key=f"edit_shp_{qno}", placeholder="Shipper name / address")
        with sh2:
            consignee = st.text_area("Consignee (ผู้รับสินค้า - ไม่บังคับ)", value=_s(selected.get("consignee")), height=68, key=f"edit_csg_{qno}", placeholder="Consignee name / address")

        section(f"2. Routing & Incoterms ({mcfg['label']})")
        r1, r2, r3, r4 = st.columns(4)
        with r1:
            mode = st.selectbox("Transport Mode", MODE_OPTIONS, index=mode_idx, key=f"edit_mode_{qno}")
        with r2:
            service_type = st.selectbox("Service Type", SERVICE_OPTIONS, index=serv_idx, key=f"edit_serv_{qno}")
        with r3:
            pol = st.text_input(mcfg["pol_label"], value=_s(selected.get("pol")), key=f"edit_pol_{qno}")
        with r4:
            pod = st.text_input(mcfg["pod_label"], value=_s(selected.get("pod")), key=f"edit_pod_{qno}")

        r5, r6, r7, r8 = st.columns(4)
        with r5:
            origin = st.text_input("Place of Origin / Receipt", value=_s(selected.get("origin")), key=f"edit_orig_{qno}")
        with r6:
            destination = st.text_input("Place of Destination / Delivery", value=_s(selected.get("destination")), key=f"edit_dest_{qno}")
        with r7:
            incoterm = st.selectbox("Incoterm", INCOTERM_OPTIONS, index=inco_idx, key=f"edit_inco_{qno}")
        with r8:
            raw_frt = _s(selected.get("freight_term")).title()
            frt_opts = ["", "Prepaid", "Collect"]
            frt_idx = frt_opts.index(raw_frt) if raw_frt in frt_opts else 0
            freight_term = st.selectbox("Freight Term", frt_opts, index=frt_idx, key=f"edit_frt_{qno}")

        carrier = st.text_input(mcfg["carrier_label"], value=_s(selected.get("carrier")), key=f"edit_carr_{qno}")

        section("3. Cargo Specifications")
        g1, g2, g3 = st.columns(3)
        with g1:
            commodity = st.text_input("Commodity", value=_s(selected.get("commodity")), key=f"edit_comm_{qno}")
            hs_code = st.text_input("HS Code", value=_s(selected.get("hs_code")), key=f"edit_hs_{qno}")
        with g2:
            container_type = st.selectbox("Equipment / Container / Vehicle", cont_opts, index=cont_type_idx, key=f"edit_cont_type_{qno}")
            container_qty = st.number_input("Container / Vehicle Qty", min_value=0.0, step=1.0, value=float(selected.get("container_quantity") or 0.0), format="%.2f", key=f"edit_cont_qty_{qno}")
        with g3:
            package_type = st.selectbox("Package Type", PACKAGE_TYPE_OPTIONS, index=pkg_type_idx, key=f"edit_pkg_type_{qno}")
            package_qty = st.number_input("Package Qty", min_value=0.0, step=0.01, value=float(selected.get("quantity") or 0.0), format="%.2f", key=f"edit_pkg_qty_{qno}")

        w1, w2, w3 = st.columns(3)
        with w1:
            weight_kg = st.number_input("Gross Weight (KG)", min_value=0.0, step=0.01, format="%.2f", value=float(selected.get("weight_kg") or 0.0), key=f"edit_wt_{qno}")
        with w2:
            volume_cbm = st.number_input("Volume (CBM)", min_value=0.0, step=0.001, format="%.3f", value=float(selected.get("volume_cbm") or 0.0), key=f"edit_cbm_{qno}")
        with w3:
            is_dg = st.checkbox("Dangerous Goods (DG)", value=bool(selected.get("is_dg")), key=f"edit_dg_{qno}")

        section("4. Pricing & Line Items")
        st.caption("💡 พิมพ์ Description, Unit, Curr, Qty, Rate ได้อิสระ โดยไม่ต้องระบุ Charge Code")
        items_df = _item_editor(charge_map, existing=selected.get("items", []), mode=mode, key=f"qv2_edit_items_{qno}")

        section("5. Terms & Remarks")
        subject = st.text_input("Subject", value=_s(selected.get("subject")), key=f"edit_subj_{qno}")
        terms = st.text_area("Terms & Conditions", value=_s(selected.get("terms_conditions"), DEFAULT_TERMS), height=100, key=f"edit_terms_{qno}")

        submitted = st.form_submit_button("💾 Save Changes", type="primary", width="stretch")

    if submitted:
        errors = []
        if customer_id is None:
            errors.append("Customer is required.")
        if valid_until < issue_date:
            errors.append("Valid Until cannot be earlier than Issue Date.")
        if not items_df:
            errors.append("Please enter at least 1 pricing charge line.")

        if errors:
            for error in errors:
                st.error(error)
            return

        final_edit_addr = customer_address.strip()
        if not final_edit_addr and customer_id in customer_dict:
            c_rec = customer_dict[customer_id]
            final_edit_addr = _s(c_rec.get("billing_address") or c_rec.get("address"))

        payload = {
            "job_type": job_type,
            "customer_id": customer_id,
            "customer_name": customer_map[customer_id],
            "customer_address": final_edit_addr,
            "shipper": shipper.strip() or None,
            "consignee": consignee.strip() or None,
            "sales_id": sales_id,
            "salesperson": sales_map.get(sales_id, "") if sales_id else "",
            "attention": attention.strip(),
            "tel": tel.strip(),
            "customer_email": customer_email.strip(),
            "quotation_date": issue_date.isoformat(),
            "validity_date": valid_until.isoformat(),
            "payment_term": payment_term.strip(),
            "carrier": carrier.strip() or None,
            "pol": pol.strip() or None,
            "pod": pod.strip() or None,
            "origin": origin.strip(),
            "destination": destination.strip(),
            "mode": mode,
            "service_type": service_type,
            "incoterm": incoterm,
            "freight_term": freight_term,
            "commodity": commodity.strip() or None,
            "hs_code": hs_code.strip() or None,
            "container_type": container_type,
            "container_quantity": container_qty,
            "package_type": package_type,
            "quantity": package_qty,
            "weight_kg": weight_kg,
            "volume_cbm": volume_cbm,
            "is_dg": is_dg,
            "subject": subject.strip() or None,
            "terms_conditions": terms.strip(),
            "status": selected.get("status") or "Draft",
        }
        try:
            update_quotation_ssot(qno, payload, items_df)
            st.success(f"Quotation {qno} updated successfully.")
            st.rerun()
        except Exception as exc:
            st.error(f"Unable to update quotation: {exc}")


def render():
    page_header("quotation", status_text="Online")
    user = st.session_state.get("user", {})
    can_edit = can_write(str(user.get("role", "")).lower(), "quotation")

    records = list_quotations() or []
    search, new_col = st.columns([4, 1])
    with search:
        query = st.text_input("🔍 Search Quotations", placeholder="Search Quotation No, Customer, Route, or Subject...", key="qv2_search")
    with new_col:
        st.write("")
        new_quote = st.button("➕ New Quotation", type="primary", width="stretch") if can_edit else False

    if query.strip():
        q = query.strip().lower()
        records = [r for r in records if q in str(r).lower()]

    if new_quote:
        st.session_state["qv2_create"] = True
    if st.session_state.get("qv2_create") and can_edit:
        _create_form(user)
        if st.button("✖️ Close Create Form", key="qv2_close"):
            st.session_state.pop("qv2_create", None)
            st.rerun()
        return

    section("Quotation Ledger (รายการใบเสนอราคา)")
    table = pd.DataFrame([
        {
            "Quotation No.": _s(r.get("quotation_no")),
            "Customer": _s(r.get("customer_name"), "—"),
            "Route": f"{_s(r.get('pol'),'—')} ➔ {_s(r.get('pod'),'—')}",
            "Service": f"{_s(r.get('service_type'))} {_s(r.get('job_type'))}".strip(),
            "Issue Date": _s(r.get("quotation_date"), "—"),
            "Valid Until": _s(r.get("validity_date"), "—"),
            "Sales": _s(r.get("salesperson"), "—"),
            "Status": _s(r.get("status"), "Draft"),
        }
        for r in records
    ])
    st.dataframe(table, hide_index=True, width="stretch")
    if not records:
        st.info("No quotations found.")
        return

    qnos = [r["quotation_no"] for r in records if r.get("quotation_no")]
    default_qno_idx = 0
    if st.session_state.get("qv2_selected") in qnos:
        default_qno_idx = qnos.index(st.session_state["qv2_selected"])
    
    selected_no = st.selectbox("Select Quotation to Manage", qnos, index=default_qno_idx, key="qv2_selected")
    selected = get_quotation_by_no(selected_no)
    if not selected:
        st.warning("Quotation not found.")
        return

    # Quotation Control Center
    status = _s(selected.get("status"), "Draft")
    section(f"Control Center: {selected_no} ({status})")
    
    # Status badges and quick actions
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Customer", _s(selected.get("customer_name"), "—"))
    m2.metric("Route", f"{_s(selected.get('pol'),'—')} ➔ {_s(selected.get('pod'),'—')}")
    m3.metric("Valid Until", _s(selected.get("validity_date"), "—"))
    m4.metric("Status", status)

    # Action Toolbar
    act_col1, act_col2, act_col3, act_col4, act_col5 = st.columns([2, 2, 2, 2, 2])
    with act_col1:
        _render_pdf(selected, selected.get("items", []))
    
    with act_col2:
        if can_edit:
            if status.lower() not in {"approved", "accepted"}:
                if st.button("✅ Approve Quote", key=f"qv2_approve_{selected_no}", type="secondary", width="stretch", help="ลูกค้าตกลง / พร้อมส่งต่อให้ฝ่ายปฏิบัติการเปิด Job"):
                    set_quotation_status_ssot(selected_no, "Approved")
                    st.success("Quotation marked as Approved!")
                    st.rerun()
            else:
                st.info("✅ Approved")

    with act_col3:
        if can_edit and status.lower() in {"approved", "accepted"}:
            if st.button("🚀 Create Job", key=f"qv2_handover_{selected_no}", type="primary", width="stretch", help="ส่งต่อให้ฝ่ายปฏิบัติการ (Operations/CS) เปิด Job"):
                try:
                    job_no = handover_quotation_to_job(selected_no, user)
                    st.success(f"Job {job_no} created successfully!")
                    st.rerun()
                except Exception as exc:
                    st.error(str(exc))
        elif can_edit:
            if st.button("📑 Duplicate", key=f"qv2_dup_{selected_no}", width="stretch"):
                try:
                    new_q = duplicate_quotation(selected_no)
                    st.success(f"Created duplicate {new_q} as Draft.")
                    st.session_state["qv2_selected"] = new_q
                    st.rerun()
                except Exception as exc:
                    st.error(str(exc))

    with act_col4:
        if can_edit and status.lower() not in {"rejected", "cancelled"}:
            if st.button("❌ Reject / Void", key=f"qv2_reject_{selected_no}", width="stretch"):
                set_quotation_status_ssot(selected_no, "Rejected")
                st.warning("Quotation marked as Rejected.")
                st.rerun()

    with act_col5:
        if can_edit:
            delete_key = f"qv2_confirm_del_{selected_no}"
            if not st.session_state.get(delete_key):
                if st.button("🗑️ Delete Quote", key=f"qv2_del_btn_{selected_no}", width="stretch"):
                    st.session_state[delete_key] = True
                    st.rerun()
            else:
                st.warning(f"Delete {selected_no}?")
                c_del_yes, c_del_no = st.columns(2)
                with c_del_yes:
                    if st.button("Yes, Delete", key=f"qv2_del_yes_{selected_no}", type="primary", width="stretch"):
                        delete_quotation_ssot(selected_no)
                        st.session_state.pop(delete_key, None)
                        st.session_state.pop("qv2_selected", None)
                        st.success(f"Quotation {selected_no} deleted.")
                        st.rerun()
                with c_del_no:
                    if st.button("Cancel", key=f"qv2_del_no_{selected_no}", width="stretch"):
                        st.session_state.pop(delete_key, None)
                        st.rerun()

    # Expandable Details & Edit
    if can_edit:
        with st.expander("✏️ Edit Quotation Details & Charges", expanded=False):
            _render_edit_form(selected, user)
