"""Production Finance workspace aligned to NATTAYARAAT billing references."""
from __future__ import annotations
import os
from datetime import date, timedelta
from typing import Any, Dict, List
import pandas as pd
import streamlit as st
from managers.auth_manager import can_write
from managers.charge_master_manager import list_charges
from managers.customer_manager import list_customers
from managers.document_approval_manager import approve_document, can_approve, get_approval_status, submit_for_approval
from managers.document_duplicate_service import duplicate_invoice, get_invoice_snapshot, update_invoice_draft
from managers.invoice_manager import TAX_TYPES, WHT_TYPES, create_invoice, list_invoices, record_payment, calculate_summary
from managers.shipment_manager import list_shipments
from ui.design_system import page_header, section

CURRENCIES=["THB","USD","EUR","CNY"]
PAYMENT_METHODS=["Bank Transfer","Cash","Cheque","Credit Card"]
DOC_TYPES={"INV":"Receipt / Tax Invoice","BN":"Billing Note","CN":"Credit Note","DN":"Debit Note","SOA":"Statement of Account"}

def _status(doc_no:str,fallback:str="Draft")->str:
    try:return get_approval_status("invoice",doc_no)
    except Exception:return fallback or "Draft"

def _pdf(doc_no:str)->None:
    k=f"fin_v2_{doc_no}"
    if st.button("PDF",key=f"{k}_make",type="primary",width="stretch"):
        try:
            from pdf.invoice_pdf import generate_invoice_pdf
            inv,items=get_invoice_snapshot(doc_no); status=_status(doc_no,inv.get("status")); path=generate_invoice_pdf({**inv,"items":items,"approval_status":status,"status":status})
            if not path or not os.path.exists(path):raise FileNotFoundError("Invoice PDF generator returned no file.")
            with open(path,"rb") as fh:st.session_state[f"{k}_bytes"]=fh.read()
            st.session_state[f"{k}_name"]=os.path.basename(path)
        except Exception as exc:st.error(f"Unable to create PDF: {exc}")
    if st.session_state.get(f"{k}_bytes"):st.download_button("Download",st.session_state[f"{k}_bytes"],file_name=st.session_state.get(f"{k}_name",f"{doc_no}.pdf"),mime="application/pdf",key=f"{k}_dl",width="stretch")

def _customer_card(customer:Dict[str,Any]|None)->None:
    if not customer:return
    section("Customer Snapshot")
    a,b=st.columns(2)
    a.markdown(f"**{customer.get('company_name','—')}**\n\nTax ID: {customer.get('tax_id') or '—'}\n\nContact: {customer.get('contact_person') or '—'}")
    b.markdown(f"**Billing Address**\n\n{customer.get('address') or '—'}\n\nTel: {customer.get('tel') or '—'} · Email: {customer.get('email') or '—'}")

def _new(user:Dict[str,Any])->None:
    customers=list_customers() or []; cmap={int(c["id"]):c for c in customers if c.get("id")}; jobs=list_shipments(limit=200) or []; jmap={j.get("job_no"):j for j in jobs if j.get("job_no")}; charges=list_charges() or []; cmap2={c.get("code"):c for c in charges if c.get("code")}
    section("New Financial Document")
    with st.form("finance_v2_new"):
        a,b,c=st.columns(3); typ=a.selectbox("Document",list(DOC_TYPES),format_func=lambda x:DOC_TYPES[x]); cid=b.selectbox("Customer",list(cmap),format_func=lambda x:cmap[x].get("company_name",str(x)) if cmap else "—"); job=c.selectbox("Linked Job",[""]+list(jmap))
        customer=cmap.get(cid) if cid else None
        if customer:
            st.caption(f"Customer Tax ID: {customer.get('tax_id') or '—'} · Address loaded from Customer Master")
        a,b,c=st.columns(3); issue=a.date_input("Issue Date",date.today()); due=b.date_input("Due Date",date.today()+timedelta(days=30)); currency=c.selectbox("Currency",CURRENCIES)
        ref=st.text_input("Reference / B/L / Job Reference",value=job or "")
        section("Charge Lines")
        if "finance_v2_items" not in st.session_state:st.session_state["finance_v2_items"]=[{"code":"","quantity":1.0,"unit_price":0.0,"tax":TAX_TYPES[0],"wht":WHT_TYPES[0] if WHT_TYPES else "None"}]
        items=[]
        for i,row in enumerate(st.session_state["finance_v2_items"]):
            a,b,c,d,e=st.columns([4,1,1.5,1.2,1.2]); codes=[""]+list(cmap2); code=a.selectbox("Charge",codes,index=codes.index(row.get("code","")) if row.get("code","") in codes else 0,format_func=lambda x:f"{x} — {cmap2[x].get('description','')}" if x else "Select charge",key=f"fin_code_{i}"); qty=b.number_input("Qty",min_value=.01,value=float(row.get("quantity",1)),key=f"fin_qty_{i}"); rate=c.number_input("Unit Price",min_value=0.0,value=float(row.get("unit_price",0)),step=100.0,key=f"fin_rate_{i}"); tax=d.selectbox("VAT",TAX_TYPES,index=TAX_TYPES.index(row.get("tax")) if row.get("tax") in TAX_TYPES else 0,key=f"fin_tax_{i}"); wht=e.selectbox("WHT",WHT_TYPES,index=WHT_TYPES.index(row.get("wht")) if row.get("wht") in WHT_TYPES else 0,key=f"fin_wht_{i}")
            desc=cmap2.get(code,{}).get("description","") if code else ""; items.append({"description":desc,"quantity":qty,"unit_price":rate,"tax_type":tax,"wht_type":wht})
        remark=st.text_area("Remarks / Payment Terms",placeholder="Example: Payment within 30 days from invoice date.")
        save=st.form_submit_button("Create Draft",type="primary",width="stretch")
    summary=calculate_summary(items); st.markdown(f"**Preview Total:** {float(summary['grand_total']):,.2f} {currency} · VAT {float(summary['total_vat_7']):,.2f} · WHT {float(summary['wht_total']):,.2f}")
    if save:
        if not cid:st.error("Customer is required.");return
        if not any(x["description"] and x["unit_price"]>0 for x in items):st.error("Select at least one charge and enter a positive rate.");return
        try:
            doc=create_invoice({"doc_type":typ,"job_no":job or None,"customer_id":cid,"customer_name":customer.get("company_name") if customer else None,"issue_date":issue.isoformat(),"due_date":due.isoformat(),"currency":currency,"ref_doc_no":ref.strip(),"remark":remark.strip(),"created_by":user.get("username","system"),"status":"DRAFT"},items)
            st.session_state["finance_v2_items"]=[{"code":"","quantity":1.0,"unit_price":0.0,"tax":TAX_TYPES[0],"wht":WHT_TYPES[0] if WHT_TYPES else "None"}];st.success(f"Created {doc} as Draft.");st.rerun()
        except Exception as exc:st.error(f"Unable to create document: {exc}")

def _edit(doc_no:str)->None:
    inv,items=get_invoice_snapshot(doc_no)
    if _status(doc_no,inv.get("status"))!="Draft":st.info("Only Draft documents can be edited.");return
    customers=list_customers() or []; cmap={int(c["id"]):c.get("company_name",str(c["id"])) for c in customers if c.get("id")}; current=inv.get("customer_id")
    if current not in cmap:st.error("Customer master data is missing.");return
    with st.expander(f"Edit {doc_no}",expanded=True):
        with st.form(f"finance_edit_{doc_no}"):
            a,b=st.columns(2);cid=a.selectbox("Customer",list(cmap),index=list(cmap).index(current),format_func=lambda x:cmap[x]);job=b.text_input("Linked Job",str(inv.get("job_no") or ""));a,b,c=st.columns(3);issue=a.date_input("Issue Date",inv.get("issue_date") or date.today());due=b.date_input("Due Date",inv.get("due_date") or date.today());currency=c.selectbox("Currency",CURRENCIES,index=CURRENCIES.index(inv.get("currency","THB")) if inv.get("currency","THB") in CURRENCIES else 0);ref=st.text_input("Reference / B/L",str(inv.get("ref_doc_no") or ""));clean=[]
            for i,item in enumerate(items):
                a,b,c,d,e=st.columns([4,1,1.5,1.2,1.2]);desc=a.text_input("Description",str(item.get("description") or ""),key=f"ed_{doc_no}_{i}");qty=b.number_input("Qty",min_value=.01,value=float(item.get("quantity") or 1),key=f"eq_{doc_no}_{i}");rate=c.number_input("Unit Price",min_value=0.0,value=float(item.get("unit_price") or 0),key=f"er_{doc_no}_{i}");tax=d.selectbox("VAT",TAX_TYPES,index=TAX_TYPES.index(item.get("tax_type")) if item.get("tax_type") in TAX_TYPES else 0,key=f"et_{doc_no}_{i}");wht=e.selectbox("WHT",WHT_TYPES,index=WHT_TYPES.index(item.get("wht_type")) if item.get("wht_type") in WHT_TYPES else 0,key=f"ew_{doc_no}_{i}");clean.append({"description":desc,"quantity":qty,"unit_price":rate,"tax_type":tax,"wht_type":wht})
            save=st.form_submit_button("Save Changes",type="primary",width="stretch")
        if save:
            try:update_invoice_draft(doc_no,{"customer_id":cid,"job_no":job or None,"issue_date":issue.isoformat(),"due_date":due.isoformat(),"currency":currency,"ref_doc_no":ref.strip()},clean);st.success("Document updated.");st.rerun()
            except Exception as exc:st.error(f"Update failed: {exc}")

def _payments()->None:
    section("Payments");rows=[r for r in(list_invoices() or []) if str(r.get("status","")).upper() not in {"PAID","CANCELLED"}]
    if not rows:st.info("No outstanding documents.");return
    i=st.selectbox("Outstanding document",range(len(rows)),format_func=lambda x:f"{rows[x].get('doc_no')} · {rows[x].get('customer_name','')} · {float(rows[x].get('outstanding',rows[x].get('grand_total',0)) or 0):,.2f} {rows[x].get('currency','THB')}",key="finance_pay_doc");r=rows[i];a,b=st.columns(2);amount=a.number_input("Payment Amount",min_value=.01,value=float(r.get("outstanding",r.get("grand_total",0)) or 0),key="finance_pay_amount");method=b.selectbox("Payment Method",PAYMENT_METHODS,key="finance_pay_method");ref=st.text_input("Transaction Reference",key="finance_pay_reference");pd=st.date_input("Payment Date",date.today(),key="finance_pay_date")
    if st.button("Record Payment",type="primary",width="stretch",key="finance_pay_save"):
        try:record_payment({"doc_no":r["doc_no"],"amount":amount,"method":method,"reference":ref.strip(),"date":pd.isoformat()});st.success("Payment recorded.");st.rerun()
        except Exception as exc:st.error(f"Payment failed: {exc}")

def render()->None:
    page_header("billing",status_text="Online");user=st.session_state.get("user",{});can_edit=can_write(str(user.get("role","")).lower(),"billing")
    tabs=st.tabs(["Documents","Payments"]+(["New Document"] if can_edit else []))
    with tabs[0]:
        rows=list_invoices() or [];q=st.text_input("Search",placeholder="Document, customer, Job or B/L reference",key="finance_v2_search")
        if q.strip():rows=[r for r in rows if q.strip().lower() in str(r).lower()]
        st.dataframe(pd.DataFrame([{"Document No.":r.get("doc_no"),"Type":DOC_TYPES.get(r.get("doc_type"),r.get("doc_type")),"Customer":r.get("customer_name"),"Issue Date":r.get("issue_date"),"Due Date":r.get("due_date"),"Total":r.get("grand_total"),"Outstanding":r.get("outstanding"),"Status":r.get("status")} for r in rows]),hide_index=True,width="stretch")
        choices=[r.get("doc_no") for r in rows if r.get("doc_no")]
        if choices:
            selected=st.selectbox("Select document",choices,key="finance_v2_selected");rec=next(r for r in rows if r.get("doc_no")==selected);status=_status(selected,rec.get("status"));a,b,c,d,e=st.columns([3,1,1,1,1]);a.caption(f"{DOC_TYPES.get(rec.get('doc_type'),rec.get('doc_type'))} · {rec.get('customer_name','—')} · {status}")
            with b:_pdf(selected)
            with c:
                if can_edit and status=="Draft" and st.button("Edit",key=f"finance_edit_{selected}",width="stretch"):st.session_state["finance_edit"]=selected;st.rerun()
            with d:
                if can_edit and status=="Draft" and st.button("Submit",key=f"finance_submit_{selected}",width="stretch"):submit_for_approval("invoice",selected,user);st.rerun()
                elif can_approve("invoice",user) and status=="Pending Approval" and st.button("Approve",key=f"finance_approve_{selected}",type="primary",width="stretch"):approve_document("invoice",selected,user);st.rerun()
            with e:
                if can_edit and st.button("Duplicate",key=f"finance_dup_{selected}",width="stretch"):st.success(f"Created {duplicate_invoice(selected,user)} as Draft.");st.rerun()
            if can_edit and st.session_state.get("finance_edit")==selected:_edit(selected)
    with tabs[1]:_payments()
    if can_edit:
        with tabs[2]:_new(user)
