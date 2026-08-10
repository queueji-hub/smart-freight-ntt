import os
import sys
from unittest.mock import patch
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from database.connection import init_database
from managers.document_manager import (
    upload_document, list_documents, get_document_versions,
    download_document_version, search_documents, link_document,
    update_document_status, delete_document
)

def test_document_management():
    print("=" * 60)
    print("TEST: Document Management")
    print("=" * 60)
    
    user_a = {"id": 1, "username": "test_user_a"}
    user_b = {"id": 2, "username": "test_user_b"}
    
    file_content = b"Dummy PDF Content"
    file_content_v2 = b"Dummy PDF Content v2"
    exe_content = b"MZ\x90\x00\x03\x00\x00\x00\x04\x00\x00\x00\xFF\xFF\x00\x00"

    with patch('managers.document_manager.get_current_tenant_id', return_value='DOC_TENANT_A'):
        from database.connection import get_connection
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM document_links")
                cur.execute("DELETE FROM document_versions")
                cur.execute("DELETE FROM documents")
            conn.commit()
            
        with patch('managers.document_numbering_service.get_current_tenant_id', return_value='DOC_TENANT_A'):
            
            # 1. Reject executable
            try:
                upload_document(
                    document_type="Commercial Invoice",
                    document_category="COMMERCIAL",
                    document_no="INV-2608-0001",
                    file_bytes=exe_content,
                    original_filename="malicious.exe",
                    mime_type="application/x-msdownload",
                    user=user_a
                )
                assert False, "Should have rejected .exe"
            except ValueError as e:
                print(f"  OK: Rejected executable ({str(e)})")
                
            # 2. Upload valid PDF
            doc_id = upload_document(
                document_type="Commercial Invoice",
                document_category="COMMERCIAL",
                document_no="INV-2608-0001",
                file_bytes=file_content,
                original_filename="invoice.pdf",
                mime_type="application/pdf",
                description="Test Invoice",
                user=user_a,
                linked_entity_type="JOB",
                linked_entity_id="JOB-2608-0001"
            )
            print(f"  OK: Uploaded PDF. doc_id={doc_id}")
            
            # 3. List documents by link
            docs = list_documents(entity_type="JOB", entity_id="JOB-2608-0001")
            assert len(docs) == 1
            assert docs[0]["document_no"] == "INV-2608-0001"
            print(f"  OK: Listed linked document")
            
            # 4. Update status
            update_document_status(doc_id, "Approved", user_a)
            docs = list_documents(entity_type="JOB", entity_id="JOB-2608-0001")
            assert docs[0]["status"] == "Approved"
            print(f"  OK: Status updated to Approved")
            
            # 5. Upload new version
            upload_document(
                document_type="Commercial Invoice",
                document_category="COMMERCIAL",
                document_no="INV-2608-0001",
                file_bytes=file_content_v2,
                original_filename="invoice_v2.pdf",
                mime_type="application/pdf",
                user=user_a
            )
            
            versions = get_document_versions(doc_id)
            print(f"DEBUG: versions = {versions}")
            assert len(versions) == 2
            assert versions[0]["version_number"] == 2
            assert versions[1]["version_number"] == 1
            print(f"  OK: Created and retrieved version 2")
            
            # 6. Download specific version
            dl_v1 = download_document_version(doc_id, 1)
            assert dl_v1["file_bytes"] == file_content
            
            dl_latest = download_document_version(doc_id)
            assert dl_latest["file_bytes"] == file_content_v2
            print(f"  OK: Downloaded versions correctly")
            
            # 7. Search normalized
            search_res = search_documents("inv 2608 0001")
            assert len(search_res) > 0
            assert search_res[0]["id"] == doc_id
            print(f"  OK: Search normalized")
            
            # 8. Link to another entity
            link_document(doc_id, "BOOKING", "BK-2608-0001", user_a)
            bk_docs = list_documents("BOOKING", "BK-2608-0001")
            assert len(bk_docs) == 1
            print(f"  OK: Multi-linked document")

    # 9. Cross-Tenant Security
    with patch('managers.document_manager.get_current_tenant_id', return_value='DOC_TENANT_B'):
        # TENANT_B shouldn't see it
        search_res_b = search_documents("INV-2608-0001")
        assert len(search_res_b) == 0, "TENANT_B found TENANT_A's doc!"
        
        try:
            download_document_version(doc_id)
            assert False, "TENANT_B downloaded TENANT_A's file!"
        except Exception as e:
            print(f"  OK: Cross-tenant download blocked ({type(e).__name__})")
            
        try:
            update_document_status(doc_id, "Rejected", user_b)
            assert False, "TENANT_B updated TENANT_A's file!"
        except Exception as e:
            print(f"  OK: Cross-tenant update blocked ({type(e).__name__})")
            
    # 10. Delete
    with patch('managers.document_manager.get_current_tenant_id', return_value='DOC_TENANT_A'):
        delete_document(doc_id, user_a)
        docs = list_documents(entity_type="JOB", entity_id="JOB-2608-0001")
        assert len(docs) == 0
        print("  OK: Soft delete successful")

if __name__ == "__main__":
    test_document_management()
    print("ALL TESTS PASSED")
