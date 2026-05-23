"""Billing / Financial module view.

Per-row tax control:
- VAT 7% / Non-VAT / Advance (เงินทดรองจ่าย)
- WHT None / 1% / 3%

Summary structure (7 lines):
1. Total Before VAT
2. Total VAT 7%
3. Total Advance
4. Total Before WHT
5. WHT 1% Amount
6. WHT 3% Amount
7. Grand Total
"""
import streamlit as st
import pandas as pd
import uuid
from datetime import date, timedelta
from managers.invoice_manager import (
    create_invoice, get_invoice_by_no, list_invoices,
    record_payment, cancel_invoice, get_outstanding_summary,
    calculate_summary, TAX_TYPES, WHT_TYPES,
)
from managers.customer_manager import list_customers, get_customer
from managers.shipment_manager import list_shipments, get_shipment
from managers.auth_manager import can_write


DOC_TYPES = {
    "INV": "📄 Invoice",
    "BN": "📑 Billing Note (ใบวางบิล)",
    "CN": "📉 Credit Note",
    "DN": "📈 Debit Note",
    "SOA": "📊 Statement of Account",
}


def render():
    user = st.session_state.get("user", {})
    role = user.get("role", "")
    can_edit = can_write(role, "billing")
    
    st.title("💰 Billing & Financial")
    st.caption("Per-row VAT/Advance/WHT · Auto financial breakdown")
    
    # ===== KPI Strip =====
    summary = get_outstanding_summary()
    k1, k2, k3 = st.columns(3)
    with k1:
        st.metric("Total Billed", f"฿{summary['billed']:,.0f}")
    with k2:
        st.metric("Total Paid", f"฿{summary['paid']:,.0f}")
    with k3:
        st.metric("Outstanding", f"฿{summary['outstanding']:,.0f}",
                  delta_color="inverse")
    
    st.markdown("---")
    
    tabs = ["📋 All Documents", "💳 Record Payment"]
    if can_edit:
        tabs.insert(0, "➕ Create Document")
    
    tab_objs = st.tabs(tabs)
    
    if can_edit:
        with tab_objs[0]:
            _create_form(user)
        with tab_objs[1]:
            _list_view()
        with tab_objs[2]:
            _payment_view()
    else:
        with tab_objs[0]:
            _list_view()
        with tab_objs[1]:
            st.info("⚠️ You have read-only access to billing.")


def _empty_inv_row():
    return {
        "id": str(uuid.uuid4())[:8],
        "description": "",
        "quantity": 1.0,
        "unit_price": 0.0,
        "amount": 0.0,
        "tax_type": "VAT 7%",
        "wht_type": "None",
    }


def _create_form(user):
    st.subheader("Create New Financial Document")
    
    doc_type = st.selectbox("Document Type *",
        options=list(DOC_TYPES.keys()),
        format_func=lambda k: DOC_TYPES[k])
    
    col1, col2 = st.columns(2)
    with col1:
        customers = list_customers()
        cust_options = [(0, "-- Select customer --")] + \
                       [(c["id"], c["company_name"]) for c in customers]
        cust_idx = st.selectbox("Customer *",
            range(len(cust_options)),
            format_func=lambda i: cust_options[i][1],
            key="bill_cust")
        cust_id = cust_options[cust_idx][0]
        cust_name = cust_options[cust_idx][1] if cust_idx > 0 else ""
        
        cust_data = get_customer(cust_id) if cust_id else None
        credit_terms = cust_data.get("credit_terms_days", 30) if cust_data else 30
        
        ships = list_shipments()
        ship_options = [("", "-- No linked shipment --")] + \
                       [(s["job_no"], f"{s['job_no']} — {s.get('customer_name','')}")
                        for s in ships[:100]]
        ship_idx = st.selectbox("Link to Shipment (optional)",
            range(len(ship_options)),
            format_func=lambda i: ship_options[i][1],
            key="bill_ship")
        job_no = ship_options[ship_idx][0]
    
    with col2:
        issue_date = st.date_input("Issue Date *", value=date.today(),
                                    key="bill_issue")
        due_date = st.date_input("Due Date",
            value=date.today() + timedelta(days=int(credit_terms)),
            key="bill_due")
        currency = st.selectbox("Currency",
            ["THB", "USD", "EUR", "CNY"], key="bill_currency")
        ref_doc = st.text_input("Reference Doc No. (for CN/DN)",
                                  key="bill_ref")
    
    # ===== ITEMS EDITOR with per-row VAT/WHT =====
    st.markdown("##### 📝 Line Items")
    st.caption("เลือก VAT/Advance และ WHT แยกแต่ละบรรทัด · Advance = เงินทดรองจ่าย ไม่คิด VAT/WHT")
    
    items_key = "bill_items_list"
    if items_key not in st.session_state:
        st.session_state[items_key] = [_empty_inv_row()]
    
    items = st.session_state[items_key]
    for it in items:
        if not it.get("id"):
            it["id"] = str(uuid.uuid4())[:8]
    
    def _sync_inv_widgets():
        for row in st.session_state[items_key]:
            rid = row["id"]
            for field, suffix in [
                ("description", "d"), ("quantity", "q"),
                ("unit_price", "u"), ("tax_type", "tax"),
                ("wht_type", "wht"),
            ]:
                wkey = f"bi_{suffix}_{rid}"
                if wkey in st.session_state:
                    row[field] = st.session_state[wkey]
            # Recalc amount = qty * unit_price
            row["amount"] = float(row["quantity"]) * float(row["unit_price"])
    
    # Header
    h = st.columns([3, 0.8, 1.1, 1.1, 1.3, 1.1, 0.4])
    h[0].markdown("**Description**")
    h[1].markdown("<div style='text-align:center'><b>Qty</b></div>",
                  unsafe_allow_html=True)
    h[2].markdown("<div style='text-align:center'><b>Unit Price</b></div>",
                  unsafe_allow_html=True)
    h[3].markdown("<div style='text-align:center'><b>Amount</b></div>",
                  unsafe_allow_html=True)
    h[4].markdown("<div style='text-align:center'><b>VAT/Advance</b></div>",
                  unsafe_allow_html=True)
    h[5].markdown("<div style='text-align:center'><b>WHT</b></div>",
                  unsafe_allow_html=True)
    h[6].markdown("**🗑**")
    
    delete_id = None
    
    for row in items:
        rid = row["id"]
        c = st.columns([3, 0.8, 1.1, 1.1, 1.3, 1.1, 0.4])
        c[0].text_input("d", value=row["description"], key=f"bi_d_{rid}",
                          label_visibility="collapsed")
        c[1].number_input("q", value=float(row["quantity"]),
                            min_value=0.0, step=1.0, key=f"bi_q_{rid}",
                            label_visibility="collapsed")
        c[2].number_input("u", value=float(row["unit_price"]),
                            min_value=0.0, format="%.2f", key=f"bi_u_{rid}",
                            label_visibility="collapsed")
        # Live amount preview
        amt = float(st.session_state.get(f"bi_q_{rid}", row["quantity"])) * \
              float(st.session_state.get(f"bi_u_{rid}", row["unit_price"]))
        c[3].markdown(
            f"<div style='padding:0.4rem;text-align:right;font-family:monospace'>"
            f"฿{amt:,.2f}</div>",
            unsafe_allow_html=True)
        c[4].selectbox("tax", TAX_TYPES,
            index=TAX_TYPES.index(row.get("tax_type", "VAT 7%"))
                if row.get("tax_type") in TAX_TYPES else 0,
            key=f"bi_tax_{rid}", label_visibility="collapsed")
        c[5].selectbox("wht", WHT_TYPES,
            index=WHT_TYPES.index(row.get("wht_type", "None"))
                if row.get("wht_type") in WHT_TYPES else 0,
            key=f"bi_wht_{rid}", label_visibility="collapsed")
        if c[6].button("🗑", key=f"bi_del_{rid}",
                        disabled=(len(items) <= 1), help="ลบรายการ"):
            delete_id = rid
    
    if delete_id:
        _sync_inv_widgets()
        st.session_state[items_key] = [
            r for r in st.session_state[items_key] if r["id"] != delete_id
        ]
        st.rerun()
    
    if st.button("➕ Add line item", key="bi_add"):
        _sync_inv_widgets()
        st.session_state[items_key].append(_empty_inv_row())
        st.rerun()
    
    # Sync before computing summary
    _sync_inv_widgets()
    items = st.session_state[items_key]
    summary = calculate_summary(items)
    
    sym = "฿" if currency == "THB" else (currency + " ")
    
    # ===== 7-LINE FINANCIAL BREAKDOWN =====
    st.markdown("##### 💸 Financial Summary")
    st.markdown(f"""
    <div style="background:#101113;border:1px solid #23252B;border-radius:8px;
                padding:1rem;margin:0.5rem 0;font-family:monospace">
        <div style="display:flex;justify-content:space-between;margin:0.25rem 0">
            <span>1. Total Before VAT</span>
            <span>{sym}{summary['total_before_vat']:,.2f}</span></div>
        <div style="display:flex;justify-content:space-between;margin:0.25rem 0">
            <span>2. Total VAT 7%</span>
            <span>{sym}{summary['total_vat_7']:,.2f}</span></div>
        <div style="display:flex;justify-content:space-between;margin:0.25rem 0;
                    color:#A855F7">
            <span>3. Total Advance (เงินทดรองจ่าย)</span>
            <span>{sym}{summary['total_advance']:,.2f}</span></div>
        <hr style="border-color:#23252B;margin:6px 0">
        <div style="display:flex;justify-content:space-between;margin:0.25rem 0;
                    color:#9CA0A8">
            <span>4. Total Before WHT</span>
            <span>{sym}{summary['total_before_wht']:,.2f}</span></div>
        <div style="display:flex;justify-content:space-between;margin:0.25rem 0;
                    color:#E5484D">
            <span>5. WHT 1% Amount</span>
            <span>-{sym}{summary['wht_1_amount']:,.2f}</span></div>
        <div style="display:flex;justify-content:space-between;margin:0.25rem 0;
                    color:#E5484D">
            <span>6. WHT 3% Amount</span>
            <span>-{sym}{summary['wht_3_amount']:,.2f}</span></div>
        <hr style="border-color:#23252B;margin:6px 0">
        <div style="display:flex;justify-content:space-between;
                    font-size:1.2rem;font-weight:600;color:#26B574">
            <span>7. GRAND TOTAL</span>
            <span>{sym}{summary['grand_total']:,.2f}</span></div>
    </div>
    """, unsafe_allow_html=True)
    
    remark = st.text_area("Remark", key="bill_remark", height=80)
    
    if st.button("🚀 Issue Document", type="primary", use_container_width=True):
        if cust_id == 0:
            st.error("Please select a customer")
        elif not [i for i in items if i["description"].strip()]:
            st.error("Please add at least one line item")
        else:
            try:
                valid_items = [i for i in items if i["description"].strip()]
                doc_no = create_invoice(
                    {
                        "doc_type": doc_type,
                        "shipment_id": None,
                        "job_no": job_no or None,
                        "customer_id": cust_id,
                        "customer_name": cust_name,
                        "issue_date": issue_date.isoformat(),
                        "due_date": due_date.isoformat(),
                        "currency": currency,
                        "ref_doc_no": ref_doc,
                        "remark": remark,
                        "credit_terms_days": int(credit_terms),
                        "created_by": user.get("username", ""),
                    },
                    valid_items
                )
                st.success(f"✅ Created **{doc_no}**")
                # Clear items
                if items_key in st.session_state:
                    del st.session_state[items_key]
                st.rerun()
            except Exception as ex:
                st.error(f"Failed: {ex}")


def _list_view():
    st.subheader("All Financial Documents")
    
    fc1, fc2, fc3 = st.columns(3)
    with fc1:
        f_type = st.selectbox("Document Type",
            ["All"] + list(DOC_TYPES.keys()),
            format_func=lambda k: "All" if k == "All" else DOC_TYPES.get(k, k),
            key="bill_filter_type")
    with fc2:
        f_status = st.selectbox("Payment Status",
            ["All", "Unpaid", "Partial", "Paid", "Cancelled"],
            key="bill_filter_status")
    with fc3:
        st.write(""); st.write("")
        st.button("🔄 Refresh", key="bill_refresh", use_container_width=True)
    
    rows = list_invoices(
        doc_type=None if f_type == "All" else f_type,
        payment_status=None if f_status == "All" else f_status,
    )
    
    if not rows:
        st.info("No documents found.")
        return
    
    df = pd.DataFrame(rows)
    display_cols = ["doc_no", "doc_type", "customer_name", "issue_date",
                    "due_date", "total_amount", "paid_amount", "outstanding",
                    "payment_status"]
    display_cols = [c for c in display_cols if c in df.columns]
    st.dataframe(df[display_cols], use_container_width=True,
                 hide_index=True, height=400,
                 column_config={
                     "doc_no": "Doc No.",
                     "doc_type": "Type",
                     "customer_name": "Customer",
                     "issue_date": "Issue",
                     "due_date": "Due",
                     "total_amount": st.column_config.NumberColumn(
                         "Total", format="฿%.2f"),
                     "paid_amount": st.column_config.NumberColumn(
                         "Paid", format="฿%.2f"),
                     "outstanding": st.column_config.NumberColumn(
                         "Outstanding", format="฿%.2f"),
                     "payment_status": "Status",
                 })
    
    col_csv, col_pdf = st.columns([1, 2])
    with col_csv:
        csv = df[display_cols].to_csv(index=False).encode("utf-8-sig")
        st.download_button("📥 Export CSV", data=csv,
            file_name="financial_documents.csv", mime="text/csv",
            use_container_width=True, key="bill_csv")
    
    st.markdown("---")
    st.markdown("##### 📄 Generate Document PDF")
    options = [r["doc_no"] for r in rows]
    sel = st.selectbox("Select document",
        options, key="bill_pdf_sel",
        format_func=lambda x: f"{x} — {next((r.get('customer_name','') for r in rows if r['doc_no']==x), '')}")
    
    if st.button("📥 Generate PDF", type="primary", key="bill_pdf_btn"):
        try:
            from pdf.invoice_pdf import generate_invoice_pdf
            inv = get_invoice_by_no(sel)
            if inv:
                cust = get_customer(inv.get("customer_id")) if inv.get("customer_id") else None
                pdf_path = generate_invoice_pdf(inv, customer=cust)
                with open(pdf_path, "rb") as f:
                    st.download_button(
                        f"📥 Download {sel}.pdf", f.read(),
                        f"{sel}.pdf", "application/pdf",
                        type="primary", key="bill_pdf_dl")
                st.success(f"PDF generated for {sel}")
        except Exception as ex:
            st.error(f"PDF generation failed: {ex}")


def _payment_view():
    st.subheader("Record Payment")
    unpaid = list_invoices(doc_type="INV", payment_status="Unpaid") + \
             list_invoices(doc_type="INV", payment_status="Partial")
    if not unpaid:
        st.info("No unpaid invoices.")
        return
    
    options = [f"{i['doc_no']} — {i.get('customer_name','')} "
               f"(Outstanding: ฿{i.get('outstanding', 0):,.2f})"
               for i in unpaid]
    sel_idx = st.selectbox("Select invoice", range(len(options)),
                            format_func=lambda i: options[i])
    sel_inv = unpaid[sel_idx]
    
    c1, c2 = st.columns(2)
    with c1:
        amount = st.number_input("Payment Amount (฿)",
            min_value=0.01, value=float(sel_inv.get("outstanding", 0)),
            format="%.2f")
    with c2:
        pay_date = st.date_input("Payment Date", value=date.today())
    
    if st.button("💳 Record Payment", type="primary"):
        if record_payment(sel_inv["doc_no"], amount, pay_date.isoformat()):
            st.success(f"✅ Payment of ฿{amount:,.2f} recorded for {sel_inv['doc_no']}")
            st.rerun()
        else:
            st.error("Failed to record payment")
