import streamlit as st
import pandas as pd
from datetime import datetime
from managers.document_manager import (
    upload_document, list_documents, get_document_versions,
    download_document_version, search_documents, link_document,
    update_document_status, delete_document, MAX_FILE_SIZE
)

# Phase D2 - Professional Freight Forwarding Document Types
DOCUMENT_TYPES = {
    "COMMERCIAL DOCUMENTS": [
        "Commercial Invoice", "Proforma Invoice", "Packing List", 
        "Purchase Order", "Sales Order", "Delivery Order", 
        "Credit Note", "Debit Note"
    ],
    "SHIPPING / CARRIER DOCUMENTS": [
        "Booking Confirmation", "Shipping Instruction", "Bill of Lading",
        "Master Bill of Lading", "House Bill of Lading", "Sea Waybill",
        "Air Waybill", "Arrival Notice", "Delivery Order", "Cargo Manifest",
        "Freight Invoice", "Carrier Invoice"
    ],
    "CUSTOMS / REGULATORY": [
        "Customs Declaration", "Export Declaration", "Import Declaration",
        "Customs Entry", "Certificate of Origin", "Import Permit",
        "Export Permit", "Tax Document", "Customs Receipt", 
        "Duty Payment Evidence", "Regulatory Certificate"
    ],
    "TRANSPORT / TRUCKING": [
        "Truck Booking", "Transport Order", "Trucking Confirmation",
        "Driver Document", "Vehicle Document", "Delivery Receipt",
        "Proof of Delivery", "Gate In", "Gate Out", "Empty Return",
        "Interchange Receipt", "EIR"
    ],
    "FINANCE": [
        "Customer Invoice", "Vendor Invoice", "Receipt", "Payment Advice",
        "Payment Evidence", "Credit Note", "Debit Note", "Statement of Account",
        "Accounts Receivable Document", "Accounts Payable Document"
    ],
    "INTERNAL OPERATIONS": [
        "Job Instruction", "Shipping Instruction", "Operation Note",
        "Rate Sheet", "Quotation", "Booking Note", "Job Cost Document",
        "Internal Approval", "Customer Approval", "Vendor Approval",
        "Email Correspondence", "Other"
    ]
}

FLAT_DOC_TYPES = []
for k, v in DOCUMENT_TYPES.items():
    FLAT_DOC_TYPES.extend(v)
FLAT_DOC_TYPES.sort()

def render_document_upload_form(entity_type: str, entity_id: str):
    st.subheader("📎 Upload New Document")
    with st.form(f"upload_doc_form_{entity_type}_{entity_id}", clear_on_submit=True):
        col1, col2 = st.columns(2)
        doc_cat = col1.selectbox("Category", list(DOCUMENT_TYPES.keys()))
        
        # Need a dynamic sub-select, but st.form doesn't support dynamic updates.
        # We'll just provide a flat list or rely on session state outside form if needed.
        # For simplicity in form, we'll use a flat list for doc type.
        doc_type = col2.selectbox("Document Type / ประเภทเอกสาร", FLAT_DOC_TYPES)
        
        c3, c4 = st.columns(2)
        doc_no = c3.text_input("Document No. / เลขที่เอกสาร (Optional)", help="e.g. INV-2608-0001")
        doc_date = c4.date_input("Document Date / วันที่เอกสาร")
        
        desc = st.text_input("Description / คำอธิบาย")
        
        uploaded_file = st.file_uploader("Select File / เลือกไฟล์ (Max 50MB)", 
                                         accept_multiple_files=False)
        
        submit = st.form_submit_button("Upload Document / อัปโหลดเอกสาร")
        
        if submit:
            if not uploaded_file:
                st.error("Please select a file to upload.")
                return
            
            if uploaded_file.size > MAX_FILE_SIZE:
                st.error("File exceeds 50MB limit.")
                return
                
            try:
                # If doc_no is empty, generate a temporary or leave blank.
                # Since document_no is NOT NULL in DB, we use 'N/A' if empty.
                final_doc_no = doc_no.strip() if doc_no.strip() else f"DOC-{datetime.now().strftime('%Y%m%d%H%M%S')}"
                
                doc_id = upload_document(
                    document_type=doc_type,
                    document_category=doc_cat,
                    document_no=final_doc_no,
                    file_bytes=uploaded_file.getvalue(),
                    original_filename=uploaded_file.name,
                    mime_type=uploaded_file.type,
                    document_date=doc_date.strftime("%Y-%m-%d"),
                    description=desc,
                    user=st.session_state.get('user'),
                    linked_entity_type=entity_type,
                    linked_entity_id=entity_id
                )
                st.success(f"Document {final_doc_no} uploaded successfully!")
                st.rerun()
            except Exception as e:
                st.error(f"Upload failed: {str(e)}")

def render_document_list(entity_type: str, entity_id: str):
    st.subheader("📋 Document History / ประวัติเอกสาร")
    docs = list_documents(entity_type, entity_id)
    
    if not docs:
        st.info("No documents found for this record.")
        return
        
    for doc in docs:
        with st.expander(f"📄 {doc['document_type']} - {doc['document_no']} (v{doc['version_number']})"):
            c1, c2, c3, c4 = st.columns(4)
            c1.caption("Original File")
            c1.write(doc['original_file_name'])
            c2.caption("Uploaded By")
            c2.write(doc['uploaded_by'])
            c3.caption("Date")
            c3.write(doc['uploaded_at'].strftime("%Y-%m-%d %H:%M") if doc['uploaded_at'] else "-")
            c4.caption("Status")
            
            status_opts = ["Draft", "Received", "Under Review", "Approved", "Rejected", "Final", "Expired", "Archived"]
            new_status = c4.selectbox("Status", status_opts, index=status_opts.index(doc['status']) if doc['status'] in status_opts else 0, key=f"stat_{doc['id']}")
            if new_status != doc['status']:
                update_document_status(doc['id'], new_status, st.session_state.get('user'))
                st.rerun()
                
            st.caption(f"**Description:** {doc['description']}")
            
            dc1, dc2, dc3, dc4 = st.columns(4)
            
            if dc1.button("📥 Download Current", key=f"dl_{doc['id']}"):
                try:
                    file_data = download_document_version(doc['id'])
                    st.download_button(
                        label="Click to Download",
                        data=file_data['file_bytes'],
                        file_name=file_data['original_file_name'],
                        mime=file_data['mime_type'],
                        key=f"dl_btn_{doc['id']}"
                    )
                except Exception as e:
                    st.error(f"Download failed: {str(e)}")
                    
            if dc2.button("📜 Version History", key=f"vh_{doc['id']}"):
                st.session_state[f"show_versions_{doc['id']}"] = not st.session_state.get(f"show_versions_{doc['id']}", False)
                
            if dc3.button("🗑️ Delete", type="primary", key=f"del_{doc['id']}"):
                delete_document(doc['id'], st.session_state.get('user'))
                st.rerun()
                
            if st.session_state.get(f"show_versions_{doc['id']}", False):
                st.write("---")
                st.write("**Version History**")
                versions = get_document_versions(doc['id'])
                for v in versions:
                    st.write(f"- **v{v['version_number']}**: {v['original_file_name']} (by {v['uploaded_by']} at {v['uploaded_at']})")

def render_document_checklist(entity_type: str, entity_id: str, workflow_type: str = "DEFAULT"):
    st.subheader("✅ Document Compliance Checklist")
    
    # Minimal checklist logic for D59
    RULES = {
        "EXPORT SEA FCL": ["Booking Confirmation", "Commercial Invoice", "Packing List", "Shipping Instruction", "Master Bill of Lading", "House Bill of Lading", "Customs Declaration", "Proof of Delivery", "Customer Invoice"],
        "IMPORT SEA FCL": ["Pre-Alert", "Commercial Invoice", "Packing List", "Master Bill of Lading", "House Bill of Lading", "Arrival Notice", "Customs Entry", "Delivery Order", "Proof of Delivery", "Customer Invoice"],
        "DEFAULT": ["Commercial Invoice", "Packing List", "Bill of Lading"]
    }
    
    required = RULES.get(workflow_type, RULES["DEFAULT"])
    docs = list_documents(entity_type, entity_id)
    received_types = [d["document_type"] for d in docs if d["status"] not in ["Rejected", "Void", "Cancelled", "Expired"]]
    
    missing = []
    received_valid = []
    
    for r in required:
        if r in received_types:
            received_valid.append(r)
        else:
            missing.append(r)
            
    pct = int((len(received_valid) / len(required)) * 100) if required else 100
    
    st.progress(pct / 100.0, text=f"{pct}% Complete ({len(received_valid)} / {len(required)} Required Documents)")
    
    if missing:
        st.warning(f"**Missing:** {', '.join(missing)}")
    else:
        st.success("All required documents received.")

def render_document_section(entity_type: str, entity_id: str, workflow_type: str = "DEFAULT"):
    """
    To be injected into views (shipment_view, booking_view, etc.)
    """
    st.markdown("---")
    render_document_checklist(entity_type, entity_id, workflow_type)
    st.markdown("---")
    render_document_upload_form(entity_type, entity_id)
    render_document_list(entity_type, entity_id)
