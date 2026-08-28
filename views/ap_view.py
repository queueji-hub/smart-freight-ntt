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
    calculate_ap_summary, create_ap_voucher, get_ap_voucher, get_ap_vouchers, update_ap_voucher_status, cancel_ap_voucher
)
from managers.vendor_manager import get_vendors
from managers.shipment_manager import list_shipments
from managers.profit_manager import get_cost_lines, update_cost_line
from managers.charge_master_manager import list_charges
from views.document_ui import render_document_section
from ui.design_system import page_header, section
from views.navigation_helper import get_active_tab, redirect_to_tab

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

    # 1. TOP HEADER ROW WITH CURRENCY SELECTION
    h1, h2, h3, h4, h5, h6 = st.columns([1.3, 1.0, 1.0, 1.3, 0.9, 1.1])
    pv_no_input = h1.text_input("Payment No. (เลขที่ใบสำคัญจ่าย)", placeholder="Auto (PV...)", key="pts_pv_no")
    pv_date = h2.date_input("PV Date (วันที่)", date.today(), key="pts_pv_date")
    due_date = h3.date_input("Due Date (ครบกำหนด)", date.today(), key="pts_pv_due")
    pv_type = h4.selectbox("Payment Type", PAYMENT_TYPES, index=0, key="pts_pv_type")
    curr_opts = ["THB", "USD", "EUR", "CNY", "JPY", "SGD"]
    pv_curr = h5.selectbox("Currency *", curr_opts, index=0, key="pts_pv_curr")
    def_ex_map = {"THB": 1.0, "USD": 35.50000, "EUR": 38.50000, "JPY": 0.24000, "CNY": 4.90000, "SGD": 26.50000}
    pv_ex = h6.number_input("Ex.Rate to THB *", min_value=0.00001, value=float(def_ex_map.get(pv_curr, 1.0)), step=0.00001, format="%.5f", key="pts_pv_ex")

    if sel_job and not sel_job.startswith("—"):
        job_rec = next((j for j in jobs if j.get("job_no") == sel_job), None)
        if job_rec:
            c_lines = get_cost_lines(job_rec["id"], cost_type="AP")
            available_c_lines = [c for c in c_lines if not c.get("voucher_no") and c.get("payout_status") in ("UNPAID", "ESTIMATED", None)]
            locked_c_lines = len(c_lines) - len(available_c_lines)
            
            if available_c_lines:
                st.info(f"จ็อบ {sel_job}: พบ {len(available_c_lines)} รายการค่าใช้จ่ายที่พร้อมตั้งเบิก" + (f" (มี {locked_c_lines} รายการที่ถูกตั้งเบิกไปแล้ว)" if locked_c_lines > 0 else ""))
                if st.button(f"⚡ Auto-fill {len(available_c_lines)} Cost Lines from Job (สกุลเงิน {pv_curr})", key="pts_ap_autofill_btn"):
                    st.session_state["pts_pv_items"] = []
                    linked_cost_ids = []
                    for c in available_c_lines:
                        c_curr = c.get("currency", "THB")
                        ex_rate = float(c.get("exchange_rate") or 1.0)
                        orig_amt = float(c.get("amount") or 0.0)
                        amt_thb = float(c.get("amount_thb") or (orig_amt * ex_rate))

                        # Respect target PV currency
                        if pv_curr == c_curr:
                            target_amt = orig_amt
                            desc_text = c.get("description") or "Operation Cost"
                        elif pv_curr == "THB":
                            target_amt = amt_thb
                            desc_text = c.get("description") or "Operation Cost"
                            if c_curr != "THB":
                                desc_text += f" ({orig_amt:,.2f} {c_curr} @ {ex_rate:.5f})"
                        else:
                            target_amt = round(amt_thb / (pv_ex if pv_ex > 0 else 1.0), 2)
                            desc_text = f"{c.get('description') or 'Operation Cost'} ({orig_amt:,.2f} {c_curr})"

                        linked_cost_ids.append(c.get("id"))
                        st.session_state["pts_pv_items"].append({
                            "service_id": c.get("matched_charge_code") or "EXP",
                            "service_text": desc_text,
                            "amount": target_amt,
                            "vat_rate": 7.0 if "7%" in str(c.get("tax_type", "")) else 0.0,
                            "has_tax": 1 if "7%" in str(c.get("tax_type", "")) else 0,
                            "wht_rate": 1.0 if "1%" in str(c.get("wht_type", "")) else (3.0 if "3%" in str(c.get("wht_type", "")) else 0.0),
                            "pr_no": f"PR-{sel_job}",
                            "master_job": sel_job
                        })
                    st.session_state["pts_pv_linked_cost_ids"] = linked_cost_ids
                    st.rerun()
            else:
                st.warning(f"จ็อบ {sel_job}: ไม่มีรายการค่าใช้จ่ายที่พร้อมตั้งเบิก (มีทั้งหมด {len(c_lines)} รายการ ซึ่งถูกตั้งเบิกไปหมดแล้ว)")

    # Initialize line items if empty
    if "pts_pv_items" not in st.session_state:
        st.session_state["pts_pv_items"] = [
            {"service_id": "FRT", "service_text": "SEAFREIGHT CHARGE", "amount": 50400.0, "vat_rate": 7.0, "has_tax": 1, "wht_rate": 1.0, "pr_no": "PR07010019", "master_job": sel_job if not sel_job.startswith("—") else "SE0701018"},
        ]

    # 2. SUPPLIER & OPERATIONAL REFERENCES
    col_sup, col_ref = st.columns([1.3, 1.0])

    with col_sup:
        st.markdown("##### 🏢 Supplier / Payee (ข้อมูลเจ้าหนี้ / สายเรือ / ค่าหัวลาก / ท่าเรือ)")
        if v_opts:
            sel_v_key = st.selectbox(
                "Select Supplier / Carrier / Transporter *",
                list(v_opts.keys()),
                format_func=lambda k: f"{v_opts[k].get('party_code') or v_opts[k].get('vendor_code')} — {v_opts[k].get('display_name') or v_opts[k].get('legal_name')}",
                key="pts_pv_vendor_select"
            )
            chosen_vendor = v_opts[sel_v_key]
            v_id = chosen_vendor["id"]
            v_name = chosen_vendor.get("legal_name") or chosen_vendor.get("display_name", "")
            v_tax_id = chosen_vendor.get("tax_id", "")
            st.caption(f"📌 **Tax ID:** {v_tax_id or '—'} | **Branch:** {chosen_vendor.get('branch_no', '00000')}")
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
    st.markdown(f"#### 📋 Expense Service Lines (ตารางรายการค่าใช้จ่าย — สกุลเงิน {pv_curr})")
    
    charge_map = {c.get("charge_code", ""): c for c in (list_charges() or [])}
    items_to_save = []
    
    for i, it in enumerate(st.session_state["pts_pv_items"]):
        with st.container():
            c_id, c_txt, c_amt, c_vat, c_wht, c_pr, c_job, c_act = st.columns([1.2, 2.5, 1.2, 0.9, 1.0, 1.2, 1.2, 0.5])
            
            s_code = c_id.text_input(f"ServiceID #{i+1}", value=it.get("service_id", "SVC"), key=f"pv_it_id_{i}")
            s_txt = c_txt.text_input("ServiceText", value=it.get("service_text", "Service Charge"), key=f"pv_it_txt_{i}")
            s_amt = c_amt.number_input(f"Amount ({pv_curr})", min_value=0.0, value=float(it.get("amount", 0.0)), step=100.0, format="%.2f", key=f"pv_it_amt_{i}")
            
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
        less_vat_diff = st.number_input("Less Vat DIFF", value=0.0, step=0.1, key="pts_pv_less_vat")
        plus_wht_diff = st.number_input("Plus WH Tax DIFF", value=0.0, step=0.1, key="pts_pv_plus_wht")
        diff_amount = st.number_input("Amount Adjust", value=0.0, step=0.01, format="%.2f", key="pts_pv_diff")

    summary = calculate_ap_summary(items_to_save, less_vat_diff=less_vat_diff, plus_wht_diff=plus_wht_diff, diff_amount=diff_amount)

    with calc_r:
        st.markdown(f"##### 📊 AP Financial Summary Matrix ({pv_curr})")
        s1, s2 = st.columns(2)
        s1.markdown(f"**Amount No VAT:** {summary['amount_no_vat']:,.2f} {pv_curr}")
        s1.markdown(f"**Amount VAT:** {summary['amount_vat']:,.2f} {pv_curr}")
        s1.markdown(f"**Subtotal:** {summary['subtotal']:,.2f} {pv_curr}")
        s1.markdown(f"**VAT (7%):** {summary['tax']:,.2f} {pv_curr}")
        s2.markdown(f"**Total Amount:** {summary['total']:,.2f} {pv_curr}")
        s2.markdown(f"**ยอดรวมหัก ณ ที่จ่าย:** <span style='color: #dc2626; font-weight: 700;'>{summary['wht_total']:,.2f} {pv_curr}</span>", unsafe_allow_html=True)
        st.markdown(f"""
            <div style="background-color: #dbeafe; border: 2px solid #3b82f6; border-radius: 6px; padding: 10px; text-align: right; margin-top: 8px;">
                <span style="font-size: 0.95rem; color: #1e40af; font-weight: 600;">Net Payable:</span><br/>
                <span style="font-size: 1.45rem; font-weight: 800; color: #1e3a8a;">{summary['net_payable']:,.2f} {pv_curr}</span>
            </div>
        """, unsafe_allow_html=True)

    st.divider()

    # 5. PAID INFORMATION
    st.markdown("#### 💵 Paid Information (ช่องทางการจ่ายเงิน / เช็ค / โอนธนาคาร)")
    p_c1, p_c2, p_c3, p_c4 = st.columns([1.2, 1.2, 1.2, 1.4])
    paid_by = p_c1.selectbox("Paid By *", ["Bank Transfer", "Cheque", "Cash", "Petty Cash"], index=0, key="pts_pv_paid_by")
    paid_amt = p_c2.number_input("Paid Amount", min_value=0.0, value=float(summary["net_payable"]), format="%.2f", key="pts_pv_paid_amt")
    chq_no = p_c3.text_input("Cheque No. / Ref", placeholder="e.g. CHQ-998811", key="pts_pv_chq_no")
    chq_date = p_c4.date_input("Payment / Cheque Date", date.today(), key="pts_pv_chq_date")
    b_c1, b_c2 = st.columns(2)
    bank_name = b_c1.selectbox("From Bank", THAI_BANKS, index=0, key="pts_pv_bank")
    branch_name = b_c2.text_input("Branch Name", value="HEAD OFFICE / สำนักงานใหญ่", key="pts_pv_branch")

    st.divider()

    # 6. SUPPLIER TAX INVOICE & WHT 50 ทวิ
    st.markdown("#### 🧾 Supplier Tax Invoice & Withholding Tax 50 ทวิ")
    st_c1, st_c2 = st.columns(2)
    with st_c1:
        st.markdown("##### 📄 Supplier Tax Invoice")
        sup_inv_no = st.text_input("Tax Invoice No. *", placeholder="e.g. TAXINV-2026-009", key="pts_pv_sup_inv_no")
        sup_inv_date = st.date_input("Tax Invoice Date", date.today(), key="pts_pv_sup_inv_date")
        sup_inv_br = st.text_input("Supplier Branch No.", value="00000", key="pts_pv_sup_inv_br")
        si_1, si_2 = st.columns(2)
        sup_inv_base = si_1.number_input("Tax Base Amount", min_value=0.0, value=float(summary["amount_vat"]), format="%.2f", key="pts_pv_sup_base")
        sup_inv_vat = si_2.number_input("Tax VAT Amount", min_value=0.0, value=float(summary["tax"]), format="%.2f", key="pts_pv_sup_vat")

    with st_c2:
        st.markdown("##### 📜 Withholding Tax 50 ทวิ (ภ.ง.ด. 3/53)")
        wht_no = st.text_input("WHT Cert No.", placeholder="Auto-generated", key="pts_pv_wht_no")
        wht_date = st.date_input("WHT Cert Date", date.today(), key="pts_pv_wht_date")
        wht_pnd = st.selectbox("P.N.D. Category", ["ภ.ง.ด. 53 (นิติบุคคล)", "ภ.ง.ด. 3 (บุคคลธรรมดา)"], index=0, key="pts_pv_wht_pnd")
        wh_1, wh_2 = st.columns(2)
        wht_base = wh_1.number_input("WHT Base Amount", min_value=0.0, value=float(summary["amount_no_vat"] + summary["amount_vat"]), format="%.2f", key="pts_pv_wht_base")
        wht_tax = wh_2.number_input("WHT Deducted Amount", min_value=0.0, value=float(summary["wht_total"]), format="%.2f", key="pts_pv_wht_tax")

    st.divider()

    # 7. BOTTOM ACTION BUTTONS
    b_sav, b_clr = st.columns([1.5, 1.0])
    if b_sav.button("💾 Save Payment Voucher & WHT 50 ทวิ", type="primary", use_container_width=True, key="pts_pv_submit_btn"):
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
                "payee_name": v_name,
                "payee_tax_id": v_tax_id,
                "invoice_no": sup_inv_no.strip() or f"V-{ref_job}",
                "invoice_date": pv_date.isoformat(),
                "due_date": due_date.isoformat(),
                "currency": pv_curr,
                "exchange_rate": pv_ex,
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

            pulled_cost_ids = st.session_state.get("pts_pv_linked_cost_ids", [])
            if pulled_cost_ids:
                created_v = get_ap_voucher(new_id)
                v_no_gen = created_v.get("voucher_no") if created_v else f"PV-{new_id}"
                for cid in pulled_cost_ids:
                    try:
                        update_cost_line(cid, {"payout_status": "REQUESTED", "voucher_no": v_no_gen})
                    except Exception:
                        pass
                st.session_state.pop("pts_pv_linked_cost_ids", None)

            st.session_state.pop("pts_pv_items", None)
            st.session_state["last_ap_id"] = new_id
            st.session_state["ap_sel_voucher_reg"] = new_id
            redirect_to_tab("ap_active_tab", "📑 AP Voucher Register (ทะเบียนใบสำคัญจ่าย)")
            st.success(f"🎉 Payment Voucher created successfully! (ID: {new_id})")
            st.rerun()
        except Exception as exc:
            st.error(f"Error creating AP Voucher: {exc}")

    if b_clr.button("🔄 Reset Form", use_container_width=True, key="pts_pv_reset_btn"):
        st.session_state.pop("pts_pv_items", None)
        st.session_state.pop("pts_pv_linked_cost_ids", None)
        redirect_to_tab("ap_active_tab", "📑 AP Voucher Register (ทะเบียนใบสำคัญจ่าย)")
        st.rerun()


def render():
    st.title("💸 Accounts Payable (AP) — Payment Voucher")
    
    tab_opts = [
        "📑 AP Voucher Register (ทะเบียนใบสำคัญจ่าย)",
        "➕ Create Payment Voucher (ออกใบสำคัญจ่าย)",
        "🛡️ Approval & Documents"
    ]
    get_active_tab("ap_active_tab", tab_opts)

    active_tab = st.radio("AP Navigation", tab_opts, horizontal=True, key="ap_active_tab", label_visibility="collapsed")

    if active_tab == tab_opts[0]:
        st.subheader("Accounts Payable Vouchers / ทะเบียนเจ้าหนี้การค้า")
        vouchers = get_ap_vouchers()
        if not vouchers:
            st.info("No AP Vouchers found.")
        else:
            total_ap_amt = sum(float(v.get("total") or 0) for v in vouchers if v.get("status") != "CANCELLED")
            total_ap_wht = sum(float(v.get("wht_total") or 0) for v in vouchers if v.get("status") != "CANCELLED")
            total_ap_net = sum(float(v.get("net_payable") or (float(v.get("total") or 0) - float(v.get("wht_total") or 0))) for v in vouchers if v.get("status") != "CANCELLED")

            m1, m2, m3 = st.columns(3)
            m1.metric("Total AP Active Amount", f"{total_ap_amt:,.2f} THB")
            m2.metric("Total WHT Deducted (ภาษีหัก)", f"{total_ap_wht:,.2f} THB")
            m3.metric("Net Disbursed (ยอดจ่ายสุทธิ)", f"{total_ap_net:,.2f} THB")

            df = pd.DataFrame([{
                "ID": v.get("id"),
                "PV No.": v.get("voucher_no") or f"PV-{v.get('id')}",
                "Vendor / Payee": v.get("vendor_name"),
                "Invoice Ref": v.get("invoice_no"),
                "Job No.": v.get("job_no") or v.get("ref_master_job_no"),
                "Currency": v.get("currency", "THB"),
                "Total Amount": f"{float(v.get('total') or 0):,.2f}",
                "WHT Total": f"{float(v.get('wht_total') or 0):,.2f}",
                "Net Payable": f"{float(v.get('net_payable') or 0):,.2f}",
                "Status": v.get("status"),
            } for v in vouchers])
            st.dataframe(df, use_container_width=True, hide_index=True)

            choices = [v.get("id") for v in vouchers]
            sel_idx = 0
            cur_sel = st.session_state.get("ap_sel_voucher_reg")
            if cur_sel in choices: sel_idx = choices.index(cur_sel)
            sel_vid = st.selectbox("Select AP Voucher for Details & PDF", choices, index=sel_idx, format_func=lambda x: next((f"#{x} — {v.get('voucher_no', 'PV')} ({v.get('vendor_name')}) [{v.get('status', 'ACTIVE')}]" for v in vouchers if v.get("id") == x), str(x)), key="ap_sel_voucher_reg")
            
            if sel_vid:
                v_detail = get_ap_voucher(sel_vid)
                if v_detail:
                    st.caption(f"Voucher: **{v_detail.get('voucher_no', 'PV')}** | Payee: **{v_detail.get('vendor_name')}** | Status: **{v_detail.get('status')}**")
                    c_act1, c_act2 = st.columns([2, 1])
                    with c_act1: _print_pv_pdf(sel_vid)
                    with c_act2:
                        if v_detail.get("status") != "CANCELLED":
                            if st.button("🔄 Rollback / ยกเลิก Voucher", key=f"ap_cancel_btn_{sel_vid}", type="secondary", use_container_width=True):
                                try:
                                    cancel_ap_voucher(sel_vid, user=st.session_state.get("user"))
                                    st.success(f"ยกเลิกใบสำคัญจ่าย #{sel_vid} สำเร็จ!")
                                    st.rerun()
                                except Exception as exc: st.error(f"Failed to cancel voucher: {exc}")
                        else: st.warning("⚠️ เอกสารนี้ถูกยกเลิกแล้ว (CANCELLED)")

    elif active_tab == tab_opts[1]:
        _render_pts_pv_create()

    elif active_tab == tab_opts[2]:
        st.subheader("AP Approval & Documents")
        vouchers = get_ap_vouchers()
        if not vouchers: st.warning("No vouchers available."); return

        for v in vouchers:
            v_no = v.get("voucher_no") or f"PV-{v['id']}"
            with st.expander(f"🧾 AP: {v_no} | Vendor: {v.get('vendor_name')} | Job: {v.get('job_no')} | Status: {v.get('status')}"):
                st.write(f"**Total Amount:** {float(v.get('total') or 0):,.2f} {v.get('currency', 'THB')} | **WHT:** {float(v.get('wht_total') or 0):,.2f} | **Net Payable:** {float(v.get('net_payable') or 0):,.2f}")
                c1, c2, c3 = st.columns([1.5, 1.5, 1.0])
                curr_status = v.get("status", "DRAFT")
                all_statuses = ["DRAFT", "REQUESTED", "SUBMITTED", "UNDER_REVIEW", "APPROVED", "POSTED", "REJECTED", "CANCELLED"]
                new_status = c1.selectbox(
                    "Update Status",
                    all_statuses,
                    index=status_idx,
                    key=f"ap_stat_{v['id']}"
                )
                if new_status != curr_status:
                    if new_status == "CANCELLED":
                        cancel_ap_voucher(v["id"], user=st.session_state.get("user"))
                    else:
                        update_ap_voucher_status(v["id"], new_status)
                    st.success(f"Updated status to {new_status}")
                    st.rerun()

                with c2:
                    render_document_section(
                        doc_type="PAYMENT_VOUCHER",
                        doc_id=v["id"],
                        job_no=v.get("job_no"),
                        user=st.session_state.get("user")
                    )

                with c3:
                    if v.get("status") != "CANCELLED":
                        if st.button("🔄 Rollback Voucher", key=f"ap_app_cancel_{v['id']}", use_container_width=True):
                            cancel_ap_voucher(v["id"], user=st.session_state.get("user"))
                            st.success(f"Cancelled voucher #{v_no}")
                            st.rerun()
