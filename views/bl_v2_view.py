"""Production B/L workspace aligned to the supplied Ocean B/L reference."""
from __future__ import annotations
import os
from datetime import date
from typing import Any, Dict
import pandas as pd
import streamlit as st
from managers.auth_manager import can_write
from managers.bl_workflow_service import BL_TYPES, approve, create_bl_from_job, get_bl, list_bls, submit_for_approval, update_bl
from managers.document_approval_manager import can_approve
from managers.shipment_manager import list_shipments
from ui.design_system import page_header, section

def _s(v: Any, default: str = "—") -> str:
    x = str(v or "").strip()
    return default if not x or x.lower() in {"none", "nan", "nat"} else x

def _d(v: Any) -> date:
    if isinstance(v, date): return v
    try: return date.fromisoformat(str(v)[:10])
    except Exception: return date.today()

def _pdf(bl: Dict[str, Any]) -> None:
    bid = int(bl["id"]); key = f"bl_v2_{bid}"
    if st.button("PDF", key=f"{key}_make", type="primary", width="stretch"):
        try:
            from pdf.bl_pdf import generate_bl_pdf
            payload = {"bl": {**bl, "approval_status": bl.get("approval_status", "Draft")}, "job": {}, "booking": {}, "containers": []}
            path = generate_bl_pdf(payload)
            if not path or not os.path.exists(path): raise FileNotFoundError("B/L PDF generator returned no file.")
            with open(path, "rb") as fh: st.session_state[f"{key}_bytes"] = fh.read()
            st.session_state[f"{key}_name"] = os.path.basename(path)
        except Exception as exc: st.error(f"Unable to create B/L PDF: {exc}")
    if st.session_state.get(f"{key}_bytes"):
        st.download_button("Download", st.session_state[f"{key}_bytes"], file_name=st.session_state.get(f"{key}_name", f"BL_{bid}.pdf"), mime="application/pdf", key=f"{key}_dl", width="stretch")

def _new(user: Dict[str, Any]) -> None:
    jobs = [j.get("job_no") for j in (list_shipments(limit=200) or []) if j.get("job_no")]
    if not jobs: st.info("Create a Job first before creating a B/L."); return
    section("New B/L")
    with st.form("bl_v2_new"):
        a,b,c = st.columns(3)
        job = a.selectbox("Job", jobs); typ = b.selectbox("B/L Type", list(BL_TYPES)); bd = c.date_input("B/L Date", date.today())
        place = st.text_input("Place of Issue", "BANGKOK, THAILAND")
        go = st.form_submit_button("Create Draft B/L", type="primary", width="stretch")
    if go:
        try:
            bid = create_bl_from_job(job, typ, user, overrides={"bl_date": bd.isoformat(), "place_of_issue": place.strip()})
            st.session_state["bl_v2_selected"] = bid; st.success("B/L created as Draft and prefilled from Job."); st.rerun()
        except Exception as exc: st.error(f"Unable to create B/L: {exc}")

def _edit(bl: Dict[str, Any]) -> None:
    bid = int(bl["id"])
    with st.expander("Edit B/L Data", expanded=True):
        with st.form(f"bl_v2_edit_{bid}"):
            section("Parties")
            a,b = st.columns(2); shipper=a.text_area("Shipper / Exporter", _s(bl.get("shipper"), ""), height=85); consignee=b.text_area("Consignee", _s(bl.get("consignee"), ""), height=85)
            notify=st.text_area("Notify Party", _s(bl.get("notify_party"), ""), height=65)
            section("Routing & Vessel")
            a,b,c=st.columns(3); por=a.text_input("Place of Receipt / Pre-Carriage", _s(bl.get("place_of_receipt"), "")); pol=b.text_input("Port of Loading", _s(bl.get("port_of_loading"), "")); pod=c.text_input("Port of Discharge", _s(bl.get("port_of_discharge"), ""))
            a,b,c=st.columns(3); delivery=a.text_input("Place of Delivery", _s(bl.get("place_of_delivery"), "")); final=a.text_input("Final Destination", _s(bl.get("final_destination"), "")); vessel=c.text_input("Ocean Vessel", _s(bl.get("vessel"), ""))
            a,b,c=st.columns(3); voyage=a.text_input("Voyage No.", _s(bl.get("voyage"), "")); etd=b.date_input("ETD", _d(bl.get("etd"))); eta=c.date_input("ETA", _d(bl.get("eta")))
            section("B/L Header & Issue")
            a,b,c=st.columns(3); bl_date=a.date_input("B/L Date", _d(bl.get("bl_date"))); issue=b.text_input("Place of Issue", _s(bl.get("place_of_issue"), "BANGKOK, THAILAND")); originals=c.number_input("No. of Original B/Ls", min_value=0, value=int(bl.get("number_of_originals") or 0), step=1)
            section("Cargo / Packages")
            a,b,c,d=st.columns(4); marks=a.text_area("Marks & Numbers", _s(bl.get("marks_numbers"), "N/M"), height=70); packages=b.number_input("No. of Packages", min_value=0, value=int(bl.get("package_qty") or 0)); ptype=c.text_input("Package Unit", _s(bl.get("package_type"), "PKGS")); hs=d.text_input("HS Code", _s(bl.get("hs_code"), ""))
            goods=st.text_area("Description of Packages and Goods", _s(bl.get("description_of_goods"), ""), height=140)
            a,b=st.columns(2); gross=a.number_input("Gross Weight (KG)", min_value=0.0, value=float(bl.get("gross_weight") or 0), step=0.01); cbm=b.number_input("Measurement (CBM)", min_value=0.0, value=float(bl.get("measurement_cbm") or 0), step=0.001)
            section("Freight & Delivery")
            a,b=st.columns(2); freight=a.selectbox("Freight", ["PREPAID","COLLECT"], index=0 if str(bl.get("freight_term") or "PREPAID").upper()=="PREPAID" else 1); payable=b.text_input("Freight Payable At", _s(bl.get("freight_payable_at"), ""))
            remarks=st.text_area("Remarks", _s(bl.get("remarks"), "")); special=st.text_area("Special Instructions", _s(bl.get("special_instructions"), ""))
            save=st.form_submit_button("Save B/L Data", type="primary", width="stretch")
        if save:
            try:
                update_bl(bid, {"shipper":shipper.strip(),"consignee":consignee.strip(),"notify_party":notify.strip(),"place_of_receipt":por.strip(),"port_of_loading":pol.strip(),"port_of_discharge":pod.strip(),"place_of_delivery":delivery.strip(),"final_destination":final.strip(),"vessel":vessel.strip() or None,"voyage":voyage.strip() or None,"etd":etd.isoformat(),"eta":eta.isoformat(),"bl_date":bl_date.isoformat(),"place_of_issue":issue.strip(),"number_of_originals":originals,"marks_numbers":marks.strip(),"freight_term":freight,"freight_payable_at":payable.strip(),"package_qty":packages,"package_type":ptype.strip(),"description_of_goods":goods.strip(),"gross_weight":gross,"measurement_cbm":cbm,"hs_code":hs.strip(),"remarks":remarks.strip(),"special_instructions":special.strip()})
                st.success("B/L updated."); st.rerun()
            except Exception as exc: st.error(f"Unable to update B/L: {exc}")

def _preview(bl: Dict[str, Any]) -> None:
    section("Document Preview Data")
    st.caption("Field order mirrors the Ocean Bill of Lading reference; the official PDF is the print/export surface.")
    a,b=st.columns(2)
    a.markdown(f"**Shipper**\n\n{_s(bl.get('shipper'))}\n\n**Consignee**\n\n{_s(bl.get('consignee'))}\n\n**Notify Party**\n\n{_s(bl.get('notify_party'))}")
    b.markdown(f"**B/L No.** `{_s(bl.get('bl_no'))}`\n\n**Type** {_s(bl.get('bl_type'))}\n\n**Originals** {_s(bl.get('number_of_originals'),'0')}\n\n**Place / Date** {_s(bl.get('place_of_issue'))} / {_s(bl.get('bl_date'))}")
    st.dataframe(pd.DataFrame([{"Pre-Carriage / Receipt":_s(bl.get('place_of_receipt')),"POL":_s(bl.get('port_of_loading')),"POD":_s(bl.get('port_of_discharge')),"Delivery":_s(bl.get('place_of_delivery')),"Final Destination":_s(bl.get('final_destination')),"Vessel / Voyage":f"{_s(bl.get('vessel'))} / {_s(bl.get('voyage'))}"}]), hide_index=True, width="stretch")
    st.dataframe(pd.DataFrame([{"Marks & Numbers":_s(bl.get('marks_numbers')),"Packages":f"{_s(bl.get('package_qty'),'0')} {_s(bl.get('package_type'),'')}","Description":_s(bl.get('description_of_goods')),"Gross KG":float(bl.get('gross_weight') or 0),"CBM":float(bl.get('measurement_cbm') or 0),"HS Code":_s(bl.get('hs_code')),"Freight":_s(bl.get('freight_term'))}]), hide_index=True, width="stretch")
    if bl.get("remarks") or bl.get("special_instructions"): st.markdown(f"**Remarks:** {_s(bl.get('remarks'),'')}  \n**Special Instructions:** {_s(bl.get('special_instructions'),'')}")

def render() -> None:
    page_header("bl", status_text="Online")
    user=st.session_state.get("user",{}); can_edit=can_write(str(user.get("role","")).lower(),"bl"); rows=list_bls() or []
    a,b,c=st.columns([4,1,1]); query=a.text_input("Search",placeholder="B/L, Job, Shipper, Consignee, POL or POD",key="bl_v2_search"); typ=b.selectbox("Type",["All"]+list(BL_TYPES),key="bl_v2_type"); new=c.button("New B/L",type="primary",width="stretch") if can_edit else False
    if query.strip(): rows=[r for r in rows if query.strip().lower() in str(r).lower()]
    if typ!="All": rows=[r for r in rows if r.get("bl_type")==typ]
    section("B/L Ledger")
    st.dataframe(pd.DataFrame([{"B/L No.":_s(r.get("bl_no")),"Type":_s(r.get("bl_type")),"Job":_s(r.get("job_no")),"Customer":_s(r.get("customer_name")),"POL":_s(r.get("port_of_loading")),"POD":_s(r.get("port_of_discharge")),"Vessel / Voyage":f"{_s(r.get('vessel'))} / {_s(r.get('voyage'))}","Status":_s(r.get("approval_status"),"Draft")} for r in rows]), hide_index=True, width="stretch")
    if new: _new(user)
    ids=[int(r["id"]) for r in rows if r.get("id") is not None]
    if not ids: st.info("No B/L records found."); return
    labels={int(r["id"]):f"{r.get('bl_no')} · {r.get('bl_type')} · {r.get('approval_status','Draft')}" for r in rows if r.get("id") is not None}; default=ids.index(st.session_state.get("bl_v2_selected")) if st.session_state.get("bl_v2_selected") in ids else 0
    selected=st.selectbox("Select B/L",ids,index=default,format_func=lambda x:labels[x],key="bl_v2_selected_box"); bl=get_bl(selected)
    if not bl: st.error("Selected B/L is no longer available."); return
    st.session_state["bl_v2_selected"]=selected; status=_s(bl.get("approval_status"),"Draft")
    section("B/L Summary"); m=st.columns(6); m[0].metric("B/L No.",_s(bl.get("bl_no"))); m[1].metric("Type",_s(bl.get("bl_type"))); m[2].metric("Job",_s(bl.get("job_no"))); m[3].metric("POL",_s(bl.get("port_of_loading"))); m[4].metric("POD",_s(bl.get("port_of_discharge"))); m[5].metric("Status",status)
    section("Actions"); a,b,c,d=st.columns([2,1,1,1]);
    with a: _pdf(bl)
    with b:
        if can_edit and status=="Draft" and st.button("Submit",key=f"bl_submit_{selected}",width="stretch"):
            try: submit_for_approval(selected,user); st.rerun()
            except Exception as exc: st.error(str(exc))
    with c:
        if can_approve("bl",user) and status=="Pending Approval" and st.button("Approve",key=f"bl_approve_{selected}",type="primary",width="stretch"):
            try: approve(selected,user); st.rerun()
            except Exception as exc: st.error(str(exc))
    with d: st.caption("PDF follows the approved Ocean B/L layout.")
    tabs=st.tabs(["B/L Data","Document Preview"])
    with tabs[0]:
        if can_edit and status in {"Draft","Pending Approval"}: _edit(bl)
        else: _preview(bl)
    with tabs[1]: _preview(bl)
