"""Job Profitability & Unified AP/AR Matrix Workspace.

Provides ERP-grade Single Source of Truth for:
- Unified Side-by-Side AP (Cost/Payables) and AR (Revenue/Billing) Ledger
- Live Accrual P&L Dashboard (Cost, Revenue, Advance, VAT, WHT, Profit Margin)
- Master Data Driven: Dynamic Charge Master & Business Parties Integration
- Multi-Currency Customer Billing / Invoicing with live Exchange Rate conversion
- Strict Single-Action Locking: Prevents duplicate pulls, repeat vouchers, or double billing
"""
from __future__ import annotations

import os
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import streamlit as st

from managers.auth_manager import can_write
from managers.charge_master_manager import list_charge_categories, list_charges
from managers.profit_manager import (
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


def _get_business_party_options(default_carrier: str = "", default_customer: str = "") -> List[Tuple[Optional[int], str, Dict[str, Any]]]:
    """Fetches business parties from Master Data and combines with Job parties."""
    options = [(None, "— Custom / Freeform —", {})]
    seen_names = set()

    try:
        from managers.master_data_crud_manager import list_parties
        parties = list_parties(active_only=True) or []
        for p in parties:
            p_id = p.get("id")
            roles = p.get("roles") or []
            role_tag = f"[{', '.join(roles)}]" if roles else "[Party]"
            name = p.get("legal_name") or p.get("display_name") or p.get("party_code")
            if name and name not in seen_names:
                seen_names.add(name)
                lbl = f"🏢 {role_tag} {name} (Tax ID: {_s(p.get('tax_id'))})"
                options.append((p_id, lbl, p))
    except Exception:
        pass

    if default_carrier and default_carrier not in seen_names:
        seen_names.add(default_carrier)
        options.append((None, f"🚢 [Carrier / Line] {default_carrier}", {"legal_name": default_carrier}))
    if default_customer and default_customer not in seen_names:
        seen_names.add(default_customer)
        options.append((None, f"👤 [Customer / Consignee] {default_customer}", {"legal_name": default_customer}))

    return options


def _get_charge_master_options() -> List[Tuple[Optional[str], str, Dict[str, Any]]]:
    """Fetches standard charges from Master Data database."""
    charges = list_charges(active_only=True) or []
    options = [(None, "— Custom / Freeform Charge —", {})]
    for c in charges:
        code = c.get("charge_code")
        desc = c.get("description")
        cat = c.get("category")
        lbl = f"💳 [{code}] {desc} ({cat})"
        options.append((code, lbl, c))
    return options


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

    page_header("Job Profitability & Unified AP / AR Control Center", "ตารางรวมต้นทุน AP - รายได้ AR, การตั้งเบิก/วางบิลเป็นชุด และวิเคราะห์กำไร P&L")

    # 1. Job Selector
    ships = list_shipments(limit=200) or []
    if not ships:
        st.info("No active freight jobs available. Please create a Job in Booking / Job Control first.")
        return

    job_options = {f"🚢 {s['job_no']} — {_s(s.get('customer_name'))} ({_s(s.get('pol'))} ➔ {_s(s.get('pod'))})": s for s in ships}
    
    pre_sel = st.session_state.get("target_job_no") or st.session_state.get("job_control_selector")
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
    ap_lines = ledger["ap_lines"]
    ar_lines = ledger["ar_lines"]

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

    # 4. Master Data Business Parties & Charge Codes Cache
    bp_options = _get_business_party_options(
        default_carrier=ship.get("carrier") or "",
        default_customer=ship.get("customer_name") or ""
    )
    charge_options = _get_charge_master_options()
    db_categories = list_charge_categories()

    # 5. Filter Active & Available Lines (Exclude already Pulled, Vouchered, Invoiced)
    ap_available_for_pull = [r for r in ap_lines if not r.get("is_matched") and not r.get("matched_ar_id")]
    ap_available_for_pv = [r for r in ap_lines if str(r.get("payout_status")).upper() != "PAID" and not r.get("voucher_no")]
    ar_available_for_inv = [r for r in ar_lines if str(r.get("billing_status")).upper() not in ["INVOICED", "COLLECTED", "PAID"] and not r.get("invoice_no")]

    # 6. Prominent Multi-Select & Batch Action Command Bar
    section("⚡ Batch Action Control Bar (ศูนย์สั่งการเบิกจ่าย, วางบิล และส่งออกเอกสาร)")

    # Status notice of active vs locked lines
    pulled_count = len(ap_lines) - len(ap_available_for_pull)
    vouchered_count = len(ap_lines) - len(ap_available_for_pv)
    invoiced_count = len(ar_lines) - len(ar_available_for_inv)
    if pulled_count > 0 or vouchered_count > 0 or invoiced_count > 0:
        st.caption(f"🔒 **Locked Status:** {pulled_count} AP lines pulled to AR | {vouchered_count} AP lines in Vouchers | {invoiced_count} AR lines on Invoices (ป้องกันการดึงหรือทำรายการซ้ำ)")

    b_col_ap, b_col_ar = st.columns(2)
    with b_col_ap:
        # Show AP lines that can be actioned (Payment Voucher or Pull to AR)
        ap_select_opts = {}
        for r in ap_lines:
            status_flags = []
            if r.get("is_matched") or r.get("matched_ar_id"):
                status_flags.append("🔒 Pulled to AR")
            if r.get("voucher_no"):
                status_flags.append(f"🔒 Voucher: {r.get('voucher_no')}")
            flag_str = f" [{', '.join(status_flags)}]" if status_flags else " [⚡ Available]"
            
            lbl = f"#{r['id']} - {r.get('description')} [{r.get('supplier','—')}] (Inv: {_s(r.get('vendor_invoice_no'))}) - {_money(r.get('amount_thb'))}{flag_str}"
            ap_select_opts[lbl] = r["id"]

        # Only default selectable to available lines
        selected_ap_labels = st.multiselect(
            "Select AP Lines for Batch Action (เลือกรายการตั้งเบิกจ่าย AP หรือ Pull to AR) *",
            options=list(ap_select_opts.keys()),
            key=f"batch_ap_sel_{shipment_id}",
            help="Select one or more available AP cost lines to pull to AR or create a Payment Voucher / Advance Request."
        )
        selected_ap_ids = [ap_select_opts[k] for k in selected_ap_labels]
        selected_ap_sum = sum(float(r.get("amount_thb") or 0) for r in ap_lines if r["id"] in selected_ap_ids)

    with b_col_ar:
        ar_select_opts = {}
        for r in ar_lines:
            status_flags = []
            if r.get("invoice_no"):
                status_flags.append(f"🔒 Invoice: {r.get('invoice_no')}")
            flag_str = f" [{', '.join(status_flags)}]" if status_flags else " [⚡ Available]"

            lbl = f"#{r['id']} - {r.get('description')} [{r.get('supplier','—')}] - {_money(r.get('amount_thb'))}{flag_str}"
            ar_select_opts[lbl] = r["id"]

        selected_ar_labels = st.multiselect(
            "Select AR Lines for Batch Action (เลือกรายการออกใบแจ้งหนี้ AR) *",
            options=list(ar_select_opts.keys()),
            key=f"batch_ar_sel_{shipment_id}",
            help="Select one or more available AR revenue lines to group into a customer invoice."
        )
        selected_ar_ids = [ar_select_opts[k] for k in selected_ar_labels]
        selected_ar_sum = sum(float(r.get("amount_thb") or 0) for r in ar_lines if r["id"] in selected_ar_ids)

    # Active Selection Status Banner
    st.info(f"📌 **Current Batch Selection:** **{len(selected_ap_ids)} AP Lines Selected** ({_money(selected_ap_sum)}) | **{len(selected_ar_ids)} AR Lines Selected** ({_money(selected_ar_sum)})")

    # Primary Action Buttons Bar (Horizontal 5 Action Columns)
    act1, act2, act3, act4, act5 = st.columns(5)

    with act1:
        if st.button("⚡ ตั้งเบิก AP (Voucher)", key=f"btn_pv_act_{shipment_id}", width="stretch", type="primary" if selected_ap_ids else "secondary"):
            if not selected_ap_ids:
                st.warning("⚠️ กรุณาเลือกรายการ AP อย่างน้อย 1 รายการในช่องด้านบนก่อนกดตั้งเบิก")
            else:
                # Check for already vouchered lines
                already_v = [r for r in ap_lines if r["id"] in selected_ap_ids and r.get("voucher_no")]
                if already_v:
                    v_str = ", ".join([f"#{x.get('id')} ({x.get('voucher_no')})" for x in already_v])
                    st.error(f"⚠️ รายการ AP ต่อไปนี้ถูกตั้งเบิกไปแล้ว: {v_str}")
                else:
                    st.session_state[f"show_pv_modal_{shipment_id}"] = "PV"

    with act2:
        if st.button("💵 เบิกสำรองจ่าย (Advance)", key=f"btn_adv_act_{shipment_id}", width="stretch"):
            if not selected_ap_ids:
                st.warning("⚠️ กรุณาเลือกรายการ AP อย่างน้อย 1 รายการในช่องด้านบน")
            else:
                already_v = [r for r in ap_lines if r["id"] in selected_ap_ids and r.get("voucher_no")]
                if already_v:
                    v_str = ", ".join([f"#{x.get('id')} ({x.get('voucher_no')})" for x in already_v])
                    st.error(f"⚠️ รายการ AP ต่อไปนี้ถูกตั้งเบิกไปแล้ว: {v_str}")
                else:
                    st.session_state[f"show_pv_modal_{shipment_id}"] = "ADV"

    with act3:
        if st.button("📥 ดึง AP ➔ AR", key=f"btn_pull_act_{shipment_id}", width="stretch"):
            if not selected_ap_ids:
                st.warning("⚠️ กรุณาเลือกรายการ AP ที่ต้องการดึงไปเป็นรายได้ AR ในช่องด้านบน")
            else:
                already_p = [r for r in ap_lines if r["id"] in selected_ap_ids and (r.get("is_matched") or r.get("matched_ar_id"))]
                if already_p:
                    p_str = ", ".join([f"#{x.get('id')}" for x in already_p])
                    st.error(f"⚠️ รายการ AP ต่อไปนี้ถูกดึงไปเป็น AR แล้ว: {p_str} (ไม่สามารถดึงซ้ำได้)")
                else:
                    st.session_state[f"show_pull_modal_{shipment_id}"] = True

    with act4:
        if st.button("🧾 วางบิล AR (Invoice)", key=f"btn_inv_act_{shipment_id}", width="stretch", type="primary" if selected_ar_ids else "secondary"):
            if not selected_ar_ids:
                st.warning("⚠️ กรุณาเลือกรายการ AR อย่างน้อย 1 รายการในช่องด้านบนเพื่อออกใบแจ้งหนี้")
            else:
                already_i = [r for r in ar_lines if r["id"] in selected_ar_ids and r.get("invoice_no")]
                if already_i:
                    i_str = ", ".join([f"#{x.get('id')} ({x.get('invoice_no')})" for x in already_i])
                    st.error(f"⚠️ รายการ AR ต่อไปนี้ถูกออกใบแจ้งหนี้ไปแล้ว: {i_str}")
                else:
                    st.session_state[f"show_inv_modal_{shipment_id}"] = True

    with act5:
        if st.button("📊 พิมพ์ P&L PDF", key=f"btn_pdf_act_{shipment_id}", width="stretch"):
            _render_pdf_profit_sheet(shipment_id)
        ps_bytes = st.session_state.get(f"profit_pdf_bytes_{shipment_id}")
        if ps_bytes:
            st.download_button(
                "⬇️ Download P&L PDF",
                data=ps_bytes,
                file_name=st.session_state.get(f"profit_pdf_name_{shipment_id}", f"Profit_{job_no}.pdf"),
                mime="application/pdf",
                key=f"dl_ps_pdf_bar_{shipment_id}",
                width="stretch"
            )

    # -------------------------------------------------------------
    # ACTION DIALOG PANELS (TRIGGERED BY PROMINENT BUTTONS)
    # -------------------------------------------------------------
    # A. Payment Voucher / Advance Request Action Panel
    if st.session_state.get(f"show_pv_modal_{shipment_id}"):
        pv_mode = st.session_state.get(f"show_pv_modal_{shipment_id}")
        is_adv = pv_mode == "ADV"
        title_tag = "ใบขอเบิกเงินทดรองจ่าย (Advance Request)" if is_adv else "ใบสำคัญจ่าย (Payment Voucher)"
        
        with st.container():
            st.markdown(f"### ⚡ ดำเนินการสร้าง {title_tag}")
            st.caption(f"สร้างเอกสารรวม {len(selected_ap_ids)} รายการ AP ที่เลือก (ยอดรวม {_money(selected_ap_sum)})")
            
            chosen_lines = [r for r in ap_lines if r["id"] in selected_ap_ids]
            default_payee = chosen_lines[0].get("supplier") if chosen_lines else ship.get("carrier")
            vinv_collected = [str(l.get("vendor_invoice_no")).strip() for l in chosen_lines if l.get("vendor_invoice_no") and str(l.get("vendor_invoice_no")).strip() not in ("None", "—", "")]
            vinv_preview = ", ".join(dict.fromkeys(vinv_collected)) if vinv_collected else "—"

            pv_c1, pv_c2, pv_c3 = st.columns(3)
            with pv_c1:
                payee_choice = st.selectbox(
                    "Payee / Vendor (ผู้รับเงินจาก Master Data) *",
                    options=range(len(bp_options)),
                    format_func=lambda idx: bp_options[idx][1],
                    key=f"pv_bp_choice_{shipment_id}"
                )
                chosen_bp = bp_options[payee_choice]
                payee_final = chosen_bp[2].get("legal_name") or chosen_bp[2].get("display_name") or default_payee or "General Vendor"

            with pv_c2:
                pv_due = st.date_input("Payment Due Date (วันครบกำหนดจ่าย) *", value=date.today(), key=f"pv_due_date_{shipment_id}")
                st.caption(f"📄 **Ref Vendor Invoices:** `{vinv_preview}`")

            with pv_c3:
                st.write("")
                st.write("")
                conf_c1, conf_c2 = st.columns(2)
                with conf_c1:
                    if st.button("🚀 ยืนยันสร้างเอกสาร", type="primary", key=f"pv_confirm_{shipment_id}", width="stretch"):
                        try:
                            v_no = create_batch_payment_voucher(
                                shipment_id=shipment_id,
                                ap_line_ids=selected_ap_ids,
                                payee_name=payee_final,
                                voucher_type="ADVANCE_REQUEST" if is_adv else "PAYMENT_VOUCHER",
                                due_date=pv_due.isoformat(),
                                user=user
                            )
                            st.session_state[f"show_pv_modal_{shipment_id}"] = False
                            st.success(f"🎉 สร้างเอกสาร {v_no} สำเร็จเรียบร้อย!")
                            st.rerun()
                        except Exception as exc:
                            st.error(f"Failed to create voucher: {exc}")
                with conf_c2:
                    if st.button("ยกเลิก", key=f"pv_cancel_{shipment_id}", width="stretch"):
                        st.session_state[f"show_pv_modal_{shipment_id}"] = False
                        st.rerun()
            st.divider()

    # B. Pull AP ➔ AR Action Panel
    if st.session_state.get(f"show_pull_modal_{shipment_id}"):
        with st.container():
            st.markdown("### 📥 ดึงรายการต้นทุน AP ➔ ไปเป็นรายได้เรียกเก็บ AR")
            st.caption(f"ดึง {len(selected_ap_ids)} รายการ AP ไปเป็น AR พร้อมกำหนดอัตรากำไร (Markup %) หรือราคาขาย")

            p_c1, p_c2, p_c3 = st.columns(3)
            with p_c1:
                pull_markup = st.number_input("Markup % (กำไรส่วนเพิ่ม %)", min_value=0.0, value=15.0, step=5.0, key=f"p_markup_{shipment_id}")
            with p_c2:
                cust_choice = st.selectbox(
                    "Customer / Bill To (ลูกค้าจาก Master Data) *",
                    options=range(len(bp_options)),
                    format_func=lambda idx: bp_options[idx][1],
                    key=f"p_cust_choice_{shipment_id}"
                )
                chosen_cust_bp = bp_options[cust_choice]
                cust_final = chosen_cust_bp[2].get("legal_name") or ship.get("customer_name") or "Customer"
            with p_c3:
                st.write("")
                st.write("")
                pull_btn1, pull_btn2 = st.columns(2)
                with pull_btn1:
                    if st.button("🚀 ยืนยัน Pull to AR", type="primary", key=f"p_confirm_{shipment_id}", width="stretch"):
                        try:
                            created = pull_ap_to_ar(
                                shipment_id=shipment_id,
                                ap_line_ids=selected_ap_ids,
                                markup_pct=pull_markup,
                                target_customer=cust_final,
                                user=user
                            )
                            st.session_state[f"show_pull_modal_{shipment_id}"] = False
                            st.success(f"🎉 สร้างรายการ AR สำเร็จ {len(created)} รายการ!")
                            st.rerun()
                        except Exception as exc:
                            st.error(f"Pull failed: {exc}")
                with pull_btn2:
                    if st.button("ยกเลิก", key=f"p_cancel_{shipment_id}", width="stretch"):
                        st.session_state[f"show_pull_modal_{shipment_id}"] = False
                        st.rerun()
            st.divider()

    # C. Batch Invoice Action Panel (With Target Currency & Exchange Rate Selection)
    if st.session_state.get(f"show_inv_modal_{shipment_id}"):
        with st.container():
            st.markdown("### 🧾 ออกใบแจ้งหนี้ลูกค้า (Batch Customer Invoice)")
            st.caption(f"รวบรวม {len(selected_ar_ids)} รายการ AR ที่เลือก (ยอดรวม THB {_money(selected_ar_sum)}) ออกใบแจ้งหนี้")

            i_c1, i_c2, i_c3 = st.columns(3)
            with i_c1:
                curr_options = ["THB", "USD", "EUR", "JPY", "CNY", "SGD"]
                chosen_curr = st.selectbox("Target Billing Currency (สกุลเงินที่ต้องการวางบิล) *", curr_options, index=0, key=f"inv_bill_curr_{shipment_id}")
            with i_c2:
                default_ex_map = {"THB": 1.0, "USD": 35.5, "EUR": 38.5, "JPY": 0.24, "CNY": 4.9, "SGD": 26.5}
                def_rate = default_ex_map.get(chosen_curr, 1.0)
                inv_ex_rate = st.number_input(f"Exchange Rate ({chosen_curr} to THB) *", min_value=0.0001, value=float(def_rate), step=0.1, key=f"inv_ex_rate_{shipment_id}")
            with i_c3:
                converted_est = selected_ar_sum / inv_ex_rate if inv_ex_rate > 0 else selected_ar_sum
                st.metric(f"Total Billed ({chosen_curr})", f"{chosen_curr} {converted_est:,.2f}")

            inv_row1, inv_row2 = st.columns([2, 1])
            with inv_row1:
                st.write(f"**Customer:** {_s(ship.get('customer_name'))} | **Job No:** {job_no}")
            with inv_row2:
                inv_btn1, inv_btn2 = st.columns(2)
                with inv_btn1:
                    if st.button("🚀 ยืนยันออก Invoice", type="primary", key=f"i_confirm_{shipment_id}", width="stretch"):
                        try:
                            inv_no = create_batch_invoice_from_ar(
                                shipment_id=shipment_id,
                                ar_line_ids=selected_ar_ids,
                                customer_id=ship.get("customer_id") or 1,
                                billing_currency=chosen_curr,
                                exchange_rate=inv_ex_rate,
                                user=user
                            )
                            st.session_state[f"show_inv_modal_{shipment_id}"] = False
                            st.success(f"🎉 สร้างใบแจ้งหนี้ {inv_no} สำเร็จเรียบร้อย (สกุลเงิน {chosen_curr})!")
                            st.rerun()
                        except Exception as exc:
                            st.error(f"Invoice creation failed: {exc}")
                with inv_btn2:
                    if st.button("ยกเลิก", key=f"i_cancel_{shipment_id}", width="stretch"):
                        st.session_state[f"show_inv_modal_{shipment_id}"] = False
                        st.rerun()
            st.divider()

    # 7. Workspace Tabs
    tab_matrix, tab_audit, tab_signoffs = st.tabs([
        "📊 Unified AP / AR Ledger Matrix & Master Data Entry",
        "📜 Document Ledger & Audit Traceability (ประวัติเอกสารย้อนหลัง)",
        "📋 P&L Sign-off & Official Profit Sheets"
    ])

    with tab_matrix:
        # Master Data Driven Entry Forms
        if can_edit and not is_fin_locked:
            add_c1, add_c2 = st.columns(2)
            with add_c1:
                with st.expander("➕ เพิ่มรายการต้นทุน AP (Add Operational Cost จาก Master Data)", expanded=len(ap_lines) == 0):
                    # Charge Master Selector outside form for instant reactive auto-fill
                    cm_idx_ap = st.selectbox(
                        "Standard Charge from Master Data (เลือกค่าบริการมาตรฐาน)",
                        options=range(len(charge_options)),
                        format_func=lambda idx: charge_options[idx][1],
                        key=f"ap_cm_choice_{shipment_id}"
                    )
                    chosen_cm_ap = charge_options[cm_idx_ap][2]

                    # Auto-fill defaults from Charge Master
                    def_desc_ap = chosen_cm_ap.get("description") or "Ocean Freight"
                    def_cat_ap = chosen_cm_ap.get("category") or db_categories[0]
                    def_unit_ap = chosen_cm_ap.get("default_unit") or "CTR"
                    def_curr_ap = chosen_cm_ap.get("default_currency") or "THB"
                    def_tax_ap = chosen_cm_ap.get("default_tax_type") or "VAT 7%"
                    def_wht_ap = chosen_cm_ap.get("default_wht_type") or "None"
                    charge_code_ap = chosen_cm_ap.get("charge_code")

                    with st.form(f"quick_add_ap_form_{shipment_id}", clear_on_submit=True):
                        cat_ap = st.selectbox(
                            "AP Category *",
                            db_categories,
                            index=db_categories.index(def_cat_ap) if def_cat_ap in db_categories else 0,
                            key=f"q_ap_cat_{shipment_id}"
                        )
                        desc_ap = st.text_input("AP Description / Charge Name *", value=def_desc_ap, key=f"q_ap_desc_{shipment_id}")
                        
                        bp_idx = st.selectbox(
                            "Payee / Vendor (เชื่อมโยง Business Parties) *",
                            options=range(len(bp_options)),
                            format_func=lambda idx: bp_options[idx][1],
                            key=f"q_ap_bp_{shipment_id}"
                        )
                        chosen_ap_bp = bp_options[bp_idx]
                        supp_ap = chosen_ap_bp[2].get("legal_name") or chosen_ap_bp[2].get("display_name") or _s(ship.get("carrier"), "")
                        party_id_ap = chosen_ap_bp[0]

                        f1, f2, f3 = st.columns(3)
                        qty_ap = f1.number_input("Qty", min_value=0.01, value=1.0, step=1.0, key=f"q_ap_qty_{shipment_id}")
                        unit_opts = ["CTR", "BL", "CBM", "TRIP", "SHPT", "LOT", "SET", "KG"]
                        unit_idx = unit_opts.index(def_unit_ap) if def_unit_ap in unit_opts else 0
                        unit_ap = f2.selectbox("Unit", unit_opts, index=unit_idx, key=f"q_ap_unit_{shipment_id}")
                        prc_ap = f3.number_input("Unit Price Rate", min_value=0.0, value=0.0, step=500.0, key=f"q_ap_prc_{shipment_id}")

                        t1, t2, t3 = st.columns(3)
                        curr_opts = ["THB", "USD", "EUR", "CNY", "JPY", "SGD"]
                        curr_idx = curr_opts.index(def_curr_ap) if def_curr_ap in curr_opts else 0
                        curr_ap = t1.selectbox("Currency", curr_opts, index=curr_idx, key=f"q_ap_curr_{shipment_id}")
                        ex_ap = t2.number_input("Ex.Rate to THB", min_value=0.001, value=1.0 if curr_ap == "THB" else 35.5, step=0.1, key=f"q_ap_ex_{shipment_id}")
                        tax_idx = TAX_TYPES.index(def_tax_ap) if def_tax_ap in TAX_TYPES else 0
                        tax_ap = t3.selectbox("Tax / VAT Type", TAX_TYPES, index=tax_idx, key=f"q_ap_tax_{shipment_id}")
                        
                        w1, w2, w3 = st.columns(3)
                        wht_idx = WHT_TYPES.index(def_wht_ap) if def_wht_ap in WHT_TYPES else 0
                        wht_ap = w1.selectbox("Withholding Tax (WHT)", WHT_TYPES, index=wht_idx, key=f"q_ap_wht_{shipment_id}")
                        vinv_ap = w2.text_input("Vendor Invoice / Tax Inv No.", placeholder="e.g. ONE-12345 / PAT-8899", key=f"q_ap_vinv_{shipment_id}")
                        vinv_date = w3.date_input("Vendor Invoice Date", value=date.today(), key=f"q_ap_vdate_{shipment_id}")

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
                                    "party_id": party_id_ap,
                                    "matched_charge_code": charge_code_ap,
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
                                    "vendor_invoice_date": vinv_date.isoformat(),
                                    "created_by": user.get("username", "operation"),
                                })
                                st.success("AP Cost Line added.")
                                st.rerun()

            with add_c2:
                with st.expander("➕ เพิ่มรายการรายได้ AR (Add Customer Revenue จาก Master Data)", expanded=len(ar_lines) == 0):
                    cm_idx_ar = st.selectbox(
                        "Standard Charge from Master Data (เลือกค่าบริการมาตรฐาน)",
                        options=range(len(charge_options)),
                        format_func=lambda idx: charge_options[idx][1],
                        key=f"ar_cm_choice_{shipment_id}"
                    )
                    chosen_cm_ar = charge_options[cm_idx_ar][2]

                    def_desc_ar = chosen_cm_ar.get("description") or "Ocean Freight Revenue"
                    def_cat_ar = chosen_cm_ar.get("category") or db_categories[0]
                    def_unit_ar = chosen_cm_ar.get("default_unit") or "CTR"
                    def_curr_ar = chosen_cm_ar.get("default_currency") or "THB"
                    def_tax_ar = chosen_cm_ar.get("default_tax_type") or "VAT 7%"
                    def_wht_ar = chosen_cm_ar.get("default_wht_type") or "None"
                    charge_code_ar = chosen_cm_ar.get("charge_code")

                    with st.form(f"quick_add_ar_form_{shipment_id}", clear_on_submit=True):
                        cat_ar = st.selectbox(
                            "AR Category *",
                            db_categories,
                            index=db_categories.index(def_cat_ar) if def_cat_ar in db_categories else 0,
                            key=f"q_ar_cat_{shipment_id}"
                        )
                        desc_ar = st.text_input("AR Description / Charge Name *", value=def_desc_ar, key=f"q_ar_desc_{shipment_id}")
                        
                        bp_ar_idx = st.selectbox(
                            "Customer / Bill To (เชื่อมโยง Business Parties) *",
                            options=range(len(bp_options)),
                            format_func=lambda idx: bp_options[idx][1],
                            key=f"q_ar_bp_{shipment_id}"
                        )
                        chosen_ar_bp = bp_options[bp_ar_idx]
                        cust_ar = chosen_ar_bp[2].get("legal_name") or chosen_ar_bp[2].get("display_name") or _s(ship.get("customer_name"), "")
                        party_id_ar = chosen_ar_bp[0]

                        f1, f2, f3 = st.columns(3)
                        qty_ar = f1.number_input("Qty", min_value=0.01, value=1.0, step=1.0, key=f"q_ar_qty_{shipment_id}")
                        unit_opts = ["CTR", "BL", "CBM", "TRIP", "SHPT", "LOT", "SET", "KG"]
                        unit_idx = unit_opts.index(def_unit_ar) if def_unit_ar in unit_opts else 0
                        unit_ar = f2.selectbox("Unit", unit_opts, index=unit_idx, key=f"q_ar_unit_{shipment_id}")
                        prc_ar = f3.number_input("Unit Price Selling Rate", min_value=0.0, value=0.0, step=500.0, key=f"q_ar_prc_{shipment_id}")

                        t1, t2, t3 = st.columns(3)
                        curr_opts = ["THB", "USD", "EUR", "CNY", "JPY", "SGD"]
                        curr_idx = curr_opts.index(def_curr_ar) if def_curr_ar in curr_opts else 0
                        curr_ar = t1.selectbox("Currency", curr_opts, index=curr_idx, key=f"q_ar_curr_{shipment_id}")
                        ex_ar = t2.number_input("Ex.Rate to THB", min_value=0.001, value=1.0 if curr_ar == "THB" else 35.5, step=0.1, key=f"q_ar_ex_{shipment_id}")
                        tax_idx = TAX_TYPES.index(def_tax_ar) if def_tax_ar in TAX_TYPES else 0
                        tax_ar = t3.selectbox("Tax / VAT Type", TAX_TYPES, index=tax_idx, key=f"q_ar_tax_{shipment_id}")
                        
                        w1, _ = st.columns(2)
                        wht_idx = WHT_TYPES.index(def_wht_ar) if def_wht_ar in WHT_TYPES else 0
                        wht_ar = w1.selectbox("Withholding Tax (WHT)", WHT_TYPES, index=wht_idx, key=f"q_ar_wht_{shipment_id}")

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
                                    "party_id": party_id_ar,
                                    "matched_charge_code": charge_code_ar,
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
            st.info("No cost or revenue lines recorded for this Job. Use the Master Data forms above to start building the ledger.")
        else:
            table_data = []
            for r in matrix_rows:
                # Link Status Tag
                if r["is_matched"]:
                    link_tag = "🔒 Pulled ➔ AR"
                elif r["ap_id"] and not r["ar_id"]:
                    link_tag = "✦ AP Available"
                else:
                    link_tag = "✦ Pure AR"

                table_data.append({
                    "No.": r["line_no"],
                    # AP Side
                    "AP Description (ต้นทุน)": r["ap_description"],
                    "Payee / Business Party": r["ap_supplier"],
                    "Vendor Inv No.": r.get("ap_vendor_inv", "—"),
                    "AP Rate": f"{r['ap_unit_price']:,.2f} {r['ap_currency']}" if r["ap_id"] else "—",
                    "AP Qty": f"{r['ap_quantity']:g} {r['ap_unit']}" if r["ap_id"] else "—",
                    "AP Amount (฿)": f"{r['ap_amount_thb']:,.2f}" if r["ap_id"] else "—",
                    "AP Tax/WHT": f"{r['ap_tax_type']} / {r['ap_wht_type']}" if r["ap_id"] else "—",
                    "AP Status": f"{r['ap_payout_status']} ({r['ap_voucher_no']})" if r["ap_id"] else "—",
                    # Bridge
                    "Link Status": link_tag,
                    # AR Side
                    "AR Description (เรียกเก็บ)": r["ar_description"],
                    "Customer (Business Party)": r["ar_customer"],
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
                    for ap in ap_lines:
                        del_opts.append((ap["id"], f"AP #{ap['id']} - {ap.get('description')} ({_money(ap.get('amount_thb'))})"))
                    for ar in ar_lines:
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
                    v_ref = _s(v.get("vendor_invoice_refs") or v.get("invoice_no"))
                    
                    with st.expander(f"📄 {v_no} — {v.get('payee_name','—')} | {_money(v.get('total'))} {v.get('currency','THB')} [{v.get('status','REQUESTED')}]", expanded=True):
                        st.write(f"**Voucher Type:** {v_type_label}")
                        st.write(f"**Ref Vendor Invoices:** `{v_ref}` | **Tax ID:** {_s(v.get('payee_tax_id'))}")
                        st.write(f"**Due Date:** {_s(v.get('due_date'))} | **Status:** {v.get('status')}")
                        
                        v_items = v.get("items", [])
                        if v_items:
                            st.write("**Itemized Charges (รายการที่รวมอยู่ในใบนี้):**")
                            st.dataframe(pd.DataFrame([{
                                "No.": idx,
                                "Description": it.get("description"),
                                "Vendor Inv No.": _s(it.get("vendor_invoice_no")),
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
                    with st.expander(f"📄 {doc_no} — {inv.get('customer_name','—')} | {_money(inv.get('grand_total'), inv.get('currency','THB'))} [{inv.get('status','ISSUED')}]", expanded=True):
                        st.write(f"**Customer:** {inv.get('customer_name')}")
                        st.write(f"**Billing Currency:** `{inv.get('currency','THB')}` | **Ex.Rate:** {float(inv.get('exchange_rate',1.0)):.4f}")
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