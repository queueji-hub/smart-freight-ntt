"""Streamlined, agile Quotation workspace for SME Logistics (5-10 users)."""
from __future__ import annotations

import os
from datetime import date, timedelta
from typing import Any, Dict, List

import pandas as pd
import streamlit as st

from config import DEFAULT_TERMS, JOB_TYPES
from managers.auth_manager import can_write
from managers.customer_manager import list_customers
from managers.master_data_manager import list_sales_users
from managers.charge_master_manager import list_charges
from managers.master_data_crud_manager import list_parties, list_ports
from managers.quotation_manager import duplicate_quotation, get_quotation_by_no, list_quotations
from managers.quotation_ssot_service import create_quotation_ssot, update_quotation_ssot, delete_quotation_ssot, set_quotation_status_ssot
from managers.job_handover_service import handover_quotation_to_job
from ui.design_system import page_header, section

CURRENCY_OPTIONS = ["USD", "THB", "EUR", "CNY", "JPY", "SGD", "GBP"]
MODE_OPTIONS = ["SEA", "AIR", "TRUCK", "MULTIMODAL"]
SERVICE_OPTIONS = ["", "FCL", "LCL", "AIR", "FTL", "LTL"]
INCOTERM_OPTIONS = ["", "EXW", "FCA", "FOB", "CFR", "CIF", "DAP", "DDP", "DDU"]
CONTAINER_TYPE_OPTIONS = ["", "20'GP", "40'GP", "40'HC", "45'HC", "20'RF", "40'RF", "20'OT", "40'OT", "20'FR", "40'FR", "LCL", "4W Truck", "6W Truck", "10W Truck", "Trailer"]
PACKAGE_TYPE_OPTIONS = ["", "Cartons", "Pallets", "Wooden Cases", "Crates", "Bags", "Drums", "Rolls", "Boxes", "Packages", "Pieces", "Units"]
UNIT_OPTIONS = ["CONTAINER", "20'GP", "40'GP", "40'HC", "CBM", "KGS", "TON", "SHPMT", "BL", "SET", "TRIP", "TRUCK", "LOT", "PACKAGE", "PALLET", "UNIT"]


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
    customers = list_customers() or []
    sales = list_sales_users() or []
    carriers = list_parties("CARRIER", active_only=True) or []
    ports = list_ports(active_only=True) or []
    charges = list_charges(active_only=True) or []
    customer_dict = {int(r["id"]): r for r in customers if r.get("id")}
    customer_map = {int(r["id"]): r.get("company_name", str(r["id"])) for r in customers if r.get("id")}
    sales_map = {int(r["id"]): (r.get("full_name") or r.get("username") or str(r["id"])) for r in sales if r.get("id")}
    carrier_map = {int(r["id"]): f"{r.get('party_code')} — {r.get('display_name') or r.get('legal_name')}" for r in carriers if r.get("id")}
    port_map = {int(r["id"]): f"{r.get('port_code')} — {r.get('port_name')}, {r.get('country_name') or ''}" for r in ports if r.get("id")}
    
    # Charge map keyed by description or code for intuitive lookup
    charge_map = {}
    for r in charges:
        code = str(r.get("charge_code") or "").strip().upper()
        if code:
            charge_map[code] = r
    return customer_map, customer_dict, sales_map, carrier_map, port_map, charge_map


def _item_editor(charge_map: dict[str, dict[str, Any]], existing: list[dict] | None = None, key: str = "qv2_items") -> list[dict]:
    # Build comprehensive charge labels including all master codes + any custom codes in existing
    charge_labels = {code: f"{code} — {c.get('description', '')}" for code, c in charge_map.items()}
    if not charge_labels:
        charge_labels = {"FRT": "FRT — Freight Charge"}

    rows = []
    for raw in existing or []:
        item = dict(raw or {})
        code = _s(item.get("charge_code")).upper()
        desc = _s(item.get("description"))
        if not code and desc:
            match = next((c for c in charge_map.values() if _s(c.get("description")).lower() == desc.lower()), None)
            code = _s(match.get("charge_code")).upper() if match else ""
        if not code:
            code = "MISC"
        if code not in charge_labels:
            charge_labels[code] = f"{code} — {desc or code}"
        
        qty = float(item.get("quantity") or 1.0)
        rate = float(item.get("unit_rate") or item.get("price") or 0.0)
        unit = _s(item.get("unit"), "CONTAINER").upper()
        # Match unit with UNIT_OPTIONS
        matched_unit = next((u for u in UNIT_OPTIONS if u.upper() == unit), "SHPMT")
        currency = _s(item.get("currency"), "USD").upper()
        if currency not in CURRENCY_OPTIONS:
            currency = "USD"
        
        rows.append({
            "charge_code": code,
            "description": desc or (charge_map.get(code, {}).get("description") or code),
            "unit": matched_unit,
            "currency": currency,
            "quantity": qty,
            "unit_rate": rate,
            "price": qty * rate,
            "remark": _s(item.get("remark")),
        })

    if not rows:
        default_code = next(iter(charge_labels), "OFR")
        master_def = charge_map.get(default_code, {})
        rows = [{
            "charge_code": default_code,
            "description": master_def.get("description") or "Ocean Freight",
            "unit": master_def.get("default_unit") or "CONTAINER",
            "currency": master_def.get("default_currency") or "USD",
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
            "charge_code": st.column_config.SelectboxColumn("Charge Code", options=list(charge_labels.keys()), format_func=lambda x: charge_labels.get(x, str(x)), required=True, width="medium"),
            "description": st.column_config.TextColumn("Description * (ระบุ/แก้ไขรายละเอียดได้)", required=True, width="large"),
            "unit": st.column_config.SelectboxColumn("Unit (หน่วย)", options=UNIT_OPTIONS, required=True, width="small"),
            "currency": st.column_config.SelectboxColumn("Curr", options=CURRENCY_OPTIONS, required=True, width="small"),
            "quantity": st.column_config.NumberColumn("Qty", min_value=0.0, step=1.0, width="small"),
            "unit_rate": st.column_config.NumberColumn("Unit Rate", min_value=0.0, step=10.0, format="%.2f", width="small"),
            "price": st.column_config.NumberColumn("Total Amount", disabled=True, format="%.2f", width="medium"),
            "remark": st.column_config.TextColumn("Remark (หมายเหตุ)", width="medium"),
        },
        key=key,
    )

    output = []
    for row in edited.to_dict("records"):
        code = _s(row.get("charge_code")).upper()
        if not code and not _s(row.get("description")):
            continue
        desc = _s(row.get("description"))
        if not desc and code in charge_map:
            desc = charge_map[code].get("description") or code
        
        qty = float(row.get("quantity") or 1.0)
        rate = float(row.get("unit_rate") or 0.0)
        unit = _s(row.get("unit"), "SHPMT")
        currency = _s(row.get("currency"), "USD").upper()
        
        output.append({
            "charge_code": code or "MISC",
            "description": desc or code or "Charge Item",
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

    with st.form("quotation_v2_create"):
        section("1. Quotation Details (ข้อมูลทั่วไป & ลูกค้า)")
        c1, c2, c3 = st.columns(3)
        with c1:
            cust_keys = list(customer_map)
            customer_id = st.selectbox("Customer * (ลูกค้า)", cust_keys, format_func=lambda x: customer_map[x]) if cust_keys else None
            attention = st.text_input("Attention (ผู้ติดต่อ)")
            tel = st.text_input("Telephone (เบอร์โทร)")
        with c2:
            sales_id = st.selectbox("Salesperson (ผู้ขาย)", list(sales_map), format_func=lambda x: sales_map[x]) if sales_map else None
            customer_email = st.text_input("Customer Email (อีเมล)")
            payment_term = st.text_input("Payment Terms (เงื่อนไขการชำระ)", value="Net 30")
        with c3:
            job_type = st.selectbox("Job Type * (ประเภทงาน)", list(JOB_TYPES.keys()), format_func=lambda x: JOB_TYPES.get(x, x))
            issue_date = st.date_input("Issue Date (วันที่ออก)", today)
            valid_until = st.date_input("Valid Until (ใช้ได้ถึง)", today + timedelta(days=30))

        # Customer Address field (Auto-filled from database if available)
        default_addr = ""
        if customer_id and customer_id in customer_dict:
            c_info = customer_dict[customer_id]
            default_addr = _s(c_info.get("address") or c_info.get("billing_address"))
        customer_address = st.text_area("Customer Address (ที่อยู่ลูกค้า - ดึงจากฐานข้อมูลลูกค้าอัตโนมัติ)", value=default_addr, height=70)

        section("2. Routing & Incoterms (เส้นทางและการส่งมอบ)")
        r1, r2, r3, r4 = st.columns(4)
        with r1:
            mode = st.selectbox("Transport Mode (โหมดขนส่ง)", MODE_OPTIONS)
        with r2:
            service_type = st.selectbox("Service Type (บริการ)", SERVICE_OPTIONS)
        with r3:
            pol_id = st.selectbox("POL (ท่าเรือต้นทาง) *", list(port_map), format_func=lambda x: port_map[x]) if port_map else None
        with r4:
            pod_id = st.selectbox("POD (ท่าเรือปลายทาง) *", list(port_map), format_func=lambda x: port_map[x]) if port_map else None

        r5, r6, r7, r8 = st.columns(4)
        with r5:
            origin = st.text_input("Origin (สถานที่รับของต้นทาง)")
        with r6:
            destination = st.text_input("Destination (สถานที่ส่งของปลายทาง)")
        with r7:
            incoterm = st.selectbox("Incoterm", INCOTERM_OPTIONS)
        with r8:
            freight_term = st.selectbox("Freight Term", ["", "Prepaid", "Collect"])

        carrier_id = st.selectbox("Preferred Carrier / Liner (สายเรือ / สายการบิน)", ["— None / TBA —"] + list(carrier_map), format_func=lambda x: carrier_map.get(x, x) if isinstance(x, int) else str(x)) if carrier_map else None
        if isinstance(carrier_id, str):
            carrier_id = None

        section("3. Cargo Specifications (ข้อมูลสินค้า & ตู้สินค้า)")
        g1, g2, g3 = st.columns(3)
        with g1:
            commodity = st.text_input("Commodity (ชื่อสินค้า)")
            hs_code = st.text_input("HS Code")
        with g2:
            container_type = st.selectbox("Container Type (ขนาดตู้)", CONTAINER_TYPE_OPTIONS)
            container_qty = st.number_input("Container Qty (จำนวนตู้)", min_value=0, step=1, value=1 if container_type and container_type != "LCL" else 0)
        with g3:
            package_type = st.selectbox("Package Type (บรรจุภัณฑ์)", PACKAGE_TYPE_OPTIONS)
            package_qty = st.number_input("Package Qty (จำนวนหีบห่อ)", min_value=0.0, step=1.0, value=0.0)

        w1, w2, w3 = st.columns(3)
        with w1:
            weight_kg = st.number_input("Gross Weight (KG)", min_value=0.0, step=10.0, format="%.2f")
        with w2:
            volume_cbm = st.number_input("Volume (CBM)", min_value=0.0, step=0.1, format="%.3f")
        with w3:
            is_dg = st.checkbox("Dangerous Goods (สินค้าอันตราย / DG)", value=False)

        section("4. Pricing & Selling Charges (รายการค่าใช้จ่ายและราคาขาย)")
        st.caption("💡 เลือกรายการค่าบริการ หรือพิมพ์ Description, เลือก Unit และ Currency ได้อิสระตามตกลงกับลูกค้า")
        items_df = _item_editor(charge_map, key="qv2_items_create")

        # Summary Metrics
        if items_df:
            totals_by_curr = {}
            for item in items_df:
                curr = item.get("currency", "USD")
                totals_by_curr[curr] = totals_by_curr.get(curr, 0.0) + float(item.get("price") or 0.0)
            st.write("**Total Summary:** " + " | ".join([f"**{tot:,.2f} {curr}**" for curr, tot in totals_by_curr.items()]))

        section("5. Terms & Remarks (เงื่อนไขและหมายเหตุ)")
        subject = st.text_input("Quotation Subject (หัวข้อ)", value=f"{mode} Freight Quotation - {customer_map.get(customer_id, '')}")
        terms = st.text_area("Terms & Conditions (ข้อกำหนดและเงื่อนไข)", value=DEFAULT_TERMS, height=100)

        submitted = st.form_submit_button("💾 Save Quotation as Draft", type="primary", width="stretch")

    if submitted:
        errors = []
        if customer_id is None:
            errors.append("Customer is required (กรุณาเลือกลูกค้า).")
        if valid_until < issue_date:
            errors.append("Valid Until cannot be earlier than Issue Date (วันหมดอายุต้องไม่อยู่ก่อนวันที่ออก).")
        if not items_df:
            errors.append("Please enter at least 1 pricing charge line (กรุณาระบุอย่างน้อย 1 รายการค่าใช้จ่าย).")

        if errors:
            for error in errors:
                st.error(error)
            return

        # Fallback address from customer master if field is left blank
        final_addr = customer_address.strip()
        if not final_addr and customer_id in customer_dict:
            c_rec = customer_dict[customer_id]
            final_addr = _s(c_rec.get("address") or c_rec.get("billing_address"))

        payload = {
            "job_type": job_type,
            "customer_id": customer_id,
            "customer_name": customer_map[customer_id],
            "customer_address": final_addr,
            "sales_id": sales_id,
            "salesperson": sales_map.get(sales_id, "") if sales_id else "",
            "attention": attention.strip(),
            "tel": tel.strip(),
            "customer_email": customer_email.strip(),
            "quotation_date": issue_date.isoformat(),
            "validity_date": valid_until.isoformat(),
            "payment_term": payment_term.strip(),
            "carrier_id": carrier_id,
            "pol_id": pol_id,
            "pod_id": pod_id,
            "pol": port_map.get(pol_id) if pol_id else None,
            "pod": port_map.get(pod_id) if pod_id else None,
            "origin": origin.strip(),
            "destination": destination.strip(),
            "carrier": carrier_map.get(carrier_id) if carrier_id else None,
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
            "status": "Draft",
        }
        try:
            qno = create_quotation_ssot(payload, items_df)
            st.success(f"🎉 Quotation {qno} created successfully!")
            st.session_state.pop("qv2_create", None)
            st.session_state["qv2_selected"] = qno
            st.rerun()
        except Exception as exc:
            st.error(f"Unable to save quotation: {exc}")


def _render_edit_form(selected: Dict[str, Any], user: Dict[str, Any]):
    qno = _s(selected.get("quotation_no"))
    customer_map, customer_dict, sales_map, carrier_map, port_map, charge_map = _master_data()
    today = date.today()

    # Index resolution with robust text-matching fallback
    cust_keys = list(customer_map)
    cur_cust = selected.get("customer_id")
    if cur_cust not in customer_map:
        c_name = _s(selected.get("customer_name")).lower()
        cur_cust = next((cid for cid, name in customer_map.items() if name.lower() == c_name or c_name in name.lower()), cust_keys[0] if cust_keys else None)
    cust_idx = cust_keys.index(cur_cust) if cur_cust in cust_keys else 0

    sales_keys = list(sales_map)
    cur_sales = selected.get("sales_id")
    if cur_sales not in sales_map:
        s_name = _s(selected.get("salesperson") or selected.get("sales_person")).lower()
        cur_sales = next((sid for sid, name in sales_map.items() if s_name and (s_name in name.lower() or name.lower() in s_name)), sales_keys[0] if sales_keys else None)
    sales_idx = sales_keys.index(cur_sales) if cur_sales in sales_keys else 0

    job_keys = list(JOB_TYPES.keys())
    raw_job = _s(selected.get("job_type"), "SE").upper()
    job_aliases = {"SEA_EXP": "SE", "SEA_IMP": "SI", "AIR_EXP": "AE", "AIR_IMP": "AI", "TRK_EXP": "TE", "TRK_IMP": "TI", "SEA_EXPORT": "SE", "SEA_IMPORT": "SI", "AIR_EXPORT": "AE", "AIR_IMPORT": "AI"}
    cur_job = job_aliases.get(raw_job, raw_job)
    if cur_job not in job_keys and job_keys:
        cur_job = job_keys[0]
    job_idx = job_keys.index(cur_job) if cur_job in job_keys else 0

    carrier_keys = list(carrier_map)
    cur_carrier = selected.get("carrier_id")
    if cur_carrier not in carrier_map:
        c_txt = _s(selected.get("carrier")).lower()
        cur_carrier = next((cid for cid, label in carrier_map.items() if c_txt and (c_txt in label.lower() or label.lower() in c_txt)), carrier_keys[0] if carrier_keys else None)
    carrier_idx = carrier_keys.index(cur_carrier) if cur_carrier in carrier_keys else 0

    port_keys = list(port_map)
    cur_pol = selected.get("pol_id")
    if cur_pol not in port_map:
        pol_txt = _s(selected.get("pol")).lower()
        cur_pol = next((pid for pid, label in port_map.items() if pol_txt and (pol_txt in label.lower() or label.lower().startswith(pol_txt[:5]))), port_keys[0] if port_keys else None)
    pol_idx = port_keys.index(cur_pol) if cur_pol in port_keys else 0

    cur_pod = selected.get("pod_id")
    if cur_pod not in port_map:
        pod_txt = _s(selected.get("pod")).lower()
        cur_pod = next((pid for pid, label in port_map.items() if pod_txt and (pod_txt in label.lower() or label.lower().startswith(pod_txt[:5]))), port_keys[0] if port_keys else None)
    pod_idx = port_keys.index(cur_pod) if cur_pod in port_keys else 0

    raw_mode = _s(selected.get("mode"), "SEA").upper()
    cur_mode = next((m for m in MODE_OPTIONS if m in raw_mode or raw_mode in m), "SEA")
    mode_idx = MODE_OPTIONS.index(cur_mode) if cur_mode in MODE_OPTIONS else 0

    raw_serv = _s(selected.get("service_type")).upper()
    cur_serv = next((s for s in SERVICE_OPTIONS if s.upper() == raw_serv), "")
    serv_idx = SERVICE_OPTIONS.index(cur_serv) if cur_serv in SERVICE_OPTIONS else 0

    raw_inco = _s(selected.get("incoterm")).upper()
    cur_inco = next((i for i in INCOTERM_OPTIONS if i.upper() == raw_inco), "")
    inco_idx = INCOTERM_OPTIONS.index(cur_inco) if cur_inco in INCOTERM_OPTIONS else 0

    raw_cont = _s(selected.get("container_type"))
    cur_cont_type = next((c for c in CONTAINER_TYPE_OPTIONS if c.lower() == raw_cont.lower()), "")
    cont_type_idx = CONTAINER_TYPE_OPTIONS.index(cur_cont_type) if cur_cont_type in CONTAINER_TYPE_OPTIONS else 0

    raw_pkg = _s(selected.get("package_type"))
    cur_pkg_type = next((p for p in PACKAGE_TYPE_OPTIONS if p.lower() == raw_pkg.lower()), "")
    pkg_type_idx = PACKAGE_TYPE_OPTIONS.index(cur_pkg_type) if cur_pkg_type in PACKAGE_TYPE_OPTIONS else 0

    # Address fallback from customer database if empty
    curr_addr = _s(selected.get("customer_address"))
    if not curr_addr and cur_cust in customer_dict:
        c_item = customer_dict[cur_cust]
        curr_addr = _s(c_item.get("address") or c_item.get("billing_address"))

    issue_date_val = _date(selected.get("quotation_date"), today)
    valid_until_val = _date(selected.get("validity_date"), issue_date_val + timedelta(days=30))

    with st.form(f"quotation_v2_edit_{qno}"):
        section("1. Quotation Details")
        c1, c2, c3 = st.columns(3)
        with c1:
            customer_id = st.selectbox("Customer *", cust_keys, index=cust_idx, format_func=lambda x: customer_map[x], key=f"edit_cust_{qno}") if cust_keys else None
            attention = st.text_input("Attention", value=_s(selected.get("attention")), key=f"edit_att_{qno}")
            tel = st.text_input("Telephone", value=_s(selected.get("tel")), key=f"edit_tel_{qno}")
        with c2:
            sales_id = st.selectbox("Salesperson", sales_keys, index=sales_idx, format_func=lambda x: sales_map[x], key=f"edit_sales_{qno}") if sales_keys else None
            customer_email = st.text_input("Customer Email", value=_s(selected.get("customer_email")), key=f"edit_email_{qno}")
            payment_term = st.text_input("Payment Terms", value=_s(selected.get("payment_term"), "Net 30"), key=f"edit_pay_{qno}")
        with c3:
            job_type = st.selectbox("Job Type *", job_keys, index=job_idx, format_func=lambda x: JOB_TYPES.get(x, x), key=f"edit_job_{qno}")
            issue_date = st.date_input("Issue Date", issue_date_val, key=f"edit_issue_{qno}")
            valid_until = st.date_input("Valid Until", valid_until_val, key=f"edit_valid_{qno}")

        # Customer Address field in Edit form
        customer_address = st.text_area("Customer Address (ที่อยู่ลูกค้า)", value=curr_addr, height=70, key=f"edit_addr_{qno}")

        section("2. Routing & Incoterms")
        r1, r2, r3, r4 = st.columns(4)
        with r1:
            mode = st.selectbox("Transport Mode", MODE_OPTIONS, index=mode_idx, key=f"edit_mode_{qno}")
        with r2:
            service_type = st.selectbox("Service Type", SERVICE_OPTIONS, index=serv_idx, key=f"edit_serv_{qno}")
        with r3:
            pol_id = st.selectbox("POL", port_keys, index=pol_idx, format_func=lambda x: port_map[x], key=f"edit_pol_{qno}") if port_keys else None
        with r4:
            pod_id = st.selectbox("POD", port_keys, index=pod_idx, format_func=lambda x: port_map[x], key=f"edit_pod_{qno}") if port_keys else None

        r5, r6, r7, r8 = st.columns(4)
        with r5:
            origin = st.text_input("Origin", value=_s(selected.get("origin")), key=f"edit_orig_{qno}")
        with r6:
            destination = st.text_input("Destination", value=_s(selected.get("destination")), key=f"edit_dest_{qno}")
        with r7:
            incoterm = st.selectbox("Incoterm", INCOTERM_OPTIONS, index=inco_idx, key=f"edit_inco_{qno}")
        with r8:
            raw_frt = _s(selected.get("freight_term")).title()
            frt_opts = ["", "Prepaid", "Collect"]
            frt_idx = frt_opts.index(raw_frt) if raw_frt in frt_opts else (1 if raw_frt.lower() == "prepaid" else (2 if raw_frt.lower() == "collect" else 0))
            freight_term = st.selectbox("Freight Term", frt_opts, index=frt_idx, key=f"edit_frt_{qno}")

        carrier_id = st.selectbox("Preferred Carrier", carrier_keys, index=carrier_idx, format_func=lambda x: carrier_map[x], key=f"edit_carr_{qno}") if carrier_keys else None

        section("3. Cargo Specifications")
        g1, g2, g3 = st.columns(3)
        with g1:
            commodity = st.text_input("Commodity", value=_s(selected.get("commodity")), key=f"edit_comm_{qno}")
            hs_code = st.text_input("HS Code", value=_s(selected.get("hs_code")), key=f"edit_hs_{qno}")
        with g2:
            container_type = st.selectbox("Container Type", CONTAINER_TYPE_OPTIONS, index=cont_type_idx, key=f"edit_cont_type_{qno}")
            container_qty = st.number_input("Container Qty", min_value=0, step=1, value=int(selected.get("container_quantity") or 0), key=f"edit_cont_qty_{qno}")
        with g3:
            package_type = st.selectbox("Package Type", PACKAGE_TYPE_OPTIONS, index=pkg_type_idx, key=f"edit_pkg_type_{qno}")
            package_qty = st.number_input("Package Qty", min_value=0.0, step=1.0, value=float(selected.get("quantity") or 0), key=f"edit_pkg_qty_{qno}")

        w1, w2, w3 = st.columns(3)
        with w1:
            weight_kg = st.number_input("Gross Weight (KG)", min_value=0.0, step=10.0, format="%.2f", value=float(selected.get("weight_kg") or 0), key=f"edit_wt_{qno}")
        with w2:
            volume_cbm = st.number_input("Volume (CBM)", min_value=0.0, step=0.1, format="%.3f", value=float(selected.get("volume_cbm") or 0), key=f"edit_cbm_{qno}")
        with w3:
            is_dg = st.checkbox("Dangerous Goods (DG)", value=bool(selected.get("is_dg")), key=f"edit_dg_{qno}")

        section("4. Pricing & Line Items")
        items_df = _item_editor(charge_map, existing=selected.get("items", []), key=f"qv2_edit_items_{qno}")

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
            final_edit_addr = _s(c_rec.get("address") or c_rec.get("billing_address"))

        payload = {
            "job_type": job_type,
            "customer_id": customer_id,
            "customer_name": customer_map[customer_id],
            "customer_address": final_edit_addr,
            "sales_id": sales_id,
            "salesperson": sales_map.get(sales_id, "") if sales_id else "",
            "attention": attention.strip(),
            "tel": tel.strip(),
            "customer_email": customer_email.strip(),
            "quotation_date": issue_date.isoformat(),
            "validity_date": valid_until.isoformat(),
            "payment_term": payment_term.strip(),
            "carrier_id": carrier_id,
            "pol_id": pol_id,
            "pod_id": pod_id,
            "pol": port_map.get(pol_id) if pol_id else None,
            "pod": port_map.get(pod_id) if pod_id else None,
            "origin": origin.strip(),
            "destination": destination.strip(),
            "carrier": carrier_map.get(carrier_id) if carrier_id else None,
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
            # Delete button with confirmation
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
