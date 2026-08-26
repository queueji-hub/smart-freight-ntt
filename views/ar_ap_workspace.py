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

    # 5. DAILY REPORTS (RECEIPTS & PAYMENTS)
    with tabs[4]:
        st.markdown("#### 📅 Daily Check Reports (รายงานตรวจสอบการเงินประจำวัน)")
        r_type = st.radio("Select Daily Report", ["Daily Collect Receipt (รายงานตรวจสอบการรับเงินประจำวัน)", "Daily Payment Voucher (รายงานตรวจสอบการจ่ายเงินประจำวัน)"], horizontal=True, key="daily_rep_type_choice")
        
        sel_date_val = st.date_input("Filter Date (เลือกวันที่ตรวจสอบ)", date.today(), key="daily_rep_date_input")
        sel_date = sel_date_val.isoformat()

        if "Receipt" in r_type:
            d_rcs = [r for r in invoices if str(r.get("issue_date", ""))[:10] == sel_date and str(r.get("status", "")).upper() != "CANCELLED"]
            st.markdown(f"##### 📥 Receipts & Tax Invoices issued on {sel_date} ({len(d_rcs)} records)")
            
            rc_df_data = [{
                "Doc No.": r.get("doc_no"),
                "Tax Inv No.": r.get("tax_receipt_no") or r.get("doc_no"),
                "Type": r.get("doc_type"),
                "Customer": r.get("customer_name"),
                "Service": r.get("service_type"),
                "Tax Base": _num(r.get("amount_vat") or r.get("subtotal")),
                "VAT 7%": _num(r.get("vat_7_amount") or r.get("vat_amount")),
                "WHT": _num(r.get("wht_amount")),
                "Net Collected": _num(r.get("net_payable") or r.get("grand_total")),
                "Payment Status": r.get("payment_status", "PAID"),
            } for r in d_rcs]
            
            if rc_df_data:
                st.dataframe(pd.DataFrame(rc_df_data), hide_index=True, use_container_width=True)
            else:
                st.info(f"No receipts recorded on {sel_date}.")

            btn_col1, btn_col2 = st.columns([1, 1])
            with btn_col1:
                if st.button("🖨️ Generate Daily Receipts PDF Report", key="btn_gen_daily_rc_pdf", type="primary", use_container_width=True):
                    try:
                        from pdf.financial_reports_pdf import generate_daily_receipts_pdf
                        p_path = generate_daily_receipts_pdf(sel_date, d_rcs)
                        if p_path and os.path.exists(p_path):
                            with open(p_path, "rb") as fh:
                                st.session_state[f"pdf_bytes_rc_{sel_date}"] = fh.read()
                            st.session_state[f"pdf_name_rc_{sel_date}"] = os.path.basename(p_path)
                            st.success("✅ สร้างรายงาน PDF สำเร็จ")
                    except Exception as exc:
                        st.error(f"Failed to generate Daily Receipts PDF: {exc}")

                if st.session_state.get(f"pdf_bytes_rc_{sel_date}"):
                    st.download_button(
                        "⬇️ Download Daily Receipts PDF",
                        st.session_state[f"pdf_bytes_rc_{sel_date}"],
                        file_name=st.session_state.get(f"pdf_name_rc_{sel_date}", f"Daily_Receipts_{sel_date}.pdf"),
                        mime="application/pdf",
                        key="dl_btn_daily_rc_pdf",
                        use_container_width=True,
                    )

            with btn_col2:
                if rc_df_data:
                    csv_data = pd.DataFrame(rc_df_data).to_csv(index=False).encode('utf-8-sig')
                    st.download_button(
                        "📥 Export Daily Receipts CSV / Excel",
                        csv_data,
                        file_name=f"Daily_Receipts_{sel_date}.csv",
                        mime="text/csv",
                        key="dl_btn_daily_rc_csv",
                        use_container_width=True,
                    )
        else:
            d_pvs = [v for v in ap_vouchers if str(v.get("invoice_date", ""))[:10] == sel_date]
            st.markdown(f"##### 📤 Payment Vouchers issued on {sel_date} ({len(d_pvs)} records)")
            
            pv_df_data = [{
                "PV No.": v.get("voucher_no"),
                "Payee / Supplier": v.get("vendor_name") or v.get("payee_name"),
                "Tax ID": v.get("vendor_tax_id") or v.get("payee_tax_id"),
                "Payment Type": v.get("payment_type"),
                "Job No.": v.get("job_no"),
                "Subtotal": _num(v.get("subtotal")),
                "VAT 7%": _num(v.get("tax")),
                "WHT": _num(v.get("wht_total")),
                "Net Disbursed": _num(v.get("net_payable") or v.get("total")),
                "Status": v.get("status"),
            } for v in d_pvs]

            if pv_df_data:
                st.dataframe(pd.DataFrame(pv_df_data), hide_index=True, use_container_width=True)
            else:
                st.info(f"No payment vouchers recorded on {sel_date}.")

            btn_col1, btn_col2 = st.columns([1, 1])
            with btn_col1:
                if st.button("🖨️ Generate Daily Payments PDF Report", key="btn_gen_daily_pv_pdf", type="primary", use_container_width=True):
                    try:
                        from pdf.financial_reports_pdf import generate_daily_payments_pdf
                        p_path = generate_daily_payments_pdf(sel_date, d_pvs)
                        if p_path and os.path.exists(p_path):
                            with open(p_path, "rb") as fh:
                                st.session_state[f"pdf_bytes_pv_{sel_date}"] = fh.read()
                            st.session_state[f"pdf_name_pv_{sel_date}"] = os.path.basename(p_path)
                            st.success("✅ สร้างรายงาน PDF สำเร็จ")
                    except Exception as exc:
                        st.error(f"Failed to generate Daily Payments PDF: {exc}")

                if st.session_state.get(f"pdf_bytes_pv_{sel_date}"):
                    st.download_button(
                        "⬇️ Download Daily Payments PDF",
                        st.session_state[f"pdf_bytes_pv_{sel_date}"],
                        file_name=st.session_state.get(f"pdf_name_pv_{sel_date}", f"Daily_Payments_{sel_date}.pdf"),
                        mime="application/pdf",
                        key="dl_btn_daily_pv_pdf",
                        use_container_width=True,
                    )

            with btn_col2:
                if pv_df_data:
                    csv_data = pd.DataFrame(pv_df_data).to_csv(index=False).encode('utf-8-sig')
                    st.download_button(
                        "📥 Export Daily Payments CSV / Excel",
                        csv_data,
                        file_name=f"Daily_Payments_{sel_date}.csv",
                        mime="text/csv",
                        key="dl_btn_daily_pv_csv",
                        use_container_width=True,
                    )

    # 6. VAT REPORTS (INPUT / OUTPUT ภ.พ. 30)
    with tabs[5]:
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
            if tax_sales:
                st.dataframe(pd.DataFrame(tax_sales), hide_index=True, use_container_width=True)
            else:
                st.info("No sales tax records.")

            c_v1, c_v2 = st.columns(2)
            with c_v1:
                if st.button("🖨️ Export Output VAT PDF (ภ.พ. 30)", key="btn_pdf_vat_sales", type="primary", use_container_width=True):
                    try:
                        from pdf.financial_reports_pdf import generate_vat_report_pdf
                        p_path = generate_vat_report_pdf("OUTPUT_SALES", tax_sales)
                        if p_path and os.path.exists(p_path):
                            with open(p_path, "rb") as fh:
                                st.session_state["pdf_bytes_vat_sales"] = fh.read()
                            st.session_state["pdf_name_vat_sales"] = os.path.basename(p_path)
                            st.success("✅ สร้างรายงานภาษีขายสำเร็จ")
                    except Exception as exc:
                        st.error(f"Failed: {exc}")

                if st.session_state.get("pdf_bytes_vat_sales"):
                    st.download_button(
                        "⬇️ Download Output VAT PDF",
                        st.session_state["pdf_bytes_vat_sales"],
                        file_name=st.session_state.get("pdf_name_vat_sales", "Output_VAT_Report.pdf"),
                        mime="application/pdf",
                        key="dl_btn_vat_sales_pdf",
                        use_container_width=True,
                    )

            with c_v2:
                if tax_sales:
                    st.download_button(
                        "📥 Export Output VAT CSV",
                        pd.DataFrame(tax_sales).to_csv(index=False).encode('utf-8-sig'),
                        file_name="Output_VAT_Sales.csv",
                        mime="text/csv",
                        key="dl_btn_vat_sales_csv",
                        use_container_width=True,
                    )

        with vat_sub2:
            st.markdown("##### 📥 รายงานภาษีซื้อ (Purchase Tax Report)")
            tax_purchases = []
            for v in ap_vouchers:
                vat_amt = _num(v.get("tax") or v.get("supplier_tax_inv_vat"))
                if vat_amt > 0:
                    tax_purchases.append({
                        "Supplier Tax Inv No.": v.get("supplier_tax_inv_no") or v.get("invoice_no") or v.get("voucher_no"),
                        "Date": v.get("supplier_tax_inv_date") or v.get("invoice_date"),
                        "Supplier Name": v.get("vendor_name") or v.get("payee_name"),
                        "Tax ID": v.get("vendor_tax_id") or v.get("payee_tax_id", "—"),
                        "Branch": v.get("supplier_tax_inv_branch", "00000"),
                        "Tax Base (มูลค่าสินค้า/บริการ)": _num(v.get("supplier_tax_inv_base") or v.get("amount_vat") or v.get("subtotal")),
                        "Input VAT 7% (ภาษีซื้อ)": vat_amt,
                        "Total": _num(v.get("total")),
                    })
            if tax_purchases:
                st.dataframe(pd.DataFrame(tax_purchases), hide_index=True, use_container_width=True)
            else:
                st.info("No purchase tax records.")

            c_vp1, c_vp2 = st.columns(2)
            with c_vp1:
                if st.button("🖨️ Export Input VAT PDF (ภ.พ. 30)", key="btn_pdf_vat_purchases", type="primary", use_container_width=True):
                    try:
                        from pdf.financial_reports_pdf import generate_vat_report_pdf
                        p_path = generate_vat_report_pdf("INPUT_PURCHASES", tax_purchases)
                        if p_path and os.path.exists(p_path):
                            with open(p_path, "rb") as fh:
                                st.session_state["pdf_bytes_vat_purchases"] = fh.read()
                            st.session_state["pdf_name_vat_purchases"] = os.path.basename(p_path)
                            st.success("✅ สร้างรายงานภาษีซื้อสำเร็จ")
                    except Exception as exc:
                        st.error(f"Failed: {exc}")

                if st.session_state.get("pdf_bytes_vat_purchases"):
                    st.download_button(
                        "⬇️ Download Input VAT PDF",
                        st.session_state["pdf_bytes_vat_purchases"],
                        file_name=st.session_state.get("pdf_name_vat_purchases", "Input_VAT_Report.pdf"),
                        mime="application/pdf",
                        key="dl_btn_vat_purchases_pdf",
                        use_container_width=True,
                    )

            with c_vp2:
                if tax_purchases:
                    st.download_button(
                        "📥 Export Input VAT CSV",
                        pd.DataFrame(tax_purchases).to_csv(index=False).encode('utf-8-sig'),
                        file_name="Input_VAT_Purchases.csv",
                        mime="text/csv",
                        key="dl_btn_vat_purchases_csv",
                        use_container_width=True,
                    )

    # 7. WITHHOLDING TAX REPORTS (ภ.ง.ด. 3 / ภ.ง.ด. 53 / 50 ทวิ)
    with tabs[6]:
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
                        "Payee Name (ผู้ถูกหัก)": v.get("vendor_name") or v.get("payee_name"),
                        "Tax ID (13 หลัก)": v.get("vendor_tax_id") or v.get("payee_tax_id", "—"),
                        "Payment Type": v.get("payment_type"),
                        "Base Amount (เงินได้ที่จ่าย)": _num(v.get("wht_base_amount") or v.get("subtotal")),
                        "Tax Deducted (ภาษีที่หัก)": _num(v.get("wht_tax_amount") or v.get("wht_total")),
                    })
            if wht_53:
                st.dataframe(pd.DataFrame(wht_53), hide_index=True, use_container_width=True)
            else:
                st.info("No WHT P.N.D. 53 records.")

            c_w1, c_w2 = st.columns(2)
            with c_w1:
                if st.button("🖨️ Export ภ.ง.ด. 53 Summary PDF", key="btn_pdf_wht_53", type="primary", use_container_width=True):
                    try:
                        from pdf.financial_reports_pdf import generate_wht_report_pdf
                        p_path = generate_wht_report_pdf("53", wht_53)
                        if p_path and os.path.exists(p_path):
                            with open(p_path, "rb") as fh:
                                st.session_state["pdf_bytes_wht_53"] = fh.read()
                            st.session_state["pdf_name_wht_53"] = os.path.basename(p_path)
                            st.success("✅ สร้างรายงาน ภ.ง.ด. 53 สำเร็จ")
                    except Exception as exc:
                        st.error(f"Failed: {exc}")

                if st.session_state.get("pdf_bytes_wht_53"):
                    st.download_button(
                        "⬇️ Download ภ.ง.ด. 53 PDF",
                        st.session_state["pdf_bytes_wht_53"],
                        file_name=st.session_state.get("pdf_name_wht_53", "WHT_PND_53.pdf"),
                        mime="application/pdf",
                        key="dl_btn_wht_53_pdf",
                        use_container_width=True,
                    )

            with c_w2:
                if wht_53:
                    st.download_button(
                        "📥 Export ภ.ง.ด. 53 CSV",
                        pd.DataFrame(wht_53).to_csv(index=False).encode('utf-8-sig'),
                        file_name="WHT_PND_53.csv",
                        mime="text/csv",
                        key="dl_btn_wht_53_csv",
                        use_container_width=True,
                    )

        with wht_sub2:
            st.markdown("##### 👤 รายงานภาษีหัก ณ ที่จ่าย ภ.ง.ด. 3 (จ่ายบุคคลธรรมดา)")
            wht_3 = []
            for v in ap_vouchers:
                if str(v.get("wht_pnd_type")) == "3" and _num(v.get("wht_total")) > 0:
                    wht_3.append({
                        "50 ทวิ No.": v.get("wht_cert_no") or f"WH-{v.get('id')}",
                        "Date": v.get("wht_cert_date") or v.get("invoice_date"),
                        "Payee Name": v.get("vendor_name") or v.get("payee_name"),
                        "Tax ID": v.get("vendor_tax_id") or v.get("payee_tax_id", "—"),
                        "Payment Type": v.get("payment_type"),
                        "Base Amount": _num(v.get("wht_base_amount") or v.get("subtotal")),
                        "Tax Deducted": _num(v.get("wht_tax_amount") or v.get("wht_total")),
                    })
            if wht_3:
                st.dataframe(pd.DataFrame(wht_3), hide_index=True, use_container_width=True)
            else:
                st.info("No WHT P.N.D. 3 records.")

            c_w3_1, c_w3_2 = st.columns(2)
            with c_w3_1:
                if st.button("🖨️ Export ภ.ง.ด. 3 Summary PDF", key="btn_pdf_wht_3", type="primary", use_container_width=True):
                    try:
                        from pdf.financial_reports_pdf import generate_wht_report_pdf
                        p_path = generate_wht_report_pdf("3", wht_3)
                        if p_path and os.path.exists(p_path):
                            with open(p_path, "rb") as fh:
                                st.session_state["pdf_bytes_wht_3"] = fh.read()
                            st.session_state["pdf_name_wht_3"] = os.path.basename(p_path)
                            st.success("✅ สร้างรายงาน ภ.ง.ด. 3 สำเร็จ")
                    except Exception as exc:
                        st.error(f"Failed: {exc}")

                if st.session_state.get("pdf_bytes_wht_3"):
                    st.download_button(
                        "⬇️ Download ภ.ง.ด. 3 PDF",
                        st.session_state["pdf_bytes_wht_3"],
                        file_name=st.session_state.get("pdf_name_wht_3", "WHT_PND_3.pdf"),
                        mime="application/pdf",
                        key="dl_btn_wht_3_pdf",
                        use_container_width=True,
                    )

            with c_w3_2:
                if wht_3:
                    st.download_button(
                        "📥 Export ภ.ง.ด. 3 CSV",
                        pd.DataFrame(wht_3).to_csv(index=False).encode('utf-8-sig'),
                        file_name="WHT_PND_3.csv",
                        mime="text/csv",
                        key="dl_btn_wht_3_csv",
                        use_container_width=True,
                    )

    # 8. CASH FLOW & LIQUIDITY
    with tabs[7]:
        st.markdown("#### 🌊 Cash Flow & Liquidity Analysis (รายงานกระแสเงินสดประจำวัน)")
        cf_date_input = st.date_input("Report Date (วันที่ออกรายงาน)", date.today(), key="cf_report_date_input")
        cf_date_str = cf_date_input.isoformat()

        # Inflows and Outflows for the selected date
        day_inflows = [r for r in invoices if str(r.get("issue_date", ""))[:10] == cf_date_str and str(r.get("status", "")).upper() != "CANCELLED"]
        day_outflows = [v for v in ap_vouchers if str(v.get("invoice_date", ""))[:10] == cf_date_str and v.get("status") not in ("CANCELLED", "REJECTED")]

        day_paid_inflow = sum(_num(r.get("net_payable") or r.get("grand_total") or r.get("amount")) for r in day_inflows)
        day_paid_outflow = sum(_num(v.get("net_payable") or v.get("total")) for v in day_outflows)
        day_net_realized = day_paid_inflow - day_paid_outflow

        # Total cumulative positions
        total_ap_payout = sum(float(v.get("net_payable") or v.get("total") or 0) for v in ap_vouchers if v.get("status") in ("POSTED", "PAID", "APPROVED"))
        total_ap_pending = sum(float(v.get("net_payable") or v.get("total") or 0) for v in ap_vouchers if v.get("status") not in ("PAID", "CANCELLED", "APPROVED"))
        
        net_cashflow_realized = paid - total_ap_payout
        net_cashflow_projected = billed - (total_ap_payout + total_ap_pending)
        
        cf1, cf2, cf3, cf4 = st.columns(4)
        cf1.metric("Cash Inflow (AR Collections)", _money(day_paid_inflow) + " THB", help=f"Cumulative Realized: {_money(paid)} THB")
        cf2.metric("Cash Outflow (AP Disbursements)", _money(day_paid_outflow) + " THB", help=f"Cumulative Realized: {_money(total_ap_payout)} THB")
        cf3.metric("Daily Net Realized", _money(day_net_realized) + " THB", help=f"Cumulative Net: {_money(net_cashflow_realized)} THB")
        cf4.metric("Projected Cumulative Net", _money(net_cashflow_projected) + " THB")
        
        st.markdown("##### 📊 Cash Inflow vs. Outflow Summary")
        cf_summary = [
            {"Category": f"Daily AR Collections ({cf_date_str})", "Amount (THB)": _money(day_paid_inflow), "Status": "Daily Inflow"},
            {"Category": f"Daily AP Disbursements ({cf_date_str})", "Amount (THB)": _money(day_paid_outflow), "Status": "Daily Outflow"},
            {"Category": "AR Outstanding (ยอดลูกหนี้รอเรียกเก็บทั้งหมด)", "Amount (THB)": _money(outstanding), "Status": "Pending Inflow"},
            {"Category": "AP Pending (ยอดเจ้าหนี้รอเบิกจ่ายทั้งหมด)", "Amount (THB)": _money(total_ap_pending), "Status": "Pending Outflow"},
            {"Category": "Cumulative Net Cash (กระแสเงินสดสุทธิสะสม)", "Amount (THB)": _money(net_cashflow_realized), "Status": "Net Liquidity"},
        ]
        st.dataframe(pd.DataFrame(cf_summary), use_container_width=True, hide_index=True)

        cf_btn1, cf_btn2 = st.columns(2)
        with cf_btn1:
            if st.button("🖨️ Export Daily Cash Flow PDF Report", key="btn_pdf_daily_cf", type="primary", use_container_width=True):
                try:
                    from pdf.financial_reports_pdf import generate_daily_cashflow_pdf
                    cf_metrics = {
                        "inflow": day_paid_inflow,
                        "outflow": day_paid_outflow,
                        "net_realized": day_net_realized,
                        "projected": net_cashflow_projected
                    }
                    p_path = generate_daily_cashflow_pdf(cf_date_str, cf_metrics, day_inflows, day_outflows)
                    if p_path and os.path.exists(p_path):
                        with open(p_path, "rb") as fh:
                            st.session_state[f"pdf_bytes_cf_{cf_date_str}"] = fh.read()
                        st.session_state[f"pdf_name_cf_{cf_date_str}"] = os.path.basename(p_path)
                        st.success("✅ สร้างรายงานกระแสเงินสด PDF สำเร็จ")
                except Exception as exc:
                    st.error(f"Failed to generate Cash Flow PDF: {exc}")

            if st.session_state.get(f"pdf_bytes_cf_{cf_date_str}"):
                st.download_button(
                    "⬇️ Download Daily Cash Flow PDF",
                    st.session_state[f"pdf_bytes_cf_{cf_date_str}"],
                    file_name=st.session_state.get(f"pdf_name_cf_{cf_date_str}", f"CashFlow_{cf_date_str}.pdf"),
                    mime="application/pdf",
                    key="dl_btn_cf_pdf",
                    use_container_width=True,
                )

        with cf_btn2:
            st.download_button(
                "📥 Export Cash Flow Summary CSV",
                pd.DataFrame(cf_summary).to_csv(index=False).encode('utf-8-sig'),
                file_name=f"CashFlow_Summary_{cf_date_str}.csv",
                mime="text/csv",
                key="dl_btn_cf_csv",
                use_container_width=True,
            )

