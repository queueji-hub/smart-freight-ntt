from __future__ import annotations
"""
Payment Voucher (AP Workspace) — Progress Transport Systems (PTS) Grade
Replicating PTS Screen 2: Multi-line Service Costs, Tax/WHT Summary Matrix,
Paid Info (Cash/Cheque/Bank), Supplier Tax Invoice (Input VAT), and Withholding Tax 50 ทวิ (ภ.ง.ด. 3/53).
"""

import os
from datetime import date, datetime
from typing import Any, Dict, List, Optional
import pandas as pd
import streamlit as st

from managers.ap_manager import (
    calculate_ap_summary, create_ap_voucher, get_ap_voucher, get_ap_vouchers, update_ap_voucher_status
)
from managers.vendor_manager import get_vendors
from managers.shipment_manager import list_shipments
from managers.profit_manager import get_cost_lines
from managers.charge_master_manager import list_charges
from views.document_ui import render_document_section
from ui.design_system import page_header, section

PAYMENT_TYPES = [
    "General Payment",
    "Ocean Freight",
    "Air Freight",
    "Port Terminal Cost (THC / ท่าเรือ)",
    "Customs Clearance & Formalities",
    "Inland Transport / Trucking",
    "Advance Customs Duty & Tax",
    "Overseas Agent Settlement",
]

THAI_BANKS = [
    "BBL - BANGKOK BANK",
    "KBANK - KASIKORNBANK",
    "SCB - SIAM COMMERCIAL BANK",
    "KTB - KRUNG THAI BANK",
    "TTB - TMBTHANACHART BANK",
    "BAY - BANK OF AYUDHYA (KRUNGSRI)",
    "UOB - UNITED OVERSEAS BANK",
    "GSB - GOVERNMENT SAVINGS BANK",
]


def _print_pv_pdf(voucher_id: int) -> None:
    bytes_key = f"ap_pv_bytes_{voucher_id}"
    name_key = f"ap_pv_name_{voucher_id}"
    if st.button("🖨️ Print PV & WHT 50 ทวิ", key=f"ap_print_btn_{voucher_id}", type="primary", use_container_width=True):
        try:
            from pdf.payment_voucher_pdf import generate_payment_voucher_pdf
            voucher = get_ap_voucher(voucher_id)
            if not voucher:
                st.error("Voucher not found.")
                return
            items = voucher.get("items") or []
            pdf_path = generate_payment_voucher_pdf(voucher, items)
            if pdf_path and os.path.exists(pdf_path):
                with open(pdf_path, "rb") as fh:
                    st.session_state[bytes_key] = fh.read()
                st.session_state[name_key] = os.path.basename(pdf_path)
            else:
                st.error("Failed to generate PV PDF.")
        except Exception as exc:
            st.error(f"Error building PDF: {exc}")

    if st.session_state.get(bytes_key):
        st.download_button(
            "⬇️ Download Payment Voucher PDF",
            st.session_state[bytes_key],
            file_name=st.session_state.get(name_key, f"PV_{voucher_id}.pdf"),
            mime="application/pdf",
            key=f"ap_download_btn_{voucher_id}",
            use_container_width=True,
        )


def _render_pts_pv_create():
    st.markdown("""
        <div style="background-color: #eff6ff; border: 1px solid #93c5fd; border-radius: 8px; padding: 12px; margin-bottom: 16px;">
            <span style="font-size: 1.15rem; font-weight: 700; color: #1e40af;">💳 Payment Voucher Entry (บันทึกใบสำคัญจ่ายเจ้าหนี้ / ค่าใช้จ่ายสายเรือ)</span>
        </div>
    """, unsafe_allow_html=True)

    vendors = get_vendors() or []
    v_opts = {f"{v.get('vendor_code', v.get('id'))} — {v.get('legal_name', '')}": v for v in vendors}
    jobs = list_shipments(limit=200) or []
    job_choices = ["— None (General Expense) —"] + [j.get("job_no") for j in jobs if j.get("job_no")]

    # Operational pull from Verified Job Cost Lines
    st.markdown("##### 📥 Pull Verified Cost from Job (ดึงรายการค่าใช้จ่ายจากฝ่ายปฏิบัติการ)")
    sel_job = st.selectbox("Select Master JOB to pull cost lines", job_choices, key="pts_ap_pull_job")

    prefill_vendor_key = None
    prefill_pr_no = ""
    
    if sel_job and not sel_job.startswith("—"):
        job_rec = next((j for j in jobs if j.get("job_no") == sel_job), None)
        if job_rec:
            c_lines = get_cost_lines(job_rec["id"], cost_type="AP")
            if c_lines:
                st.info(f"Found {len(c_lines)} verified cost line(s) for Job {sel_job}.")
                if st.button("⚡ Auto-fill Cost Lines from Job", key="pts_ap_autofill_btn"):
                    st.session_state["pts_pv_items"] = []
                    for c in c_lines:
                        st.session_state["pts_pv_items"].append({
                            "service_id": c.get("matched_charge_code") or "EXP",
                            "service_text": c.get("description") or "Operation Cost",
                            "amount": float(c.get("amount") or 0.0),
                            "vat_rate": 7.0 if "7%" in str(c.get("tax_type", "")) else 0.0,
                            "has_tax": 1 if "7%" in str(c.get("tax_type", "")) else 0,
                            "wht_rate": 1.0 if "1%" in str(c.get("wht_type", "")) else (3.0 if "3%" in str(c.get("wht_type", "")) else 0.0),
                            "pr_no": c.get("voucher_no") or f"PR-{sel_job}",
                            "master_job": sel_job
                        })
                    st.rerun()

    # Initialize line items if empty
    if "pts_pv_items" not in st.session_state:
        st.session_state["pts_pv_items"] = [
            {"service_id": "FRT", "service_text": "SEAFREIGHT CHARGE", "amount": 50400.0, "vat_rate": 7.0, "has_tax": 1, "wht_rate": 1.0, "pr_no": "PR07010019", "master_job": sel_job if not sel_job.startswith("—") else "SE0701018"},
            {"service_id": "THC", "service_text": "TERMINAL HANDLING CHARGE", "amount": 2500.0, "vat_rate": 7.0, "has_tax": 1, "wht_rate": 3.0, "pr_no": "PR07010019", "master_job": sel_job if not sel_job.startswith("—") else "SE0701018"},
            {"service_id": "CFS", "service_text": "CFS RECEIVING CHARGE", "amount": 1250.0, "vat_rate": 7.0, "has_tax": 1, "wht_rate": 3.0, "pr_no": "PR07010019", "master_job": sel_job if not sel_job.startswith("—") else "SE0701018"},
            {"service_id": "BLF", "service_text": "BILL OF LADING FEE", "amount": 500.0, "vat_rate": 7.0, "has_tax": 1, "wht_rate": 1.0, "pr_no": "PR07010019", "master_job": sel_job if not sel_job.startswith("—") else "SE0701018"},
        ]

    # 1. TOP HEADER ROW
    h1, h2, h3, h4 = st.columns([1.5, 1.2, 1.2, 1.8])
    pv_no_input = h1.text_input("Payment No. (เลขที่ใบสำคัญจ่าย)", placeholder="Auto (PV...)", key="pts_pv_no")
    pv_date = h2.date_input("PV Date (วันที่)", date.today(), key="pts_pv_date")
    due_date = h3.date_input("Due Date (ครบกำหนด)", date.today(), key="pts_pv_due")
    pv_type = h4.selectbox("Payment Type", PAYMENT_TYPES, index=0, key="pts_pv_type")

    # 2. SUPPLIER & OPERATIONAL REFERENCES
    col_sup, col_ref = st.columns([1.3, 1.0])

    with col_sup:
        st.markdown("##### 🏢 Supplier Information (ข้อมูลเจ้าหนี้/สายเรือ)")
        if v_opts:
            sel_v_key = st.selectbox("Supplier ID & Name*", list(v_opts.keys()), key="pts_pv_vendor_select")
            chosen_vendor = v_opts[sel_v_key]
            v_id = chosen_vendor["id"]
            v_name = chosen_vendor.get("legal_name", "")
            v_tax_id = chosen_vendor.get("tax_id", "")
        else:
            st.warning("No vendors registered in Master Data.")
            v_id = None
            v_name = ""
            v_tax_id = ""

        pv_desc = st.text_input("Description (รายละเอียดหลัก)", value=f"OBL# {sel_job}" if not sel_job.startswith("—") else "", key="pts_pv_desc")
        pv_note = st.text_area("NOTE (บันทึกช่วยจำ)", height=65, key="pts_pv_note")

    with col_ref:
        st.markdown("##### 📑 Job & Purchase References")
        ms_code = st.selectbox("Master Service", ["SE (Sea Export)", "SI (Sea Import)", "AE (Air Export)", "AI (Air Import)", "TR (Trucking)"], index=0, key="pts_pv_ms")
        ref_job = st.text_input("Ref. Master JOB No.", value="" if sel_job.startswith("—") else sel_job, key="pts_pv_ref_job")
        ref_shp = st.text_input("Ref. Shipment No.", value=f"{ref_job}-01" if ref_job else "", key="pts_pv_ref_shp")
        ref_pr = st.text_input("Ref. Purchase No. (PR No.)", value=f"PR-{ref_job}" if ref_job else "", key="pts_pv_ref_pr")

    st.divider()

    # 3. SERVICE LINE ITEMS GRID
    st.markdown("#### 📋 Expense Service Lines (ตารางรายการค่าใช้จ่าย)")
    
    charge_map = {c.get("charge_code", ""): c for c in (list_charges() or [])}
    items_to_save = []
    
    for i, it in enumerate(st.session_state["pts_pv_items"]):
        with st.container():
            c_id, c_txt, c_amt, c_vat, c_wht, c_pr, c_job, c_act = st.columns([1.2, 2.5, 1.2, 0.9, 1.0, 1.2, 1.2, 0.5])
            
            s_code = c_id.text_input(f"ServiceID #{i+1}", value=it.get("service_id", "SVC"), key=f"pv_it_id_{i}")
            s_txt = c_txt.text_input("ServiceText", value=it.get("service_text", "Service Charge"), key=f"pv_it_txt_{i}")
            s_amt = c_amt.number_input("Amount", min_value=0.0, value=float(it.get("amount", 0.0)), step=100.0, format="%.2f", key=f"pv_it_amt_{i}")
            
            s_vat = c_vat.selectbox("VAT", ["07", "00"], index=0 if it.get("vat_rate", 7.0) > 0 else 1, key=f"pv_it_vat_{i}")
            
            w_idx = 1 if it.get("wht_rate") == 1.0 else (2 if it.get("wht_rate") == 3.0 else (3 if it.get("wht_rate") == 5.0 else 0))
            s_wht = c_wht.selectbox("W/H", ["0%", "1%", "3%", "5%"], index=w_idx, key=f"pv_it_wht_{i}")
            
            s_pr = c_pr.text_input("PrNo", value=it.get("pr_no", ref_pr), key=f"pv_it_pr_{i}")
            s_job = c_job.text_input("MasterJOB", value=it.get("master_job", ref_job), key=f"pv_it_job_{i}")

            vat_rate_val = 7.0 if s_vat == "07" else 0.0
            wht_rate_val = 1.0 if s_wht == "1%" else (3.0 if s_wht == "3%" else (5.0 if s_wht == "5%" else 0.0))

            items_to_save.append({
                "service_id": s_code,
                "service_text": s_txt,
                "amount": s_amt,
                "vat_rate": vat_rate_val,
                "has_tax": 1 if vat_rate_val > 0 else 0,
                "wht_rate": wht_rate_val,
                "pr_no": s_pr,
                "master_job": s_job,
            })

            if c_act.button("❌", key=f"pv_del_it_{i}"):
                st.session_state["pts_pv_items"].pop(i)
                st.rerun()

    if st.button("➕ Add Expense Line (เพิ่มรายการค่าใช้จ่าย)", key="pv_add_line_btn"):
        st.session_state["pts_pv_items"].append({
            "service_id": "EXP", "service_text": "", "amount": 0.0, "vat_rate": 7.0, "has_tax": 1, "wht_rate": 3.0, "pr_no": ref_pr, "master_job": ref_job
        })
        st.rerun()

    # 4. SUMMARY CALCULATION MATRIX
    st.divider()
    calc_l, calc_r = st.columns([1.1, 1.2])

    with calc_l:
        st.markdown("##### ⚙️ Adjustments & Rounding")
        less_vat_diff = st.number_input("Less Vat DIFF (ปรับลดยอด VAT)", value=0.0, step=0.1, key="pts_pv_less_vat")
        plus_wht_diff = st.number_input("Plus WH Tax DIFF (ปรับยอด WHT)", value=0.0, step=0.1, key="pts_pv_plus_wht")
        diff_amount = st.number_input("Amount (Default +/- ปรับเศษสตางค์)", value=0.0, step=0.01, format="%.2f", key="pts_pv_diff")

    summary = calculate_ap_summary(
        items_to_save,
        less_vat_diff=less_vat_diff,
        plus_wht_diff=plus_wht_diff,
        diff_amount=diff_amount
    )

    with calc_r:
        st.markdown("##### 📊 AP Financial Summary Matrix")
        s1, s2 = st.columns(2)
        s1.markdown(f"**Amount No VAT:** {summary['amount_no_vat']:,.2f} THB")
        s1.markdown(f"**Amount VAT:** {summary['amount_vat']:,.2f} THB")
        s1.markdown(f"**Subtotal:** {summary['subtotal']:,.2f} THB")
        s1.markdown(f"**VAT (7%):** {summary['tax']:,.2f} THB")

        s2.markdown(f"**Total Amount (ยอดรวม):** {summary['total']:,.2f} THB")
        s2.markdown(f"**ยอดรวมหัก ณ ที่จ่าย:** <span style='color: #dc2626; font-weight: 700;'>{summary['wht_total']:,.2f} THB</span>", unsafe_allow_html=True)
        
        st.markdown(f"""
            <div style="background-color: #dbeafe; border: 2px solid #3b82f6; border-radius: 6px; padding: 10px; text-align: right; margin-top: 8px;">
                <span style="font-size: 0.95rem; color: #1e40af; font-weight: 600;">Net Payable (ยอดจ่ายสุทธิหลังหักภาษี):</span><br/>
                <span style="font-size: 1.45rem; font-weight: 800; color: #1e3a8a;">{summary['net_payable']:,.2f} THB</span>
            </div>
        """, unsafe_allow_html=True)

    st.divider()

    # 5. BOTTOM 4 TABS (PAID INFO, SUPPLIER TAX INVOICE, WHT 50 ทวิ, OTHER INFO)
    t_paid, t_tax_inv, t_wht_cert, t_other = st.tabs([
        "💳 Paid Information (การจ่ายชำระ)",
        "🧾 Supplier Tax Invoice / ใบกำกับภาษี",
        "📜 Withholding Tax / หนังสือรับรอง 50 ทวิ",
        "📝 Other Information"
    ])

    with t_paid:
        st.markdown("##### 🏦 Disbursement Details (รายละเอียดการชำระเงิน)")
        p1, p2, p3 = st.columns(3)
        paid_by = p1.selectbox("Pay By", ["Bank Transfer", "Cheque", "Cash"], key="pts_pv_paid_by")
        paid_amt = p2.number_input("Paid Amount", min_value=0.0, value=summary["net_payable"], format="%.2f", key="pts_pv_paid_amt")
        chq_no = p3.text_input("Cheque No. / Transfer Ref.", placeholder="e.g. CHQ-998822", key="pts_pv_chq_no")

        p4, p5, p6 = st.columns(3)
        chq_date = p4.date_input("Cheque / Payment Date", date.today(), key="pts_pv_chq_date")
        bank_name = p5.selectbox("Bank", THAI_BANKS, index=0, key="pts_pv_bank")
        branch_name = p6.text_input("Branch", value="HEAD OFFICE", key="pts_pv_branch")

    with t_tax_inv:
        st.markdown("##### 📄 Supplier Tax Invoice (บันทึกภาษีซื้อเพื่อยื่น ภ.พ. 30)")
        ti1, ti2, ti3 = st.columns(3)
        sup_inv_no = ti1.text_input("Supplier Tax Invoice No.*", placeholder="e.g. IV-2026-8899", key="pts_pv_sup_inv_no")
        sup_inv_date = ti2.date_input("Tax Invoice Date", date.today(), key="pts_pv_sup_inv_date")
        sup_inv_br = ti3.text_input("Supplier Branch No.", value="00000", key="pts_pv_sup_inv_br")

        ti4, ti5 = st.columns(2)
        sup_inv_base = ti4.number_input("Tax Base Amount (ฐานภาษี)", min_value=0.0, value=summary["amount_vat"], format="%.2f", key="pts_pv_sup_base")
        sup_inv_vat = ti5.number_input("Input VAT 7% (ยอดภาษีซื้อ)", min_value=0.0, value=summary["tax"], format="%.2f", key="pts_pv_sup_vat")

    with t_wht_cert:
        st.markdown("##### 📜 Withholding Tax Certificate (หนังสือรับรองการหักภาษี ณ ที่จ่าย 50 ทวิ)")
        w1, w2, w3 = st.columns(3)
        wht_no = w1.text_input("WH TAX No. (เลขที่ 50 ทวิ)", placeholder="Auto (WH...)", key="pts_pv_wht_no")
        wht_date = w2.date_input("WHT Date (วันที่หัก)", date.today(), key="pts_pv_wht_date")
        wht_pnd = w3.selectbox("ภ.ง.ด. Type", ["53 (นิติบุคคล)", "3 (บุคคลธรรมดา)"], key="pts_pv_wht_pnd")

        w4, w5 = st.columns(2)
        wht_base = w4.number_input("WHT Base Amount (มูลค่าที่จ่าย)", min_value=0.0, value=summary["subtotal"], format="%.2f", key="pts_pv_wht_base")
        wht_tax = w5.number_input("WHT Tax Deducted (ภาษีที่หักและนำส่ง)", min_value=0.0, value=summary["wht_total"], format="%.2f", key="pts_pv_wht_tax")

        st.caption(f"ผู้ถูกหัก: **{v_name or '—'}** (Tax ID: {v_tax_id or '—'}) | ผู้มีหน้าที่หัก: **บริษัท ณัฏฐยาราชย์ จำกัด** (0735568004823)")

    with t_other:
        st.markdown("##### 📝 Internal Remarks & Notes")
        st.text_area("Audit Notes", value=pv_note, key="pts_pv_audit_notes")

    # 6. SAVE & SUBMIT ACTIONS
    st.divider()
    b_save, b_clr = st.columns([1, 1])

    if b_save.button("💾 Save & Post Payment Voucher", type="primary", use_container_width=True, key="pts_pv_save_btn"):
        if not v_id:
            st.error("Please select a vendor/supplier.")
            return
        if not items_to_save:
            st.error("Please add at least one expense line.")
            return
        try:
            pnd_clean = "53" if "53" in wht_pnd else "3"
            new_id = create_ap_voucher({
                "voucher_no": pv_no_input.strip() or None,
                "payment_type": pv_type,
                "service_type": ms_code[:2],
                "job_no": ref_job,
                "ref_master_job_no": ref_job,
                "ref_shipment_no": ref_shp,
                "ref_purchase_no": ref_pr,
                "vendor_id": v_id,
                "supplier_name": v_name,
                "supplier_tax_id": v_tax_id,
                "payee_name": v_name,
                "payee_tax_id": v_tax_id,
                "invoice_no": sup_inv_no.strip() or f"V-{ref_job}",
                "invoice_date": pv_date.isoformat(),
                "due_date": due_date.isoformat(),
                "currency": "THB",
                "exchange_rate": 1.0,
                "less_vat_diff": less_vat_diff,
                "plus_wht_diff": plus_wht_diff,
                "diff_amount": diff_amount,
                "paid_by": paid_by,
                "paid_amount": paid_amt,
                "chq_no": chq_no,
                "chq_date": chq_date.isoformat(),
                "bank_name": bank_name,
                "branch_name": branch_name,
                "supplier_tax_inv_no": sup_inv_no.strip(),
                "supplier_tax_inv_date": sup_inv_date.isoformat(),
                "supplier_tax_inv_branch": sup_inv_br,
                "supplier_tax_inv_base": sup_inv_base,
                "supplier_tax_inv_vat": sup_inv_vat,
                "wht_cert_no": wht_no.strip() or None,
                "wht_cert_date": wht_date.isoformat(),
                "wht_pnd_type": pnd_clean,
                "wht_base_amount": wht_base,
                "wht_tax_amount": wht_tax,
                "status": "APPROVED",
                "remark": pv_desc,
            }, items_to_save, st.session_state.get("user"))

            st.success(f"🎉 Payment Voucher created successfully! (ID: {new_id})")
            st.session_state["last_ap_id"] = new_id
            st.rerun()
        except Exception as exc:
            st.error(f"Error creating AP Voucher: {exc}")

    if b_clr.button("🔄 Reset Form", use_container_width=True, key="pts_pv_reset_btn"):
        st.session_state.pop("pts_pv_items", None)
        st.rerun()


def render():
    st.title("💸 Accounts Payable (AP) — Payment Voucher")
    
    tab_list, tab_new, tab_approval = st.tabs([
        "📑 AP Voucher Register (ทะเบียนใบสำคัญจ่าย)",
        "➕ Create Payment Voucher (ออกใบสำคัญจ่าย)",
        "🛡️ Approval & Documents"
    ])

    with tab_list:
        st.subheader("Accounts Payable Vouchers / ทะเบียนเจ้าหนี้การค้า")
        vouchers = get_ap_vouchers()
        if not vouchers:
            st.info("No AP Vouchers found.")
        else:
            # Summary Metrics
            total_ap_amt = sum(float(v.get("total") or 0) for v in vouchers)
            total_ap_wht = sum(float(v.get("wht_total") or 0) for v in vouchers)
            total_ap_net = sum(float(v.get("net_payable") or (float(v.get("total") or 0) - float(v.get("wht_total") or 0))) for v in vouchers)

            m1, m2, m3 = st.columns(3)
            m1.metric("Total AP Amount", f"{total_ap_amt:,.2f} THB")
            m2.metric("Total WHT Deducted (ภาษีหัก)", f"{total_ap_wht:,.2f} THB")
            m3.metric("Net Disbursed (ยอดจ่ายสุทธิ)", f"{total_ap_net:,.2f} THB")

            df = pd.DataFrame([{
                "ID": v.get("id"),
                "PV No.": v.get("voucher_no") or f"PV-{v.get('id')}",
                "Vendor / Payee": v.get("vendor_name"),
                "Invoice Ref": v.get("invoice_no"),
                "Job No.": v.get("job_no") or v.get("ref_master_job_no"),
                "Date": v.get("invoice_date"),
                "Total Amount": f"{float(v.get('total') or 0):,.2f}",
                "WHT Total": f"{float(v.get('wht_total') or 0):,.2f}",
                "Net Payable": f"{float(v.get('net_payable') or 0):,.2f}",
                "Status": v.get("status"),
            } for v in vouchers])
            st.dataframe(df, use_container_width=True, hide_index=True)

            # Selected Document Actions
            choices = [v.get("id") for v in vouchers]
            sel_vid = st.selectbox("Select AP Voucher for Details & PDF", choices, format_func=lambda x: next((f"#{x} — {v.get('voucher_no', 'PV')} ({v.get('vendor_name')})" for v in vouchers if v.get("id") == x), str(x)), key="ap_sel_voucher_reg")
            if sel_vid:
                v_detail = get_ap_voucher(sel_vid)
                if v_detail:
                    st.caption(f"Voucher: **{v_detail.get('voucher_no', 'PV')}** | Payee: **{v_detail.get('vendor_name')}** | Job: **{v_detail.get('job_no', '—')}**")
                    _print_pv_pdf(sel_vid)

    with tab_new:
        _render_pts_pv_create()

    with tab_approval:
        st.subheader("AP Approval & Documents")
        vouchers = get_ap_vouchers()
        if not vouchers:
            st.warning("No vouchers available.")
            return

        for v in vouchers:
            v_no = v.get("voucher_no") or f"PV-{v['id']}"
            with st.expander(f"🧾 AP: {v_no} | Vendor: {v.get('vendor_name')} | Job: {v.get('job_no')} | Status: {v.get('status')}"):
                st.write(f"**Total Amount:** {float(v.get('total') or 0):,.2f} {v.get('currency', 'THB')} | **WHT:** {float(v.get('wht_total') or 0):,.2f} | **Net Payable:** {float(v.get('net_payable') or 0):,.2f}")
                
                c1, c2 = st.columns(2)
                curr_status = v.get("status", "DRAFT")
                all_statuses = ["DRAFT", "REQUESTED", "SUBMITTED", "UNDER_REVIEW", "APPROVED", "POSTED", "REJECTED", "CANCELLED"]
                status_idx = all_statuses.index(curr_status) if curr_status in all_statuses else 0
                new_status = c1.selectbox(
                    "Update Status", 
                    all_statuses,
                    index=status_idx,
                    key=f"ap_stat_{v['id']}"
                )
                if new_status != curr_status:
                    update_ap_voucher_status(v['id'], new_status, st.session_state.get('user'))
                    st.rerun()

                render_document_section("ap_voucher", str(v['id']))
