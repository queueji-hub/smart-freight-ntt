"""Job Profitability & Unified AP/AR Matrix Workspace.

Provides ERP-grade Single Source of Truth for:
- Unified Side-by-Side AP (Cost/Payables) and AR (Revenue/Billing) Ledger
- Live Accrual P&L Dashboard (Cost, Revenue, Advance, VAT, WHT, Profit Margin)
- Pull AP to AR with customizable markup and selling descriptions
- Batch AP Payment Voucher & Advance Request generation
- Batch AR Customer Invoice generation
- Comprehensive Document Audit Trail & Line Item Traceability
"""
from __future__ import annotations

import os
from datetime import date, datetime
from typing import Any, Dict, List, Optional

import pandas as pd
import streamlit as st

from managers.auth_manager import can_write
from managers.profit_manager import (
    AP_CATEGORIES,
    AR_CATEGORIES,
    TAX_TYPES,
    WHT_TYPES,
    add_cost_line,
    compute_line_tax_and_net,
    create_batch_invoice_from_ar,
    create_batch_payment_voucher,
    create_profit_sheet,
    delete_cost_line,
    get_cost_lines,
    get_job_document_audit,
    get_profit_summary,
    get_unified_job_ledger,
    list_profit_sheets,
    lock_job_financials,
    pull_ap_to_ar,
    unlock_job_financials,
    update_cost_line,
    update_signoff,
)
from managers.shipment_manager import get_shipment, list_shipments
from ui.design_system import page_header, section


def _s(v: Any, fb: str = "—") -> str:
    if v is None:
        return fb
    x = str(v).strip()
    return fb if not x or x.lower() in {"none", "nan", "nat"} else x


def _money(n: Any, curr: str = "฿") -> str:
    try:
        val = float(n or 0)
        return f"{curr} {val:,.2f}"
    except (ValueError, TypeError):
        return f"{curr} 0.00"


def _render_pdf_profit_sheet(shipment_id: int):
    try:
        from pdf.profit_pdf import generate_profit_pdf
        pdf_path = generate_profit_pdf(shipment_id)
        if pdf_path and os.path.exists(pdf_path):
            with open(pdf_path, "rb") as f:
                st.session_state[f"profit_pdf_bytes_{shipment_id}"] = f.read()
            st.session_state[f"profit_pdf_name_{shipment_id}"] = os.path.basename(pdf_path)
            st.toast("✅ Profit Sheet PDF generated.", icon="📄")
    except Exception as exc:
        st.error(f"Failed to generate Profit Sheet PDF: {exc}")


def _render_pdf_payment_voucher(voucher: Dict[str, Any], items: List[Dict[str, Any]]):
    try:
        from pdf.payment_voucher_pdf import generate_payment_voucher_pdf
        pdf_path = generate_payment_voucher_pdf(voucher, items)
        if pdf_path and os.path.exists(pdf_path):
            v_no = voucher.get("voucher_no", "PV")
            with open(pdf_path, "rb") as f:
                st.session_state[f"voucher_pdf_bytes_{v_no}"] = f.read()
            st.session_state[f"voucher_pdf_name_{v_no}"] = os.path.basename(pdf_path)
            st.toast(f"✅ Payment Voucher PDF {v_no} ready.", icon="📄")
    except Exception as exc:
        st.error(f"Failed to generate Voucher PDF: {exc}")


def render():
    user = st.session_state.get("user", {})
    role = str(user.get("role", "")).lower()
    can_edit = can_write(role, "shipment") or can_write(role, "billing")
    tenant_id = user.get("tenant_id", "default")

    section("Job Profitability & Unified AP / AR Ledger (ตารางรวมต้นทุน-รายได้ และกำไร)")

    # 1. Job Selector
    ships = list_shipments(limit=200) or []
    if not ships:
        st.info("No active freight jobs available. Please create a Job in Booking / Job Control first.")
        return

    job_options = {f"🚢 {s['job_no']} — {_s(s.get('customer_name'))} ({_s(s.get('pol'))} ➔ {_s(s.get('pod'))})": s for s in ships}
    
    # Check if pre-selected via session state
    pre_sel = st.session_state.get("job_control_selector")
    default_idx = 0
    if pre_sel:
        for idx, (lbl, s_obj) in enumerate(job_options.items()):
            if s_obj.get("job_no") == pre_sel or str(s_obj.get("id")) == str(pre_sel):
                default_idx = idx
                break

    sel_label = st.selectbox("Select Target Job / Shipment Operation *", list(job_options.keys()), index=default_idx, key="profit_unified_job_sel")
    ship = job_options[sel_label]
    shipment_id = ship["id"]
    job_no = ship.get("job_no")
    is_fin_locked = bool(ship.get("financial_locked"))

    # 2. Fetch Ledger Data
    ledger = get_unified_job_ledger(shipment_id)
    summary = ledger["summary"]
    matrix_rows = ledger["matrix_rows"]

    # 3. Accrual P&L Summary Cards
    gp = summary["gross_profit"]
    margin = summary["margin_pct"]
    yield_color = "🟢" if gp >= 0 else "🔴"

    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    with kpi1:
        st.metric(
            "💸 Total AP (Cost / ค่าใช้จ่าย)",
            _money(summary["total_ap_amount"]),
            help=f"Service Cost: {_money(summary['total_ap_amount'] - summary['total_ap_advance'])} | Advance: {_money(summary['total_ap_advance'])} | VAT: {_money(summary['total_ap_vat'])} | WHT: {_money(summary['total_ap_wht'])} | Net Payable: {_money(summary['total_ap_net'])}"
        )
        st.caption(f"Status: {summary['ap_counts']['unpaid']} Unpaid · {summary['ap_counts']['requested']} Requested · {summary['ap_counts']['paid']} Paid")

    with kpi2:
        st.metric(
            "💰 Total AR (Revenue / รายได้)",
            _money(summary["total_ar_amount"]),
            help=f"Service Rev: {_money(summary['total_ar_amount'] - summary['total_ar_advance'])} | Advance: {_money(summary['total_ar_advance'])} | VAT: {_money(summary['total_ar_vat'])} | WHT: {_money(summary['total_ar_wht'])} | Net Receivable: {_money(summary['total_ar_net'])}"
        )
        st.caption(f"Status: {summary['ar_counts']['unbilled']} Unbilled · {summary['ar_counts']['invoiced']} Invoiced · {summary['ar_counts']['collected']} Collected")

    with kpi3:
        st.metric(
            f"{yield_color} Gross Profit (กำไรขั้นต้น)",
            _money(gp),
            delta=f"{margin:.1f}% Margin Ratio",
        )
        st.caption("Net Accrual Margin = Revenue (AR) - Cost (AP)")

    with kpi4:
        st.metric(
            "🧾 Net Cashflow Expected",
            _money(summary["total_ar_net"] - summary["total_ap_net"]),
            help="Total AR Net Receivable minus Total AP Net Payable"
        )
        lock_status = "🔒 Financial Locked" if is_fin_locked else "🔓 Financial Open"
        st.caption(lock_status)

    # 4. Workspace Tabs
    tab_matrix, tab_audit, tab_signoffs = st.tabs([
        "📊 Unified AP / AR Ledger & Cost Reconciliation",
        "📜 Document Ledger & Audit Traceability (ประวัติเอกสารย้อนหลัง)",
        "📋 P&L Sign-off & Official Profit Sheets"
    ])

    with tab_matrix:
        # Action Toolbar
        act_col1, act_col2, act_col3 = st.columns([4, 4, 3])
        with act_col1:
            st.markdown("##### ⚙️ Financial Operations Toolbar")
        with act_col2:
            st.write("")
        with act_col3:
            if st.button("📄 Export Profit Sheet PDF", key=f"pdf_ps_{shipment_id}", width="stretch", type="primary"):
                _render_pdf_profit_sheet(shipment_id)
            ps_bytes = st.session_state.get(f"profit_pdf_bytes_{shipment_id}")
            if ps_bytes:
                st.download_button(
                    "⬇️ Download Profit Sheet PDF",
                    data=ps_bytes,
                    file_name=st.session_state.get(f"profit_pdf_name_{shipment_id}", f"Profit_{job_no}.pdf"),
                    mime="application/pdf",
                    key=f"dl_ps_pdf_{shipment_id}",
                    width="stretch"
                )

        # Batch Action Expanders
        if can_edit and not is_fin_locked:
            b_exp1, b_exp2, b_exp3 = st.columns(3)
            with b_exp1:
                with st.expander("📥 Pull AP ➔ AR (ดึงรายการต้นทุนไปเป็นรายได้)", expanded=False):
                    ap_available = [r for r in ledger["ap_lines"]]
                    if ap_available:
                        ap_pull_opts = {f"#{r['id']} - {r.get('description')} ({_money(r.get('amount_thb'))})": r["id"] for r in ap_available}
                        selected_pull_ids = st.multiselect("Select AP Lines to Pull into AR *", options=list(ap_pull_opts.keys()), key=f"pull_ap_sel_{shipment_id}")
                        markup = st.number_input("Markup % (กำไรส่วนเพิ่ม %)", min_value=0.0, value=15.0, step=5.0, key=f"pull_markup_{shipment_id}")
                        cust_name_target = st.text_input("Customer Name / Bill To", value=_s(ship.get("customer_name")), key=f"pull_cust_{shipment_id}")
                        
                        if st.button("🚀 Pull & Create AR Revenue Lines", type="primary", key=f"btn_pull_{shipment_id}", width="stretch"):
                            if not selected_pull_ids:
                                st.error("Please select at least one AP line.")
                            else:
                                target_ids = [ap_pull_opts[k] for k in selected_pull_ids]
                                created = pull_ap_to_ar(shipment_id, target_ids, markup_pct=markup, target_customer=cust_name_target, user=user)
                                st.success(f"🎉 Successfully pulled {len(created)} lines to AR.")
                                st.rerun()
                    else:
                        st.info("No AP cost lines recorded yet to pull.")

            with b_exp2:
                with st.expander("⚡ ตั้งเบิกจ่าย AP เป็นชุด (Batch Payment Voucher)", expanded=False):
                    unpaid_ap = [r for r in ledger["ap_lines"] if str(r.get("payout_status")).upper() != "PAID"]
                    if unpaid_ap:
                        v_opts = {f"#{r['id']} - {r.get('description')} [{r.get('supplier','—')}] ({_money(r.get('amount_thb'))})": r["id"] for r in unpaid_ap}
                        sel_v_ids = st.multiselect("Select AP Lines to Group into Voucher *", options=list(v_opts.keys()), key=f"pv_batch_sel_{shipment_id}")
                        v_type = st.selectbox("Voucher Type", ["PAYMENT_VOUCHER (ใบสำคัญจ่าย)", "ADVANCE_REQUEST (ใบขอเบิกเงินทดรองจ่าย)"], key=f"pv_type_{shipment_id}")
                        payee_default = unpaid_ap[0].get("supplier") if unpaid_ap else ""
                        payee = st.text_input("Payee / Vendor Name (ผู้รับเงิน) *", value=payee_default, key=f"pv_payee_{shipment_id}")
                        due = st.date_input("Due Date (วันครบกำหนดจ่าย)", value=date.today(), key=f"pv_due_{shipment_id}")

                        if st.button("⚡ Generate AP Payment Voucher", type="primary", key=f"btn_gen_pv_{shipment_id}", width="stretch"):
                            if not sel_v_ids:
                                st.error("Please select at least one AP cost line.")
                            elif not payee.strip():
                                st.error("Payee name is required.")
                            else:
                                t_ids = [v_opts[k] for k in sel_v_ids]
                                v_no = create_batch_payment_voucher(shipment_id, t_ids, payee.strip(), voucher_type="ADVANCE" if "ADVANCE" in v_type else "PAYMENT_VOUCHER", due_date=due.isoformat(), user=user)
                                st.success(f"🎉 Created Payment Voucher {v_no} successfully.")
                                st.rerun()
                    else:
                        st.info("All AP lines are paid or no AP lines exist.")

            with b_exp3:
                with st.expander("⚡ ออกใบแจ้งหนี้ AR เป็นชุด (Batch Invoice)", expanded=False):
                    unbilled_ar = [r for r in ledger["ar_lines"] if str(r.get("billing_status")).upper() not in ["INVOICED", "COLLECTED", "PAID"]]
                    if unbilled_ar:
                        ar_opts = {f"#{r['id']} - {r.get('description')} ({_money(r.get('amount_thb'))})": r["id"] for r in unbilled_ar}
                        sel_ar_ids = st.multiselect("Select AR Lines to Group into Invoice *", options=list(ar_opts.keys()), key=f"inv_batch_sel_{shipment_id}")
                        
                        if st.button("⚡ Generate Customer Invoice", type="primary", key=f"btn_gen_inv_{shipment_id}", width="stretch"):
                            if not sel_ar_ids:
                                st.error("Please select at least one AR revenue line.")
                            else:
                                t_ids = [ar_opts[k] for k in sel_ar_ids]
                                inv_no = create_batch_invoice_from_ar(shipment_id, t_ids, user=user)
                                st.success(f"🎉 Created Invoice {inv_no} successfully.")
                                st.rerun()
                    else:
                        st.info("All AR lines have already been invoiced or no AR lines exist.")

        # Quick Add Cost & Revenue Drawers
        if can_edit and not is_fin_locked:
            add_c1, add_c2 = st.columns(2)
            with add_c1:
                with st.expander("➕ เพิ่มรายการต้นทุน AP (Add Operational Cost)", expanded=len(ledger["ap_lines"]) == 0):
                    with st.form(f"quick_add_ap_form_{shipment_id}", clear_on_submit=True):
                        cat_ap = st.selectbox("AP Category *", AP_CATEGORIES, key=f"q_ap_cat_{shipment_id}")
                        desc_ap = st.text_input("AP Description / Charge Name *", placeholder="e.g. Ocean Freight, THC, Customs Clearance...", key=f"q_ap_desc_{shipment_id}")
                        supp_ap = st.text_input("Supplier / Vendor / Payee (จ่ายให้ใคร)", value=_s(ship.get("carrier"), ""), key=f"q_ap_sup_{shipment_id}")
                        
                        f1, f2, f3 = st.columns(3)
                        qty_ap = f1.number_input("Qty", min_value=0.01, value=1.0, step=1.0, key=f"q_ap_qty_{shipment_id}")
                        unit_ap = f2.selectbox("Unit", ["BL", "CTR", "CBM", "TRIP", "SHPT", "LOT", "SET", "KG"], index=0, key=f"q_ap_unit_{shipment_id}")
                        prc_ap = f3.number_input("Unit Price Rate", min_value=0.0, value=0.0, step=500.0, key=f"q_ap_prc_{shipment_id}")

                        t1, t2, t3 = st.columns(3)
                        curr_ap = t1.selectbox("Currency", ["THB", "USD", "EUR", "CNY", "JPY", "SGD"], index=0, key=f"q_ap_curr_{shipment_id}")
                        ex_ap = t2.number_input("Ex.Rate to THB", min_value=0.001, value=1.0 if curr_ap == "THB" else 35.5, step=0.1, key=f"q_ap_ex_{shipment_id}")
                        tax_ap = t3.selectbox("Tax / VAT Type", TAX_TYPES, index=0, key=f"q_ap_tax_{shipment_id}")
                        
                        w1, w2 = st.columns(2)
                        wht_ap = w1.selectbox("Withholding Tax (WHT)", WHT_TYPES, index=0, key=f"q_ap_wht_{shipment_id}")
                        vinv_ap = w2.text_input("Vendor Invoice / Ref No.", placeholder="e.g. ONE-12345 / PAT-8899", key=f"q_ap_vinv_{shipment_id}")

                        # Preview calculations live
                        prev = compute_line_tax_and_net(qty_ap, prc_ap, tax_ap, wht_ap, curr_ap, ex_ap)
                        st.info(f"📊 **Preview Amount:** {prev['amount']:,.2f} {curr_ap} ({prev['amount_thb']:,.2f} THB) | VAT: {prev['vat_amount']:,.2f} | WHT: {prev['wht_amount']:,.2f} | **Net Payable: {prev['net_amount']:,.2f} {curr_ap}**")

                        if st.form_submit_button("💾 Save AP Cost Line", type="primary", width="stretch"):
                            if not desc_ap.strip():
                                st.error("Description is required.")
                            else:
                                add_cost_line({
                                    "shipment_id": shipment_id,
                                    "cost_type": "AP",
                                    "category": cat_ap,
                                    "description": desc_ap.strip(),
                                    "supplier": supp_ap.strip() or None,
                                    "quantity": qty_ap,
                                    "unit": unit_ap,
                                    "unit_price": prc_ap,
                                    "currency": curr_ap,
                                    "exchange_rate": ex_ap,
                                    "tax_type": tax_ap,
                                    "wht_type": wht_ap,
                                    "vendor_invoice_no": vinv_ap.strip() or None,
                                    "created_by": user.get("username", "operation"),
                                })
                                st.success("AP Cost Line added.")
                                st.rerun()

            with add_c2:
                with st.expander("➕ เพิ่มรายการรายได้ AR (Add Customer Revenue)", expanded=len(ledger["ar_lines"]) == 0):
                    with st.form(f"quick_add_ar_form_{shipment_id}", clear_on_submit=True):
                        cat_ar = st.selectbox("AR Category *", AR_CATEGORIES, key=f"q_ar_cat_{shipment_id}")
                        desc_ar = st.text_input("AR Description / Charge Name *", placeholder="e.g. Ocean Freight & THC, Documentation...", key=f"q_ar_desc_{shipment_id}")
                        cust_ar = st.text_input("Customer / Bill To", value=_s(ship.get("customer_name"), ""), key=f"q_ar_cust_{shipment_id}")
                        
                        f1, f2, f3 = st.columns(3)
                        qty_ar = f1.number_input("Qty", min_value=0.01, value=1.0, step=1.0, key=f"q_ar_qty_{shipment_id}")
                        unit_ar = f2.selectbox("Unit", ["BL", "CTR", "CBM", "TRIP", "SHPT", "LOT", "SET", "KG"], index=0, key=f"q_ar_unit_{shipment_id}")
                        prc_ar = f3.number_input("Unit Price Selling Rate", min_value=0.0, value=0.0, step=500.0, key=f"q_ar_prc_{shipment_id}")

                        t1, t2, t3 = st.columns(3)
                        curr_ar = t1.selectbox("Currency", ["THB", "USD", "EUR", "CNY", "JPY", "SGD"], index=0, key=f"q_ar_curr_{shipment_id}")
                        ex_ar = t2.number_input("Ex.Rate to THB", min_value=0.001, value=1.0 if curr_ar == "THB" else 35.5, step=0.1, key=f"q_ar_ex_{shipment_id}")
                        tax_ar = t3.selectbox("Tax / VAT Type", TAX_TYPES, index=0, key=f"q_ar_tax_{shipment_id}")
                        
                        w1, _ = st.columns(2)
                        wht_ar = w1.selectbox("Withholding Tax (WHT)", WHT_TYPES, index=0, key=f"q_ar_wht_{shipment_id}")

                        # Preview calculations live
                        prev_ar = compute_line_tax_and_net(qty_ar, prc_ar, tax_ar, wht_ar, curr_ar, ex_ar)
                        st.info(f"📊 **Preview Revenue:** {prev_ar['amount']:,.2f} {curr_ar} ({prev_ar['amount_thb']:,.2f} THB) | VAT: {prev_ar['vat_amount']:,.2f} | WHT: {prev_ar['wht_amount']:,.2f} | **Net Receivable: {prev_ar['net_amount']:,.2f} {curr_ar}**")

                        if st.form_submit_button("💾 Save AR Revenue Line", type="primary", width="stretch"):
                            if not desc_ar.strip():
                                st.error("Description is required.")
                            else:
                                add_cost_line({
                                    "shipment_id": shipment_id,
                                    "cost_type": "AR",
                                    "category": cat_ar,
                                    "description": desc_ar.strip(),
                                    "supplier": cust_ar.strip() or None,
                                    "quantity": qty_ar,
                                    "unit": unit_ar,
                                    "unit_price": prc_ar,
                                    "currency": curr_ar,
                                    "exchange_rate": ex_ar,
                                    "tax_type": tax_ar,
                                    "wht_type": wht_ar,
                                    "created_by": user.get("username", "operation"),
                                })
                                st.success("AR Revenue Line added.")
                                st.rerun()

        # Unified Side-by-Side AP/AR Ledger Matrix Table
        section("Unified Side-by-Side AP / AR Ledger Matrix (ตารางรวม AP/AR และกำไรต่อรายการ)")

        if not matrix_rows:
            st.info("No cost or revenue lines recorded for this Job. Use the quick add forms above to start building the ledger.")
        else:
            table_data = []
            for r in matrix_rows:
                table_data.append({
                    "No.": r["line_no"],
                    # AP Side
                    "AP Description (ต้นทุน)": r["ap_description"],
                    "Payee / Vendor": r["ap_supplier"],
                    "AP Rate": f"{r['ap_unit_price']:,.2f} {r['ap_currency']}" if r["ap_id"] else "—",
                    "AP Qty": f"{r['ap_quantity']:g} {r['ap_unit']}" if r["ap_id"] else "—",
                    "AP Amount (฿)": f"{r['ap_amount_thb']:,.2f}" if r["ap_id"] else "—",
                    "AP Tax/WHT": f"{r['ap_tax_type']} / {r['ap_wht_type']}" if r["ap_id"] else "—",
                    "AP Status": f"{r['ap_payout_status']} ({r['ap_voucher_no']})" if r["ap_id"] else "—",
                    # Bridge
                    "Link": "➔" if r["is_matched"] else ("✦ Pure AR" if not r["ap_id"] else "✦ Unbilled AP"),
                    # AR Side
                    "AR Description (เรียกเก็บ)": r["ar_description"],
                    "Customer": r["ar_customer"],
                    "AR Rate": f"{r['ar_unit_price']:,.2f} {r['ar_currency']}" if r["ar_id"] else "—",
                    "AR Qty": f"{r['ar_quantity']:g} {r['ar_unit']}" if r["ar_id"] else "—",
                    "AR Amount (฿)": f"{r['ar_amount_thb']:,.2f}" if r["ar_id"] else "—",
                    "AR Tax/WHT": f"{r['ar_tax_type']} / {r['ar_wht_type']}" if r["ar_id"] else "—",
                    "AR Status": f"{r['ar_billing_status']} ({r['ar_invoice_no']})" if r["ar_id"] else "—",
                    # Profit
                    "Line Profit (฿)": f"{r['line_profit_thb']:,.2f}",
                    "Margin %": f"{r['line_margin_pct']:.1f}%",
                })

            df_matrix = pd.DataFrame(table_data)
            st.dataframe(df_matrix, hide_index=True, width="stretch")

            # Prune / Delete Line segment
            if can_edit and not is_fin_locked:
                with st.expander("🗑️ Delete / Prune Ledger Line", expanded=False):
                    del_opts = []
                    for ap in ledger["ap_lines"]:
                        del_opts.append((ap["id"], f"AP #{ap['id']} - {ap.get('description')} ({_money(ap.get('amount_thb'))})"))
                    for ar in ledger["ar_lines"]:
                        del_opts.append((ar["id"], f"AR #{ar['id']} - {ar.get('description')} ({_money(ar.get('amount_thb'))})"))

                    if del_opts:
                        d_col1, d_col2 = st.columns([3, 1])
                        chosen_del = d_col1.selectbox("Select Line to Remove", del_opts, format_func=lambda x: x[1], key=f"del_line_sel_{shipment_id}")
                        if d_col2.button("🗑️ Delete Line", type="secondary", key=f"del_btn_{shipment_id}", width="stretch"):
                            delete_cost_line(chosen_del[0])
                            st.success("Line removed.")
                            st.rerun()

    with tab_audit:
        section("Document Ledger & Audit Traceability (ประวัติเอกสารย้อนหลังและรายการในแต่ละใบ)")
        doc_audit = get_job_document_audit(shipment_id)

        vouchers = doc_audit["payment_vouchers"]
        invoices = doc_audit["invoices"]

        doc_c1, doc_c2 = st.columns(2)

        with doc_c1:
            st.markdown(f"#### 📑 AP Payment Vouchers & Advance ({len(vouchers)} Documents)")
            if not vouchers:
                st.info("No AP Payment Vouchers generated yet for this Job.")
            else:
                for v in vouchers:
                    v_no = v.get("voucher_no")
                    v_type_label = "ใบขอเบิกเงินทดรองจ่าย (Advance)" if "ADVANCE" in str(v.get("voucher_type")).upper() else "ใบสำคัญจ่าย (Payment Voucher)"
                    with st.expander(f"📄 {v_no} — {v.get('payee_name','—')} | {_money(v.get('total'))} {v.get('currency','THB')} [{v.get('status','REQUESTED')}]", expanded=True):
                        st.write(f"**Voucher Type:** {v_type_label}")
                        st.write(f"**Due Date:** {_s(v.get('due_date'))} | **Status:** {v.get('status')}")
                        
                        v_items = v.get("items", [])
                        if v_items:
                            st.write("**Itemized Charges (รายการที่รวมอยู่ในใบนี้):**")
                            st.dataframe(pd.DataFrame([{
                                "No.": idx,
                                "Description": it.get("description"),
                                "Qty": f"{it.get('quantity', 1):g} {it.get('unit', 'UNIT')}",
                                "Rate": f"{float(it.get('unit_price',0)):,.2f}",
                                "Amount": f"{float(it.get('amount',0)):,.2f}",
                                "Tax Type": it.get("tax_type"),
                                "VAT": f"{float(it.get('vat_amount',0)):,.2f}",
                                "WHT": f"{float(it.get('wht_amount',0)):,.2f}",
                                "Net Payable": f"{float(it.get('net_amount',0)):,.2f}",
                            } for idx, it in enumerate(v_items, start=1)]), hide_index=True, width="stretch")
                        
                        pv_col1, pv_col2 = st.columns(2)
                        with pv_col1:
                            if st.button(f"📄 Export PDF ({v_no})", key=f"exp_pv_btn_{v_no}", width="stretch"):
                                _render_pdf_payment_voucher(v, v_items)
                        with pv_col2:
                            v_bytes = st.session_state.get(f"voucher_pdf_bytes_{v_no}")
                            if v_bytes:
                                st.download_button(
                                    f"⬇️ Download {v_no}.pdf",
                                    data=v_bytes,
                                    file_name=f"{v_no}.pdf",
                                    mime="application/pdf",
                                    key=f"dl_pv_btn_{v_no}",
                                    width="stretch",
                                )

        with doc_c2:
            st.markdown(f"#### 🧾 AR Customer Invoices ({len(invoices)} Documents)")
            if not invoices:
                st.info("No Customer Invoices generated yet for this Job.")
            else:
                for inv in invoices:
                    doc_no = inv.get("doc_no")
                    with st.expander(f"📄 {doc_no} — {inv.get('customer_name','—')} | {_money(inv.get('grand_total'))} [{inv.get('status','ISSUED')}]", expanded=True):
                        st.write(f"**Customer:** {inv.get('customer_name')}")
                        st.write(f"**Issue Date:** {_s(inv.get('issue_date'))} | **Due Date:** {_s(inv.get('due_date'))} | **Status:** {inv.get('status')}")
                        
                        inv_items = inv.get("items", [])
                        if inv_items:
                            st.write("**Itemized Charges (รายการที่รวมอยู่ในใบแจ้งหนี้นี้):**")
                            st.dataframe(pd.DataFrame([{
                                "No.": idx,
                                "Description": it.get("description"),
                                "Qty": f"{it.get('quantity', 1):g} {it.get('unit', 'UNIT')}",
                                "Rate": f"{float(it.get('unit_price',0)):,.2f}",
                                "Amount": f"{float(it.get('amount',0)):,.2f}",
                                "Tax Type": it.get("tax_type"),
                                "VAT": f"{float(it.get('vat_amount',0)):,.2f}",
                                "WHT": f"{float(it.get('wht_amount',0)):,.2f}",
                                "Net Receivable": f"{float(it.get('net_amount',0)):,.2f}",
                            } for idx, it in enumerate(inv_items, start=1)]), hide_index=True, width="stretch")

                        if st.button(f"📂 Open in Billing Workspace ({doc_no})", key=f"goto_inv_{doc_no}", width="stretch"):
                            st.session_state["current_navigation"] = "billing"
                            st.query_params["page"] = "billing"
                            st.rerun()

    with tab_signoffs:
        section("Official Job Profitability Sheets & Sign-offs (การลงนามอนุมัติ P&L)")
        sheets = list_profit_sheets(shipment_id) or []

        if can_edit:
            if st.button("🚀 Create Official Job Profitability Sheet Record", type="primary", key=f"create_ps_rec_{shipment_id}", width="stretch"):
                res = create_profit_sheet(shipment_id, prepared_by=user.get("username", "accountant"))
                st.success(f"🎉 Created Profit Sheet Record {res.get('sheet_no')}.")
                st.rerun()

        if not sheets:
            st.info("No signed profit sheet profiles archived yet.")
        else:
            for sh in sheets:
                with st.expander(f"📑 {sh['sheet_no']} | Revenue: {_money(sh.get('total_ar'))} | Cost: {_money(sh.get('total_ap'))} | Net Profit: {_money(sh.get('net_profit'))} ({sh.get('profit_margin',0):.1f}%)"):
                    s_c1, s_c2, s_c3 = st.columns(3)
                    s_c1.write(f"**Prepared By:** {_s(sh.get('prepared_by'))}")
                    s_c2.write(f"**Reviewed By:** {_s(sh.get('reviewed_by'))} ({_s(sh.get('reviewed_at'))})")
                    s_c3.write(f"**Approved By:** {_s(sh.get('approved_by'))} ({_s(sh.get('approved_at'))})")

                    if role in ["admin", "accounting", "manager"] and not sh.get("approved_by"):
                        sign_btn1, sign_btn2 = st.columns(2)
                        with sign_btn1:
                            if st.button(f"✍️ Review Sign-off ({sh['sheet_no']})", key=f"rev_{sh['id']}", width="stretch"):
                                update_signoff(sh["id"], "review", user.get("username", "manager"))
                                st.success("Reviewed.")
                                st.rerun()
                        with sign_btn2:
                            if st.button(f"✅ Executive Approval Sign-off ({sh['sheet_no']})", key=f"app_{sh['id']}", width="stretch", type="primary"):
                                update_signoff(sh["id"], "approve", user.get("username", "director"))
                                lock_job_financials(shipment_id, user)
                                st.success("Approved and Job Financials Locked.")
                                st.rerun()