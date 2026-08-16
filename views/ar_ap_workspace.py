"""AR/AP operational workspace built on the existing Finance SSOT."""
from __future__ import annotations
import pandas as pd
import streamlit as st
from managers.invoice_manager import list_invoices, record_payment
from managers.auth_manager import can_write
from ui.design_system import page_header, section


def _money(v):
    try: return f"{float(v or 0):,.2f}"
    except Exception: return "0.00"


def render():
    page_header("billing", status_text="Online")
    user=st.session_state.get("user",{})
    writable=can_write(str(user.get("role","")).lower(),"billing")
    rows=list_invoices() or []
    ar=[r for r in rows if str(r.get("status","")).upper() not in {"CANCELLED"}]
    total=sum(float(r.get("grand_total",0) or 0) for r in ar)
    outstanding=sum(float(r.get("outstanding",0) or 0) for r in ar)
    paid=total-outstanding
    a,b,c=st.columns(3);a.metric("AR Billed",_money(total));b.metric("AR Paid",_money(paid));c.metric("AR Outstanding",_money(outstanding))
    tabs=st.tabs(["AR Aging","SOA View","Payment Register"])
    with tabs[0]:
        section("Accounts Receivable"); q=st.text_input("Customer / Document / Job / B/L",key="ar_search")
        view=ar
        if q.strip(): view=[r for r in view if q.strip().lower() in str(r).lower()]
        st.dataframe(pd.DataFrame([{"Document":r.get("doc_no"),"Customer":r.get("customer_name"),"Issue":r.get("issue_date"),"Due":r.get("due_date"),"Total":r.get("grand_total"),"Outstanding":r.get("outstanding"),"Status":r.get("status")} for r in view]),hide_index=True,width="stretch")
    with tabs[1]:
        section("Statement of Account (SOA)")
        customers=sorted({str(r.get("customer_name")) for r in ar if r.get("customer_name")})
        customer=st.selectbox("Customer",customers,key="soa_customer") if customers else None
        if customer:
            view=[r for r in ar if r.get("customer_name")==customer]
            st.dataframe(pd.DataFrame([{"Document":r.get("doc_no"),"Date":r.get("issue_date"),"Due":r.get("due_date"),"Debit":r.get("grand_total"),"Credit":0,"Balance":r.get("outstanding")} for r in view]),hide_index=True,width="stretch")
            st.metric("Customer Outstanding",_money(sum(float(r.get("outstanding",0) or 0) for r in view)))
    with tabs[2]:
        section("Payment Register")
        outstanding_rows=[r for r in ar if float(r.get("outstanding",0) or 0)>0]
        if not writable: st.info("Payment entry requires billing write permission.")
        elif not outstanding_rows: st.success("No outstanding AR documents.")
        else:
            selected=st.selectbox("Document",range(len(outstanding_rows)),format_func=lambda i:f"{outstanding_rows[i].get('doc_no')} · {outstanding_rows[i].get('customer_name')}",key="ar_payment_doc")
            r=outstanding_rows[selected]; amount=st.number_input("Amount",min_value=.01,value=float(r.get("outstanding",0)),key="ar_payment_amount"); method=st.selectbox("Method",["Bank Transfer","Cash","Cheque","Credit Card"],key="ar_payment_method"); ref=st.text_input("Reference",key="ar_payment_ref")
            if st.button("Record Payment",type="primary",key="ar_record_payment"):
                record_payment({"doc_no":r.get("doc_no"),"amount":amount,"method":method,"reference":ref.strip()});st.success("Payment recorded.");st.rerun()
