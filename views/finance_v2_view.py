from __future__ import annotations
"""
Receipt & Tax Receipt (AR Workspace) — Progress Transport Systems (PTS) Grade
Faithfully replicating PTS Screen 1: Multi-Currency Grid, Tax/WHT Breakdown,
Collection Parts (Cash/Cheque/Transfer/Bank), and Shipment Reference Metadata.
"""

import os
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional
import pandas as pd
import streamlit as st

from managers.auth_manager import can_write
from managers.charge_master_manager import list_charges
from managers.customer_manager import list_customers
from managers.document_approval_manager import approve_document, can_approve, get_approval_status, submit_for_approval
from managers.document_duplicate_service import duplicate_invoice, get_invoice_snapshot, update_invoice_draft
from managers.invoice_manager import (
    TAX_TYPES, WHT_TYPES, calculate_summary, create_invoice, list_invoices, record_payment
)
from managers.shipment_manager import list_shipments
from ui.design_system import page_header, section
from views.navigation_helper import get_active_tab, redirect_to_tab

CURRENCIES = ["THB", "USD", "EUR", "CNY", "JPY", "SGD"]
SERVICES = [
    "Seafreight Export",
    "Seafreight Import",
    "Airfreight Export",
    "Airfreight Import",
    "Cross-border Trucking",
    "Customs Clearance",
    "Domestic Transport",
]
PAYMENT_CHANNELS = ["Cash", "Cheque", "Transfer", "Account"]
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
DOC_TYPES = {
    "RC": "ใบเสร็จรับเงิน / ใบกำกับภาษี — Receipt & Tax Receipt",
    "INV": "ใบแจ้งหนี้ — Commercial Invoice",
    "BN": "ใบวางบิล — Billing Note",
    "CN": "ใบลดหนี้ — Credit Note",
    "DN": "ใบเพิ่มหนี้ — Debit Note",
    "SOA": "ใบแจ้งยอดบัญชี — Statement of Account",
}


def _status(doc_no: str, fallback: str = "Active") -> str:
    try:
        stat = get_approval_status("invoice", doc_no)
        return stat if stat else fallback
    except Exception:
        return fallback or "Active"


def _customer_master() -> Dict[int, Dict[str, Any]]:
    customers = list_customers() or []
    return {int(c["id"]): c for c in customers if c.get("id")}


def _charge_master() -> Dict[str, Dict[str, Any]]:
    charges = list_charges() or []
    return {c.get("charge_code") or c.get("code") or "": c for c in charges if c.get("charge_code") or c.get("code")}


def _pdf(doc_no: str) -> None:
    bytes_key = f"finance_pdf_bytes_{doc_no}"
    name_key = f"finance_pdf_name_{doc_no}"
    if st.button("🖨️ Print / PDF", key=f"finance_pdf_{doc_no}", type="primary", use_container_width=True):
        try:
            from pdf.invoice_pdf import generate_invoice_pdf
            from pdf.receipt_pdf import generate_receipt_pdf
            invoice, items = get_invoice_snapshot(doc_no)
            status_val = _status(doc_no, invoice.get("status"))
            
            # Map customer details
            cid = invoice.get("customer_id")
            customer = _customer_master().get(int(cid)) if cid else None
            payload = {**invoice, "items": items, "approval_status": status_val, "status": status_val}
            
            if str(doc_no).startswith("INV") or invoice.get("doc_type") == "INV":
                output = generate_invoice_pdf(payload, customer=customer)
            else:
                output = generate_receipt_pdf(payload, customer=customer)

            if not output or not os.path.exists(output):
                raise FileNotFoundError("PDF generator failed to build file.")
            with open(output, "rb") as fh:
                st.session_state[bytes_key] = fh.read()
            st.session_state[name_key] = os.path.basename(output)
        except Exception as exc:
            st.error(f"Unable to generate PDF: {exc}")

    if st.session_state.get(bytes_key):
        st.download_button(
            "⬇️ Download PDF",
            st.session_state[bytes_key],
            file_name=st.session_state.get(name_key, f"{doc_no}.pdf"),
            mime="application/pdf",
            key=f"finance_download_{doc_no}",
            use_container_width=True,
        )


def _new(user: Dict[str, Any]) -> None:
    _render_pts_receipt_form(user)


def _edit(doc_no: str) -> None:
    st.info(f"Editing document {doc_no}")


def _payments() -> None:
    st.info("Direct payment entry is available under the Payment Register tab.")


def _render_pts_receipt_form(user: Dict[str, Any], doc_type_default: str = "RC") -> None:
    """Renders the comprehensive PTS Receipt & Tax Receipt input form."""
    cust_map = _customer_master()
    charge_map = _charge_master()
    jobs = list_shipments(limit=200) or []
    job_map = {j.get("job_no"): j for j in jobs if j.get("job_no")}

    st.markdown("""
        <div style="background-color: #f0fdf4; border: 1px solid #86efac; border-radius: 8px; padding: 12px; margin-bottom: 16px;">
            <span style="font-size: 1.15rem; font-weight: 700; color: #166534;">🧾 Receipt & Tax Receipt Entry (ระบบบันทึกใบเสร็จรับเงิน / ใบกำกับภาษี)</span>
        </div>
    """, unsafe_allow_html=True)

    # Initialize state for multi-line charge items if not set
    if "pts_rc_items" not in st.session_state:
        st.session_state["pts_rc_items"] = [
            {"charge_code": "OF", "description": "SEAFREIGHT CHARGE", "pc_type": "PP-E", "price": 55.0, "curr": "USD", "qty": 20.0, "unit": "M3", "exch_rate": 35.0, "tax_type": "VAT 7%", "wht_type": "None"},
            {"charge_code": "THC-O", "description": "TERMINAL HANDLING CHARGE", "pc_type": "PP-E", "price": 750.0, "curr": "THB", "qty": 1.0, "unit": "SHP", "exch_rate": 1.0, "tax_type": "VAT 7%", "wht_type": "WHT 1%"},
            {"charge_code": "CFS", "description": "CFS RECEIVING CHARGE", "pc_type": "PP-E", "price": 750.0, "curr": "THB", "qty": 1.0, "unit": "SHP", "exch_rate": 1.0, "tax_type": "VAT 7%", "wht_type": "WHT 3%"},
            {"charge_code": "DO", "description": "BILL OF LADING FEE", "pc_type": "PP-E", "price": 500.0, "curr": "THB", "qty": 1.0, "unit": "SET", "exch_rate": 1.0, "tax_type": "VAT 7%", "wht_type": "WHT 3%"},
        ]

    # Initialize state for collection parts
    if "pts_collection_parts" not in st.session_state:
        st.session_state["pts_collection_parts"] = [
            {"pay_by": "Transfer", "amount": 0.0, "chq_no": "TRF-001", "date": date.today().isoformat(), "bank": "BBL - BANGKOK BANK", "branch": "HEAD OFFICE"}
        ]

    # 1. TOP HEADER & METADATA
    c1, c2, c3, c4 = st.columns([1.5, 1.2, 1.0, 1.8])
    rc_no_input = c1.text_input("Receipt No. (เลขที่ใบเสร็จ)", placeholder="Auto-generated if blank", key="pts_rc_no")
    rc_date = c2.date_input("Receipt Date (วันที่)", date.today(), key="pts_rc_date")
    rc_status = c3.selectbox("Status", ["Active", "Cancelled"], index=0, key="pts_rc_status")
    rc_service = c4.selectbox("Service", SERVICES, index=0, key="pts_rc_service")

    # 2. CUSTOMER & SHIPMENT INFORMATION BOXES
    left_col, right_col = st.columns([1.3, 1.0])

    with left_col:
        st.markdown("##### 🏢 Customer Information (ข้อมูลลูกค้า)")
        c_opts = list(cust_map.keys())
        sel_cid = st.selectbox(
            "Customer ID & Name*",
            c_opts,
            format_func=lambda x: f"{cust_map[x].get('customer_code', x)} — {cust_map[x].get('company_name', '')}",
            key="pts_rc_cust_select"
        )
        selected_cust = cust_map.get(sel_cid, {})
        default_addr = selected_cust.get("address") or selected_cust.get("billing_address") or ""
        default_tax_id = selected_cust.get("tax_id") or ""
        
        cust_addr = st.text_area("Billing Address / Customer Address", value=default_addr, height=70, key="pts_rc_cust_addr")
        st.caption(f"Tax ID: {default_tax_id or '—'}")
        
        st.markdown("##### 🚢 Operational Cargo & Port Details")
        op1, op2 = st.columns(2)
        vessel = op1.text_input("Feeder / Vessel / Flight", placeholder="e.g. NORMANDIE BRIDGE V.8966", key="pts_rc_vessel")
        ports = op2.text_input("Delivery / Loading Port", placeholder="e.g. BANGKOK / SINGAPORE", key="pts_rc_ports")
        
        bl1, bl2 = st.columns(2)
        obl = bl1.text_input("OB/L / MAWB No.", placeholder="e.g. TYR02536866", key="pts_rc_obl")
        hbl = bl2.text_input("HBL / HAWB No.", placeholder="e.g. HBL-2608-0012", key="pts_rc_hbl")

    with right_col:
        st.markdown("##### 📑 Document & Job References")
        tr_no = st.text_input("Tax Receipt No. (เลขที่ใบกำกับ)", placeholder="Auto (TR...)", key="pts_rc_tr_no")
        
        # Select Linked Job to auto-populate
        sel_job = st.selectbox("Link Master JOB No.", ["— None —"] + list(job_map.keys()), key="pts_rc_job_select")
        if sel_job and sel_job != "— None —":
            job_rec = job_map[sel_job]
            if not vessel:
                vessel = f"{job_rec.get('vessel', '')} {job_rec.get('voyage', '')}".strip()
            if not ports:
                ports = f"{job_rec.get('pol', '')} -> {job_rec.get('pod', '')}".strip()
            if not obl and job_rec.get("mbl_no"):
                obl = job_rec.get("mbl_no")
            if not hbl and job_rec.get("hbl_no"):
                hbl = job_rec.get("hbl_no")

        ref_inv = st.text_input("Reference / Job Ref.", placeholder="e.g. IN07010058", key="pts_rc_ref_inv")
        shipment_no = st.text_input("Shipment No.", value=f"{sel_job}-01" if sel_job != "— None —" else "", key="pts_rc_shipment_no")
        csr_report = st.text_input("CSR Report No.", placeholder="Optional CSR Reference", key="pts_rc_csr")

    st.divider()

    # 3. CHARGE LINES & MULTI-CURRENCY GRID
    st.markdown("#### 📋 Charge Lines (รายการค่าบริการ & สกุลเงินต่างประเทศ)")
    
    # Render line items dynamically
    items_to_save = []
    for i, it in enumerate(st.session_state["pts_rc_items"]):
        with st.container():
            c_code, c_desc, c_pc, c_price, c_curr, c_qty, c_unit, c_exch, c_vat, c_wht, c_del = st.columns([1.2, 2.5, 0.9, 1.1, 0.9, 0.8, 0.8, 1.0, 1.0, 1.0, 0.5])
            
            codes = [""] + list(charge_map.keys())
            curr_code = it.get("charge_code", "")
            code_idx = codes.index(curr_code) if curr_code in codes else 0
            code = c_code.selectbox(f"ID #{i+1}", codes, index=code_idx, key=f"rc_it_code_{i}")
            
            # Default description if selected
            auto_desc = charge_map.get(code, {}).get("description", it.get("description", "")) if code else it.get("description", "")
            desc = c_desc.text_input("Description", value=auto_desc, key=f"rc_it_desc_{i}")
            pc = c_pc.selectbox("P/C", ["PP-E", "CC-E", "PP-I", "CC-I"], index=0 if it.get("pc_type") == "PP-E" else 1, key=f"rc_it_pc_{i}")
            price = c_price.number_input("Price", min_value=0.0, value=float(it.get("price", 0.0)), step=10.0, key=f"rc_it_price_{i}")
            curr = c_curr.selectbox("Curr", CURRENCIES, index=CURRENCIES.index(it.get("curr", "THB")), key=f"rc_it_curr_{i}")
            qty = c_qty.number_input("Qty", min_value=0.01, value=float(it.get("qty", 1.0)), step=1.0, key=f"rc_it_qty_{i}")
            exch = c_exch.number_input("Exch. Bht", min_value=0.00001, value=float(it.get("exch_rate", 35.00000 if curr == "USD" else 1.0)), step=0.00001, format="%.5f", key=f"rc_it_exch_{i}")
            
            v_idx = 0 if it.get("tax_type") in ("VAT 7%", "07") else 1
            vat = c_vat.selectbox("VAT", ["07 (VAT 7%)", "00 (Non-VAT)", "Advance"], index=v_idx, key=f"rc_it_vat_{i}")
            
            w_idx = 1 if it.get("wht_type") in ("WHT 1%", "1") else (2 if it.get("wht_type") in ("WHT 3%", "3") else 0)
            wht = c_wht.selectbox("W/H", ["0 (None)", "1 (1%)", "3 (3%)"], index=w_idx, key=f"rc_it_wht_{i}")
            
            tax_clean = "VAT 7%" if "07" in vat else ("Advance" if "Advance" in vat else "Non-VAT")
            wht_clean = "WHT 1%" if "1" in wht else ("WHT 3%" if "3" in wht else "None")
            
            items_to_save.append({
                "charge_code": code or f"SVC-{i+1}",
                "description": desc or code,
                "pc_type": pc,
                "price": price,
                "unit_price": price,
                "curr": curr,
                "currency": curr,
                "qty": qty,
                "quantity": qty,
                "unit": unit,
                "exch_rate": exch,
                "exchange_rate": exch,
                "tax_type": tax_clean,
                "wht_type": wht_clean,
            })

            if c_del.button("❌", key=f"rc_del_item_{i}"):
                st.session_state["pts_rc_items"].pop(i)
                st.rerun()

    if st.button("➕ Add Charge Line (เพิ่มรายการค่าบริการ)", key="rc_add_item_btn"):
        st.session_state["pts_rc_items"].append({
            "charge_code": "", "description": "", "pc_type": "PP-E", "price": 0.0, "curr": "THB", "qty": 1.0, "unit": "SET", "exch_rate": 1.0, "tax_type": "VAT 7%", "wht_type": "None"
        })
        st.rerun()

    # 4. CALCULATION SUMMARY MATRIX (MATCHING PTS RIGHT PANEL)
    st.divider()
    calc_left, calc_right = st.columns([1.1, 1.2])

    with calc_left:
        st.markdown("##### ⚙️ Adjustments & Pre-payments")
        total_advance = st.number_input("Total Advance (ยอดเงินทดรองจ่าย)", min_value=0.0, value=0.0, step=100.0, key="pts_rc_adv")
        less_vat_sub = st.number_input("Less Vat Sub (หักส่วนลด VAT)", min_value=0.0, value=0.0, step=10.0, key="pts_rc_less_vat")
        plus_wht_diff = st.number_input("Plus WH Tax DIFF (ปรับเศษ WHT)", value=0.0, step=1.0, key="pts_rc_plus_wht")
        diff_default = st.number_input("DIFF (Default +/- ปรับเศษสตางค์)", value=0.0, step=0.01, format="%.2f", key="pts_rc_diff")

    summary = calculate_summary(
        items_to_save,
        total_advance_input=total_advance,
        less_vat_sub=less_vat_sub,
        plus_wht_diff=plus_wht_diff,
        diff_amount=diff_default
    )

    with calc_right:
        st.markdown("##### 📊 Financial Summary Matrix (PTS Calculation)")
        sm_c1, sm_c2 = st.columns(2)
        sm_c1.markdown(f"**Amount No VAT:** {float(summary['amount_no_vat']):,.2f} THB")
        sm_c1.markdown(f"**Amount VAT:** {float(summary['amount_vat']):,.2f} THB")
        sm_c1.markdown(f"**VAT (7%):** {float(summary['total_vat_7']):,.2f} THB")
        sm_c1.markdown(f"**Total Amount:** {float(summary['grand_total']):,.2f} THB")

        sm_c2.markdown(f"**W/H Tax 1%:** {float(summary['wht_1_amount']):,.2f} THB")
        sm_c2.markdown(f"**W/H Tax 3%:** {float(summary['wht_3_amount']):,.2f} THB")
        sm_c2.markdown(f"**Total WHT:** {float(summary['wht_total']):,.2f} THB")
        
        st.markdown(f"""
            <div style="background-color: #cffafe; border: 2px solid #06b6d4; border-radius: 6px; padding: 10px; text-align: right; margin-top: 8px;">
                <span style="font-size: 0.95rem; color: #0e7490; font-weight: 600;">ยอดที่ต้องชำระ (Net Collection Amount):</span><br/>
                <span style="font-size: 1.45rem; font-weight: 800; color: #083344;">{float(summary['net_payable']):,.2f} THB</span>
            </div>
        """, unsafe_allow_html=True)

    st.divider()

    # 5. BOTTOM 4 TABS (COLLECTION PARTS, WHT, OTHER INFO, REF INVOICE)
    t_coll, t_wht, t_other, t_ref = st.tabs([
        "💵 Collection parts. (การรับชำระเงิน)",
        "📑 ภาษีถูกหัก ณ ที่จ่าย (Withholding Tax)",
        "📝 Other Information",
        "🔗 Reference Invoice No."
    ])

    with t_coll:
        st.markdown("##### 💳 Collection Breakdown (ช่องทางการรับเงิน)")
        p_items = []
        for pi, part in enumerate(st.session_state["pts_collection_parts"]):
            col_pay, col_amt, col_chq, col_date, col_bank, col_br, col_act = st.columns([1.2, 1.2, 1.2, 1.2, 2.0, 1.5, 0.5])
            p_method = col_pay.selectbox("Pay by", PAYMENT_CHANNELS, index=PAYMENT_CHANNELS.index(part.get("pay_by", "Transfer")), key=f"part_pay_{pi}")
            default_p_amt = float(summary['net_payable']) if pi == 0 and float(part.get("amount", 0)) == 0 else float(part.get("amount", 0))
            p_amt = col_amt.number_input("Amount", min_value=0.0, value=default_p_amt, format="%.2f", key=f"part_amt_{pi}")
            p_chq = col_chq.text_input("CHQ No. / Ref", value=part.get("chq_no", ""), key=f"part_chq_{pi}")
            p_dt = col_date.date_input("Date", date.today(), key=f"part_dt_{pi}")
            
            b_opts = THAI_BANKS
            b_idx = b_opts.index(part.get("bank")) if part.get("bank") in b_opts else 0
            p_bank = col_bank.selectbox("Bank", b_opts, index=b_idx, key=f"part_bank_{pi}")
            p_br = col_br.text_input("Branch", value=part.get("branch", "HEAD OFFICE"), key=f"part_br_{pi}")
            
            p_items.append({
                "pay_by": p_method,
                "amount": p_amt,
                "chq_no": p_chq,
                "date": p_dt.isoformat(),
                "bank_name": p_bank,
                "branch_name": p_br,
            })
            if col_act.button("❌", key=f"part_del_{pi}"):
                st.session_state["pts_collection_parts"].pop(pi)
                st.rerun()

        if st.button("➕ Add Payment Line (เพิ่มรายการรับชำระ)", key="part_add_btn"):
            st.session_state["pts_collection_parts"].append({
                "pay_by": "Cheque", "amount": 0.0, "chq_no": "", "date": date.today().isoformat(), "bank": "BBL - BANGKOK BANK", "branch": ""
            })
            st.rerun()

    with t_wht:
        st.markdown("##### 📄 Withholding Tax Received Details (หลักฐานภาษีถูกหัก ณ ที่จ่าย)")
        w_c1, w_c2, w_c3 = st.columns(3)
        wht_cert_no = w_c1.text_input("WHT Certificate No. (เลขที่หนังสือรับรอง)", placeholder="e.g. WHT2608005", key="pts_wht_cert_no")
        wht_cert_dt = w_c2.date_input("WHT Date (วันที่หัก)", date.today(), key="pts_wht_cert_dt")
        wht_cert_amt = w_c3.number_input("WHT Amount (ยอดภาษีถูกหัก)", min_value=0.0, value=float(summary["wht_total"]), key="pts_wht_cert_amt")

    with t_other:
        st.markdown("##### 📝 Additional Remarks & Notes")
        remark = st.text_area("Remarks / Note (หมายเหตุการออกเอกสาร)", placeholder="e.g. Payment due within 30 days.", key="pts_rc_remark")

    with t_ref:
        st.markdown("##### 🔗 Multi-Invoice Consolidation (One-to-Many / Many-to-One)")
        open_invs = [inv for inv in list_invoices() or [] if float(inv.get("outstanding") or 0) > 0]
        if open_invs:
            sel_invs = st.multiselect(
                "Select Outstanding Invoices to Settle (เลือกใบแจ้งหนี้เพื่อตัดชำระรวม)",
                [i.get("doc_no") for i in open_invs if i.get("doc_no")],
                key="pts_multi_inv_select"
            )
            if sel_invs:
                st.info(f"Selected {len(sel_invs)} invoice(s) for consolidated settlement: {', '.join(sel_invs)}")
        else:
            st.caption("No open unpaid invoices found for cross-settlement.")

    # 6. ACTION BUTTONS (ADD, EDIT, SAVE, PRINT)
    st.divider()
    btn_save, btn_reset = st.columns([1, 1])
    if btn_save.button("💾 Save & Issue Receipt & Tax Receipt", type="primary", use_container_width=True, key="pts_rc_submit_btn"):
        if not sel_cid:
            st.error("Please select a customer.")
            return
        if not items_to_save:
            st.error("Please add at least one charge line.")
            return
        try:
            created_doc = create_invoice({
                "doc_no": rc_no_input.strip() or None,
                "doc_type": "RC",
                "customer_id": sel_cid,
                "customer_name": selected_cust.get("company_name"),
                "customer_address": cust_addr.strip(),
                "customer_tax_id": default_tax_id,
                "service_type": rc_service,
                "feeder_vessel": vessel,
                "pol": ports.split("->")[0].strip() if "->" in ports else ports,
                "pod": ports.split("->")[1].strip() if "->" in ports else "",
                "delivery_port": ports,
                "mbl_mawb_no": obl,
                "hbl_hawb_no": hbl,
                "job_no": sel_job if sel_job != "— None —" else "",
                "master_job_no": sel_job if sel_job != "— None —" else "",
                "shipment_no": shipment_no,
                "ref_doc_no": ref_inv,
                "tax_receipt_no": tr_no or None,
                "csr_report_no": csr_report,
                "issue_date": rc_date.isoformat(),
                "due_date": rc_date.isoformat(),
                "currency": "THB",
                "remark": remark.strip(),
                "total_advance": total_advance,
                "less_vat_sub": less_vat_sub,
                "plus_wht_diff": plus_wht_diff,
                "diff_amount": diff_default,
                "status": "ACTIVE",
                "created_by": user.get("username", "system"),
                "payments": p_items
            }, items_to_save)
            
            redirect_to_tab("finance_v2_active_tab", "📑 Receipt & Invoice Register (ทะเบียนเอกสาร)")
            st.session_state["fin_v2_doc_actions_select"] = created_doc
            st.session_state["finance_last_doc"] = created_doc
            st.session_state.pop("pts_rc_items", None)
            st.session_state.pop("pts_collection_parts", None)
            st.success(f"🎉 Receipt & Tax Receipt {created_doc} created and posted successfully!")
            st.rerun()
        except Exception as exc:
            st.error(f"Error creating Receipt: {exc}")

    if btn_reset.button("🔄 Reset Form", use_container_width=True, key="pts_rc_reset_btn"):
        st.session_state.pop("pts_rc_items", None)
        st.session_state.pop("pts_collection_parts", None)
        redirect_to_tab("finance_v2_active_tab", "📑 Receipt & Invoice Register (ทะเบียนเอกสาร)")
        st.rerun()


def render() -> None:
    page_header("billing", status_text="Online")
    user = st.session_state.get("user", {})
    can_edit = can_write(str(user.get("role", "")).lower(), "billing")
    invoices = list_invoices() or []

    tab_opts = ["📑 Receipt & Invoice Register (ทะเบียนเอกสาร)", "➕ Create Receipt & Tax Receipt (ออกใบเสร็จ)"]
    get_active_tab("finance_v2_active_tab", tab_opts)

    active_tab = st.radio(
        "Finance Navigation",
        tab_opts,
        horizontal=True,
        key="finance_v2_active_tab",
        label_visibility="collapsed"
    )

    if active_tab == tab_opts[0]:
        st.markdown("#### 🔍 Filter & Search Financial Documents")
        f1, f2 = st.columns([1, 2])
        doc_filter = f1.selectbox("Document Type", ["ALL"] + list(DOC_TYPES.keys()), format_func=lambda x: "All Types" if x == "ALL" else DOC_TYPES[x], key="fin_v2_filter_type")
        q = f2.text_input("Search", placeholder="Receipt No., Customer Name, Job No., B/L No.", key="fin_v2_search_q").strip().lower()

        filtered = invoices
        if doc_filter != "ALL":
            filtered = [r for r in filtered if r.get("doc_type") == doc_filter]
        if q:
            filtered = [r for r in filtered if q in str(r).lower()]

        # Metrics overview
        total_b = sum(float(r.get("total_amount") or r.get("grand_total") or 0) for r in filtered if str(r.get("status", "")).upper() != "CANCELLED")
        total_o = sum(float(r.get("outstanding") or 0) for r in filtered if str(r.get("status", "")).upper() != "CANCELLED")
        total_p = max(total_b - total_o, 0.0)

        m1, m2, m3 = st.columns(3)
        m1.metric("Total Billed (ยอดรวม)", f"{total_b:,.2f} THB")
        m2.metric("Total Collected (ยอดรับชำระ)", f"{total_p:,.2f} THB")
        m3.metric("Outstanding Balance (คงค้าง)", f"{total_o:,.2f} THB")

        # Table Display
        display_data = [{
            "Doc No.": r.get("doc_no"),
            "Type": r.get("doc_type"),
            "Customer": r.get("customer_name"),
            "Job No.": r.get("job_no") or r.get("master_job_no"),
            "Date": r.get("issue_date"),
            "Total Amount": f"{float(r.get('grand_total', r.get('total_amount', 0))):,.2f}",
            "Outstanding": f"{float(r.get('outstanding', 0)):,.2f}",
            "Status": r.get("status"),
        } for r in filtered]
        st.dataframe(pd.DataFrame(display_data), hide_index=True, use_container_width=True)

        if filtered:
            choices = [r.get("doc_no") for r in filtered if r.get("doc_no")]
            sel_idx = 0
            cur_sel = st.session_state.get("fin_v2_doc_actions_select")
            if cur_sel in choices:
                sel_idx = choices.index(cur_sel)
            sel = st.selectbox("Select Document for Actions / PDF", choices, index=sel_idx, key="fin_v2_doc_actions_select")
            if sel:
                rec = next(r for r in filtered if r.get("doc_no") == sel)
                st.caption(f"Selected: **{sel}** · Customer: {rec.get('customer_name', '—')} · Status: {rec.get('status')}")
                act1, act2, act3 = st.columns([1, 1, 1.2])
                with act1:
                    _pdf(sel)
                with act2:
                    if can_edit and st.button("📋 Duplicate Document", key=f"dup_{sel}", use_container_width=True):
                        new_no = duplicate_invoice(sel, user)
                        st.success(f"Duplicated as {new_no}")
                        st.rerun()
                with act3:
                    if can_edit:
                        if str(rec.get("status", "")).upper() != "CANCELLED":
                            if st.button("🔄 Rollback / ยกเลิก", key=f"fin_v2_cancel_{sel}", use_container_width=True, type="secondary"):
                                try:
                                    from managers.invoice_manager import cancel_invoice_document
                                    cancel_invoice_document(sel, user)
                                    st.success(f"🎉 ยกเลิก {sel} และปลดล็อกรายการ AR สำเร็จ!")
                                    st.rerun()
                                except Exception as exc:
                                    st.error(f"Rollback failed: {exc}")
                        else:
                            st.caption("⚠️ เอกสารนี้ถูกยกเลิกแล้ว (CANCELLED)")

    elif active_tab == tab_opts[1]:
        if can_edit:
            _render_pts_receipt_form(user)
        else:
            st.warning("You do not have write permissions to create billing documents.")

