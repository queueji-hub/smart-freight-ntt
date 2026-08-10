"""
Phase 18.8, 18.10, 18.13 - Document Center, PDF Center, Physical Custody
"""
import streamlit as st
import pandas as pd
from datetime import datetime

from managers.document_manager import search_documents, download_document_version, delete_document, update_document_status
from managers.physical_document_manager import list_custody_records, update_custody_status
from managers.shipment_manager import list_shipments
from managers.report_manager import get_company_monthly_performance
from pdf.report_generator import generate_job_sheet_pdf, generate_company_monthly_pdf
import os

DOC_CATEGORIES = {
    "COMMERCIAL": ["Commercial Invoice", "Packing List", "Purchase Order", "Sales Contract", "Proforma Invoice"],
    "SHIPPING": ["Booking Confirmation", "Shipping Instruction", "HBL", "MBL", "Sea Waybill", "Arrival Notice", "Delivery Order", "Freight Invoice"],
    "CUSTOMS / TRADE": ["Export Declaration", "Import Declaration", "Customs Entry", "Certificate of Origin", "Form E", "Form C"],
    "TRANSPORT": ["Transport Order", "Trucking Order", "Pickup Order", "Delivery Order", "Container Release", "Gate In", "Gate Out", "POD"],
    "FINANCE": ["Customer Invoice", "Vendor Invoice", "AP Voucher", "Payment Voucher", "Receipt", "SOA"],
    "REGULATORY": ["AMS", "ACI", "ENS", "ISF", "Customs Submission"],
    "INTERNAL": ["Job Sheet", "Profitability Report", "Sales Performance", "Monthly Company Report"]
}

def render():
    st.title("📎 Global Document Center & PDF Engine")
    
    tabs = st.tabs(["🔍 Document Search", "🖨️ PDF Generation Center", "🗄️ Physical Document Custody"])
    
    # ---------------------------------------------------------
    # TAB 1: DOCUMENT SEARCH
    # ---------------------------------------------------------
    with tabs[0]:
        st.subheader("Global Search")
        c1, c2, c3 = st.columns(3)
        q = c1.text_input("Search (Doc No, Job No, HBL, Customer)")
        cat = c2.selectbox("Category", ["All"] + list(DOC_CATEGORIES.keys()))
        
        flat_types = ["All"]
        if cat != "All":
            flat_types.extend(DOC_CATEGORIES[cat])
            
        doc_type = c3.selectbox("Document Type", flat_types)
        
        if st.button("Search", type="primary"):
            docs = search_documents(q)
            if doc_type != "All":
                docs = [d for d in docs if d.get("document_type") == doc_type]
            if cat != "All" and doc_type == "All":
                docs = [d for d in docs if d.get("document_type") in DOC_CATEGORIES[cat]]
                
            st.session_state["doc_results"] = docs
            
        results = st.session_state.get("doc_results", [])
        if results:
            st.success(f"Found {len(results)} matches.")
            for doc in results:
                with st.expander(f"📄 {doc.get('document_type', 'DOC')} - {doc.get('document_no', 'N/A')} (v{doc.get('version_number', 1)})"):
                    col1, col2 = st.columns(2)
                    col1.write(f"**Filename:** {doc.get('original_file_name')}")
                    col1.write(f"**Uploaded By:** {doc.get('uploaded_by')} at {doc.get('uploaded_at')}")
                    
                    status_opts = ["Draft", "Final", "Archived"]
                    new_status = col2.selectbox("Status", status_opts, index=status_opts.index(doc.get('status', 'Draft')) if doc.get('status') in status_opts else 0, key=f"stat_{doc['id']}")
                    if new_status != doc.get('status'):
                        update_document_status(doc['id'], new_status, st.session_state.get("user"))
                        st.rerun()
                        
                    if st.button("Download", key=f"dl_{doc['id']}"):
                        try:
                            file_data = download_document_version(doc['id'])
                            st.download_button(
                                label="Confirm Download",
                                data=file_data['file_bytes'],
                                file_name=file_data['original_file_name'],
                                mime=file_data['mime_type'],
                                key=f"conf_dl_{doc['id']}"
                            )
                        except Exception as e:
                            st.error(f"Download Error: {str(e)}")
        else:
            st.info("No documents found.")

    # ---------------------------------------------------------
    # TAB 2: PDF GENERATION CENTER
    # ---------------------------------------------------------
    with tabs[1]:
        st.subheader("Historical & Real-time PDF Generator")
        st.warning("⚠️ Do not overwrite historical PDFs. Regeneration creates Version 2, 3, etc.")
        
        pdf_type = st.selectbox("Select Report to Generate", ["Job Sheet", "Company Monthly Report"])
        
        if pdf_type == "Job Sheet":
            jobs = list_shipments()
            if jobs:
                job_no = st.selectbox("Select Job", [j["job_no"] for j in jobs])
                if st.button("Generate PDF"):
                    # Mock PDF Gen mapping since UI layer shouldn't recreate logic
                    # In real app, we fetch job, profit, milestones and pass to pdf_engine.
                    st.info("Triggering PDF Engine for Job Sheet...")
                    try:
                        # Fallback testing
                        pdf_path = generate_job_sheet_pdf(
                            job_data={"job_no": job_no, "status": "Generated"},
                            profit_data={"ar_actual": 0, "ap_actual": 0, "actual_net_profit": 0},
                            milestones=[]
                        )
                        with open(pdf_path, "rb") as f:
                            st.download_button("Download Generated PDF", f, file_name=f"{job_no}_JobSheet.pdf")
                    except Exception as e:
                        st.error(f"PDF Engine failed: {str(e)}. (Check FPDF dependencies)")
            else:
                st.info("No jobs available.")
                
        elif pdf_type == "Company Monthly Report":
            now = datetime.now()
            c1, c2 = st.columns(2)
            rm = c1.selectbox("Month", [f"{i:02d}" for i in range(1,13)], index=now.month-1)
            ry = c2.selectbox("Year", ["2025", "2026", "2027"])
            
            if st.button("Generate Executive PDF"):
                st.info("Triggering PDF Engine...")
                try:
                    perf = get_company_monthly_performance(rm, ry)
                    pdf_path = generate_company_monthly_pdf(rm, ry, perf)
                    with open(pdf_path, "rb") as f:
                        st.download_button("Download Monthly Report", f, file_name=f"Company_Report_{rm}_{ry}.pdf")
                except Exception as e:
                    st.error(f"PDF Engine failed: {str(e)}")

    # ---------------------------------------------------------
    # TAB 3: PHYSICAL DOCUMENT CUSTODY
    # ---------------------------------------------------------
    with tabs[2]:
        st.subheader("Physical Original Document Tracking")
        st.caption("Phase 18.13 - Track original OBL, COO, Form E paper custody.")
        
        records = list_custody_records()
        if records:
            df_custody = pd.DataFrame(records)
            st.dataframe(df_custody[["job_no", "document_type", "is_original", "status", "custodian", "received_date", "released_date"]], use_container_width=True)
            
            # Simple status update
            rec_id = st.selectbox("Select Record to Update", df_custody["id"].tolist())
            new_stat = st.selectbox("New Custody Status", ["IN OFFICE", "WITH CUSTOMER", "WITH CARRIER", "WITH CUSTOMS", "ARCHIVED", "LOST"])
            
            if st.button("Update Custody"):
                update_custody_status(rec_id, new_stat)
                st.success("Updated!")
                st.rerun()
        else:
            st.info("No physical documents are being tracked.")
