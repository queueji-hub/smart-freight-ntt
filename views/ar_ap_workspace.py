from __future__ import annotations
"""
Comprehensive Financial Control & Tax Reporting Workspace (PTS Standard)
Features: AR/AP Aging, Customer/Supplier SOA, Daily Collections & Disbursements,
Output VAT (ภาษีขาย), Input VAT (ภาษีซื้อ), and Withholding Tax Reports (ภ.ง.ด. 3/53).
"""

from datetime import date, datetime
import pandas as pd
import streamlit as st

from managers.invoice_manager import list_invoices, record_payment
from managers.ap_manager import get_ap_vouchers
from managers.customer_manager import list_customers
from managers.vendor_manager import get_vendors
from managers.auth_manager import can_write
from ui.design_system import page_header, section

PAYMENT_METHODS = ["Bank Transfer", "Cash", "Cheque", "Credit Card"]


def _num(value):
    try:
        return float(value or 0)
    except Exception:
        return 0.0


def _money(value):
    return f"{_num(value):,.2f}"


def _is_open(row):
    return str(row.get("status", "")).upper() not in {"CANCELLED", "PAID"} and _num(row.get("outstanding")) > 0


def _is_overdue(row):
    due = str(row.get("due_date") or "")
    return _is_open(row) and bool(due) and due < date.today().isoformat()


def render():
    page_header("billing", status_text="Online")
    user = st.session_state.get("user", {})
    writable = can_write(str(user.get("role", "")).lower(), "billing")
    
    invoices = list_invoices() or []
    ap_vouchers = get_ap_vouchers() or []
    
    open_invs = [r for r in invoices if _is_open(r)]
    overdue_invs = [r for r in open_invs if _is_overdue(r)]

    section("AR / Outstanding Control")
    
    # High-level Metrics
    billed = sum(_num(r.get("grand_total") or r.get("total_amount")) for r in invoices if str(r.get("status", "")).upper() != "CANCELLED")
    outstanding = sum(_num(r.get("outstanding")) for r in open_invs)
    paid = max(billed - outstanding, 0.0)
    overdue = sum(_num(r.get("outstanding")) for r in overdue_invs)
    ap_total = sum(_num(v.get("total")) for v in ap_vouchers)

    a, b, c, d = st.columns(4)
    a.metric("AR Billed", _money(billed) + " THB")
    b.metric("AR Paid", _money(paid) + " THB")
    c.metric("AR Outstanding", _money(outstanding) + " THB")
    d.metric("Overdue", _money(overdue) + " THB")

    tabs = st.tabs([
        "Accounts Receivable Aging",
        "Statement of Account (SOA)",
        "Payment Register",
        "💳 AP Control (Supplier Aging & SOA)",
        "🧾 Daily Reports (รายงานตรวจสอบรายวัน)",
        "📑 VAT Reports (ภาษีซื้อ / ภาษีขาย)",
        "📜 Withholding Tax (ภาษีหัก ณ ที่จ่าย)",
        "🌊 Cash Flow & Liquidity"
    ])

    # 1. AR AGING
    with tabs[0]:
        section("Accounts Receivable Aging")
        q = st.text_input("Search Customer / Document / Job / B/L", key="ar_search_filter")
        view_invs = open_invs
        if q.strip():
            view_invs = [r for r in view_invs if q.strip().lower() in str(r).lower()]

        today_dt = date.today()
        
        aging_rows = []
        for r in view_invs:
            due_str = str(r.get("due_date") or "")
            days_overdue = 0
            if due_str:
                try:
                    due_d = datetime.strptime(due_str[:10], "%Y-%m-%d").date()
                    days_overdue = (today_dt - due_d).days
                except Exception:
                    pass

            bucket = "Current (ยังไม่ถึงกำหนด)"
            if days_overdue > 90:
                bucket = "> 90 Days"
            elif days_overdue > 60:
                bucket = "61 - 90 Days"
            elif days_overdue > 30:
                bucket = "31 - 60 Days"
            elif days_overdue > 0:
                bucket = "1 - 30 Days"

            aging_rows.append({
                "Document": r.get("doc_no"),
                "Type": r.get("doc_type"),
                "Customer": r.get("customer_name"),
                "Issue": r.get("issue_date"),
                "Due": r.get("due_date"),
                "Overdue Days": max(days_overdue, 0),
                "Aging Bucket": bucket,
                "Total": _num(r.get("grand_total") or r.get("total_amount")),
                "Outstanding": _num(r.get("outstanding")),
                "Status": "OVERDUE" if days_overdue > 0 else r.get("status"),
            })
        st.dataframe(pd.DataFrame(aging_rows), hide_index=True, use_container_width=True)

    # 2. STATEMENT OF ACCOUNT (SOA)
    with tabs[1]:
        section("Statement of Account (SOA)")
        cust_names = sorted({str(r.get("customer_name")) for r in invoices if r.get("customer_name")})
        sel_cust = st.selectbox("Customer", cust_names, key="ar_soa_cust_select") if cust_names else None
        if sel_cust:
            c_invs = [r for r in invoices if r.get("customer_name") == sel_cust and str(r.get("status", "")).upper() != "CANCELLED"]
            c_balance = sum(_num(r.get("outstanding")) for r in c_invs)
            c_total_billed = sum(_num(r.get("grand_total") or r.get("total_amount")) for r in c_invs)
            c_paid = max(c_total_billed - c_balance, 0.0)

            sc1, sc2, sc3 = st.columns(3)
            sc1.metric("Customer Outstanding", _money(c_balance) + " THB")
            sc2.metric("Total Billed", _money(c_total_billed) + " THB")
            sc3.metric("Total Paid", _money(c_paid) + " THB")

            st.dataframe(pd.DataFrame([{
                "Document": r.get("doc_no"),
                "Date": r.get("issue_date"),
                "Due": r.get("due_date"),
                "Debit": _num(r.get("grand_total") or r.get("total_amount")),
                "Credit": max(_num(r.get("grand_total") or r.get("total_amount")) - _num(r.get("outstanding")), 0.0),
                "Balance": _num(r.get("outstanding")),
            } for r in c_invs]), hide_index=True, use_container_width=True)

    # 3. PAYMENT REGISTER
    with tabs[2]:
        section("Payment Register")
        if not writable:
            st.info("Payment entry requires billing write permission.")
        elif not open_invs:
            st.success("No outstanding AR documents.")
        else:
            options = [r.get("doc_no") for r in open_invs if r.get("doc_no")]
            selected = st.selectbox("Outstanding Document", options, key="ar_payment_doc")
            rec = next(r for r in open_invs if r.get("doc_no") == selected)
            st.caption(f"Customer: {rec.get('customer_name', '—')} · Outstanding: {_money(rec.get('outstanding'))} {rec.get('currency', 'THB')}")
            amount = st.number_input("Payment Amount", min_value=0.01, max_value=max(_num(rec.get("outstanding")), 0.01), value=max(_num(rec.get("outstanding")), 0.01), key="ar_payment_amount")
            method = st.selectbox("Payment Method", PAYMENT_METHODS, key="ar_payment_method")
            reference = st.text_input("Transaction Reference", key="ar_payment_ref")
            payment_date = st.date_input("Payment Date", date.today(), key="ar_payment_date")
            
            rc_btn1, rc_btn2 = st.columns([1, 1])
            if rc_btn1.button("Record Payment", type="primary", width="stretch", key="ar_record_payment"):
                try:
                    record_payment({"doc_no": selected, "amount": amount, "method": method, "reference": reference.strip(), "date": payment_date.isoformat()})
                    st.success(f"Payment recorded for {selected}. Receipt / Tax Invoice ready.")
                    st.rerun()
                except Exception as exc:
                    st.error(f"Payment failed: {exc}")

            with rc_btn2:
                from views.receipt_view import render_receipt_action
                render_receipt_action(selected)

    # 4. AP AGING & SOA
    with tabs[3]:
        sub_ap1, sub_ap2 = st.tabs(["AP Aging Analysis", "Supplier Statement of Account (SOA)"])
        
        with sub_ap1:
            st.markdown("##### ⏳ Accounts Payable Aging (รายงานวิเคราะห์อายุเจ้าหนี้)")
            ap_aging = []
            for v in ap_vouchers:
                ap_aging.append({
                    "PV No.": v.get("voucher_no") or f"PV-{v.get('id')}",
                    "Supplier": v.get("vendor_name"),
                    "Invoice Ref": v.get("invoice_no"),
                    "Date": v.get("invoice_date"),
                    "Due Date": v.get("due_date"),
                    "Total AP": _num(v.get("total")),
                    "WHT Total": _num(v.get("wht_total")),
                    "Net Payable": _num(v.get("net_payable") or v.get("total")),
                    "Status": v.get("status"),
                })
            st.dataframe(pd.DataFrame(ap_aging), hide_index=True, use_container_width=True)

        with sub_ap2:
            st.markdown("##### 🚢 Supplier Statement of Account (ใบแจ้งยอดบัญชีเจ้าหนี้/สายเรือรายตัว)")
            sup_names = sorted({str(v.get("vendor_name")) for v in ap_vouchers if v.get("vendor_name")})
            sel_sup = st.selectbox("Select Supplier", sup_names, key="ap_soa_sup_select") if sup_names else None
            if sel_sup:
                s_vouchers = [v for v in ap_vouchers if v.get("vendor_name") == sel_sup]
                s_total = sum(_num(v.get("total")) for v in s_vouchers)
                s_net = sum(_num(v.get("net_payable") or v.get("total")) for v in s_vouchers)

                st.write(f"**Supplier:** {sel_sup} | **Total Invoices:** {len(s_vouchers)} | **Total Payables:** {_money(s_total)} THB | **Net Payable:** {_money(s_net)} THB")
                st.dataframe(pd.DataFrame([{
                    "PV No.": v.get("voucher_no"),
                    "Date": v.get("invoice_date"),
                    "Invoice No.": v.get("invoice_no"),
                    "Job No.": v.get("job_no"),
                    "Subtotal": _num(v.get("subtotal")),
                    "VAT": _num(v.get("tax")),
                    "WHT": _num(v.get("wht_total")),
                    "Net Amount": _num(v.get("net_payable") or v.get("total")),
                    "Status": v.get("status"),
                } for v in s_vouchers]), hide_index=True, use_container_width=True)

    # 3. DAILY REPORTS
    with tabs[2]:
        st.markdown("#### 📅 Daily Check Reports (รายงานตรวจสอบการเงินประจำวัน)")
        r_type = st.radio("Select Daily Report", ["Daily Collect Receipt (รายงานตรวจสอบการรับเงินประจำวัน)", "Daily Payment Voucher (รายงานตรวจสอบการจ่ายเงินประจำวัน)"], horizontal=True)
        
        sel_date = st.date_input("Filter Date", date.today(), key="daily_rep_date").isoformat()

        if "Receipt" in r_type:
            d_rcs = [r for r in invoices if str(r.get("issue_date", ""))[:10] == sel_date]
            st.markdown(f"##### 📥 Receipts issued on {sel_date} ({len(d_rcs)} records)")
            if d_rcs:
                st.dataframe(pd.DataFrame([{
                    "Doc No.": r.get("doc_no"),
                    "Type": r.get("doc_type"),
                    "Customer": r.get("customer_name"),
                    "Service": r.get("service_type"),
                    "Total Amount": _num(r.get("grand_total") or r.get("total_amount")),
                    "VAT 7%": _num(r.get("vat_7_amount") or r.get("vat_amount")),
                    "WHT": _num(r.get("wht_amount")),
                    "Net Paid": _num(r.get("net_payable")),
                } for r in d_rcs]), hide_index=True, use_container_width=True)
            else:
                st.info(f"No receipts recorded on {sel_date}.")
        else:
            d_pvs = [v for v in ap_vouchers if str(v.get("invoice_date", ""))[:10] == sel_date]
            st.markdown(f"##### 📤 Payment Vouchers issued on {sel_date} ({len(d_pvs)} records)")
            if d_pvs:
                st.dataframe(pd.DataFrame([{
                    "PV No.": v.get("voucher_no"),
                    "Payee / Supplier": v.get("vendor_name"),
                    "Payment Type": v.get("payment_type"),
                    "Job No.": v.get("job_no"),
                    "Subtotal": _num(v.get("subtotal")),
                    "VAT 7%": _num(v.get("tax")),
                    "WHT": _num(v.get("wht_total")),
                    "Net Disbursed": _num(v.get("net_payable") or v.get("total")),
                } for v in d_pvs]), hide_index=True, use_container_width=True)
            else:
                st.info(f"No payment vouchers recorded on {sel_date}.")

    # 4. VAT REPORTS (INPUT / OUTPUT)
    with tabs[3]:
        st.markdown("#### 🧾 Value Added Tax Reports (รายงานภาษีมูลค่าเพิ่ม ภ.พ. 30)")
        vat_sub1, vat_sub2 = st.tabs(["รายงานภาษีขาย (Output VAT)", "รายงานภาษีซื้อ (Input VAT)"])

        with vat_sub1:
            st.markdown("##### 📤 รายงานภาษีขาย (Sales Tax Report)")
            tax_sales = []
            for r in invoices:
                vat_amt = _num(r.get("vat_7_amount") or r.get("vat_amount"))
                if vat_amt > 0 or _num(r.get("amount_vat")) > 0:
                    tax_sales.append({
                        "Tax Invoice No.": r.get("tax_receipt_no") or r.get("doc_no"),
                        "Date": r.get("issue_date"),
                        "Customer Name": r.get("customer_name"),
                        "Tax ID": r.get("customer_tax_id", "—"),
                        "Branch": r.get("customer_branch", "00000"),
                        "Tax Base (มูลค่าสินค้า/บริการ)": _num(r.get("amount_vat") or r.get("subtotal")),
                        "Output VAT 7% (ภาษีมูลค่าเพิ่ม)": vat_amt,
                        "Total": _num(r.get("grand_total") or r.get("total_amount")),
                    })
            st.dataframe(pd.DataFrame(tax_sales), hide_index=True, use_container_width=True)

        with vat_sub2:
            st.markdown("##### 📥 รายงานภาษีซื้อ (Purchase Tax Report)")
            tax_purchases = []
            for v in ap_vouchers:
                vat_amt = _num(v.get("tax") or v.get("supplier_tax_inv_vat"))
                if vat_amt > 0:
                    tax_purchases.append({
                        "Supplier Tax Inv No.": v.get("supplier_tax_inv_no") or v.get("invoice_no"),
                        "Date": v.get("supplier_tax_inv_date") or v.get("invoice_date"),
                        "Supplier Name": v.get("vendor_name"),
                        "Tax ID": v.get("vendor_tax_id", "—"),
                        "Branch": v.get("supplier_tax_inv_branch", "00000"),
                        "Tax Base (มูลค่าสินค้า/บริการ)": _num(v.get("supplier_tax_inv_base") or v.get("amount_vat") or v.get("subtotal")),
                        "Input VAT 7% (ภาษีซื้อ)": vat_amt,
                        "Total": _num(v.get("total")),
                    })
            st.dataframe(pd.DataFrame(tax_purchases), hide_index=True, use_container_width=True)

    # 5. WITHHOLDING TAX REPORTS (ภ.ง.ด. 3 / ภ.ง.ด. 53)
    with tabs[4]:
        st.markdown("#### 📜 Withholding Tax Reports & 50 ทวิ Summary")
        wht_sub1, wht_sub2 = st.tabs(["ภาษีหัก ณ ที่จ่าย (ภ.ง.ด. 53 / นิติบุคคล)", "ภาษีหัก ณ ที่จ่าย (ภ.ง.ด. 3 / บุคคลธรรมดา)"])
        
        with wht_sub1:
            st.markdown("##### 🏢 รายงานภาษีหัก ณ ที่จ่าย ภ.ง.ด. 53 (จ่ายนิติบุคคล)")
            wht_53 = []
            for v in ap_vouchers:
                if str(v.get("wht_pnd_type", "53")) == "53" and _num(v.get("wht_total")) > 0:
                    wht_53.append({
                        "50 ทวิ No.": v.get("wht_cert_no") or f"WH-{v.get('id')}",
                        "Date": v.get("wht_cert_date") or v.get("invoice_date"),
                        "Payee Name (ผู้ถูกหัก)": v.get("vendor_name"),
                        "Tax ID (13 หลัก)": v.get("vendor_tax_id", "—"),
                        "Payment Type": v.get("payment_type"),
                        "Base Amount (เงินได้ที่จ่าย)": _num(v.get("wht_base_amount") or v.get("subtotal")),
                        "Tax Deducted (ภาษีที่หัก)": _num(v.get("wht_tax_amount") or v.get("wht_total")),
                    })
            st.dataframe(pd.DataFrame(wht_53), hide_index=True, use_container_width=True)

        with wht_sub2:
            st.markdown("##### 👤 รายงานภาษีหัก ณ ที่จ่าย ภ.ง.ด. 3 (จ่ายบุคคลธรรมดา)")
            wht_3 = []
            for v in ap_vouchers:
                if str(v.get("wht_pnd_type")) == "3" and _num(v.get("wht_total")) > 0:
                    wht_3.append({
                        "50 ทวิ No.": v.get("wht_cert_no") or f"WH-{v.get('id')}",
                        "Date": v.get("wht_cert_date") or v.get("invoice_date"),
                        "Payee Name": v.get("vendor_name"),
                        "Tax ID": v.get("vendor_tax_id", "—"),
                        "Base Amount": _num(v.get("wht_base_amount") or v.get("subtotal")),
                        "Tax Deducted": _num(v.get("wht_tax_amount") or v.get("wht_total")),
                    })
            st.dataframe(pd.DataFrame(wht_3), hide_index=True, use_container_width=True)

    # 6. CASH FLOW & LIQUIDITY
    with tabs[5]:
        st.markdown("#### 🌊 Cash Flow & Liquidity Analysis")
        total_ap_payout = sum(float(v.get("total") or 0) for v in ap_vouchers if v.get("status") in ("POSTED", "PAID", "APPROVED"))
        total_ap_pending = sum(float(v.get("total") or 0) for v in ap_vouchers if v.get("status") not in ("PAID", "CANCELLED", "APPROVED"))
        
        net_cashflow_realized = paid - total_ap_payout
        net_cashflow_projected = billed - (total_ap_payout + total_ap_pending)
        
        cf1, cf2, cf3, cf4 = st.columns(4)
        cf1.metric("Cash Inflow (AR Collections)", _money(paid) + " THB")
        cf2.metric("Cash Outflow (AP Disbursements)", _money(total_ap_payout) + " THB")
        cf3.metric("Net Realized Cash Flow", _money(net_cashflow_realized) + " THB")
        cf4.metric("Projected Net Cash Flow", _money(net_cashflow_projected) + " THB")
        
        st.markdown("##### 📊 Cash Inflow vs. Outflow Summary")
        cf_summary = [
            {"Category": "AR Collections (เงินรับชำระจากลูกค้า)", "Amount (THB)": _money(paid), "Status": "Received Inflow"},
            {"Category": "AR Outstanding (ยอดลูกหนี้รอเรียกเก็บ)", "Amount (THB)": _money(outstanding), "Status": "Pending Inflow"},
            {"Category": "AP Disbursements (เงินจ่ายสายเรือ/Vendor)", "Amount (THB)": _money(total_ap_payout), "Status": "Disbursed Outflow"},
            {"Category": "AP Pending (ยอดเจ้าหนี้รอเบิกจ่าย)", "Amount (THB)": _money(total_ap_pending), "Status": "Pending Outflow"},
            {"Category": "Net Cash Position (กระแสเงินสดสุทธิ)", "Amount (THB)": _money(net_cashflow_realized), "Status": "Net Liquidity"},
        ]
        st.dataframe(pd.DataFrame(cf_summary), use_container_width=True, hide_index=True)
