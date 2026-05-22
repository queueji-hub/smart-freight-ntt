"""Billing / Financial module view."""
import streamlit as st
import pandas as pd
from datetime import date, timedelta
from managers.invoice_manager import (
    create_invoice, get_invoice_by_no, list_invoices,
    record_payment, cancel_invoice, get_outstanding_summary,
    calculate_totals,
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
    st.caption("Invoice · Billing Note · Credit/Debit Note · SOA · Payment Tracking")
    
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


def _create_form(user):
    st.subheader("Create New Financial Document")
    
    doc_type = st.selectbox("Document Type *",
        options=list(DOC_TYPES.keys()),
        format_func=lambda k: DOC_TYPES[k])
    
    col1, col2 = st.columns(2)
    with col1:
        # Customer selection
        customers = list_customers()
        cust_options = [(0, "-- Select customer --")] + \
                       [(c["id"], c["company_name"]) for c in customers]
        cust_idx = st.selectbox("Customer *",
            range(len(cust_options)),
            format_func=lambda i: cust_options[i][1],
            key="bill_cust")
        cust_id = cust_options[cust_idx][0]
        cust_name = cust_options[cust_idx][1] if cust_idx > 0 else ""
        
        # Auto-fill from customer
        cust_data = get_customer(cust_id) if cust_id else None
        credit_terms = cust_data.get("credit_terms_days", 30) if cust_data else 30
        
        # Pull from shipment
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
    
    # Items editor
    st.markdown("##### 📝 Line Items")
    items_key = "bill_items_list"
    if items_key not in st.session_state:
        st.session_state[items_key] = [
            {"description": "", "quantity": 1.0, "unit_price": 0.0, "amount": 0.0}
        ]
    
    items = st.session_state[items_key]
    h = st.columns([3, 1, 1.2, 1.2, 0.5])
    h[0].markdown("**Description**")
    h[1].markdown("**Qty**")
    h[2].markdown("**Unit Price**")
    h[3].markdown("**Amount**")
    h[4].markdown("**🗑**")
    
    for i in range(len(items)):
        c = st.columns([3, 1, 1.2, 1.2, 0.5])
        items[i]["description"] = c[0].text_input("d",
            value=items[i]["description"], key=f"bi_d_{i}",
            label_visibility="collapsed")
        items[i]["quantity"] = c[1].number_input("q",
            value=float(items[i]["quantity"]), min_value=0.0, step=1.0,
            key=f"bi_q_{i}", label_visibility="collapsed")
        items[i]["unit_price"] = c[2].number_input("u",
            value=float(items[i]["unit_price"]), min_value=0.0,
            format="%.2f", key=f"bi_u_{i}", label_visibility="collapsed")
        # Auto-calc amount
        amt = items[i]["quantity"] * items[i]["unit_price"]
        items[i]["amount"] = amt
        c[3].markdown(f"<div style='padding:0.4rem'>฿{amt:,.2f}</div>",
                      unsafe_allow_html=True)
        if c[4].button("🗑", key=f"bi_del_{i}", disabled=(len(items) <= 1)):
            items.pop(i)
            st.rerun()
    
    if st.button("➕ Add line item"):
        items.append({"description": "", "quantity": 1.0,
                      "unit_price": 0.0, "amount": 0.0})
        st.rerun()
    
    # Tax settings
    st.markdown("##### 💸 Tax")
    t1, t2 = st.columns(2)
    with t1:
        vat_rate = st.number_input("VAT Rate (%)", min_value=0.0,
            max_value=20.0, value=7.0, step=0.5, key="bill_vat")
    with t2:
        wht_rate = st.selectbox("WHT Rate (%)",
            [0.0, 1.0, 3.0, 5.0], index=0, key="bill_wht")
    
    # Live totals preview
    totals = calculate_totals(items, vat_rate=vat_rate, wht_rate=wht_rate)
    st.markdown(f"""
    <div style="background:#101113;border:1px solid #23252B;border-radius:8px;
                padding:1rem;margin:1rem 0">
        <div style="display:flex;justify-content:space-between;margin:0.25rem 0">
            <span>Subtotal</span><span>฿{totals['subtotal']:,.2f}</span></div>
        <div style="display:flex;justify-content:space-between;margin:0.25rem 0">
            <span>VAT ({vat_rate}%)</span>
            <span>฿{totals['vat_amount']:,.2f}</span></div>
        <div style="display:flex;justify-content:space-between;margin:0.25rem 0;
                    color:#E5484D">
            <span>WHT ({wht_rate}%)</span>
            <span>-฿{totals['wht_amount']:,.2f}</span></div>
        <hr style="border-color:#23252B">
        <div style="display:flex;justify-content:space-between;
                    font-size:1.2rem;font-weight:600">
            <span>Net Total</span><span>฿{totals['total_amount']:,.2f}</span></div>
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
                        "vat_rate": vat_rate,
                        "wht_rate": wht_rate,
                        "ref_doc_no": ref_doc,
                        "remark": remark,
                        "credit_terms_days": int(credit_terms),
                        "created_by": user.get("username", ""),
                    },
                    valid_items
                )
                st.success(f"✅ Created **{doc_no}**")
                # Clear items
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
                 hide_index=True, height=500,
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
    
    csv = df[display_cols].to_csv(index=False).encode("utf-8-sig")
    st.download_button("📥 Export CSV", data=csv,
        file_name="financial_documents.csv", mime="text/csv")


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
