import pytest
import time
from database.connection import init_database
from database.local_schema_compat import ensure_phase30_local_schema
from managers.tenant_context import set_current_tenant_id
from managers.document_manager import (
    upload_document,
    list_documents,
    get_document,
    get_document_versions,
    link_document_to_entity,
    get_related_entities,
    update_document_status,
    delete_document,
)


@pytest.fixture(autouse=True)
def setup_db():
    init_database()
    ensure_phase30_local_schema()


def test_document_upload_versioning_and_lifecycle():
    uid = int(time.time() * 1000) % 1000000
    tenant_a = f"tenant_doc_{uid}"
    tenant_b = f"tenant_doc_other_{uid}"

    set_current_tenant_id(tenant_a)

    user = {"id": 1, "username": "doc_controller"}
    sample_content = b"PDF_SMART_FREIGHT_MOCK_CONTENT_VERSION_1"
    
    # 1. Upload initial document
    doc_id = upload_document(
        document_type="BOOKING_CONFIRMATION",
        document_category="OPERATIONAL",
        document_no=f"DOC-BK-{uid}",
        file_bytes=sample_content,
        original_filename=f"booking_confirmation_{uid}.pdf",
        mime_type="application/pdf",
        document_date="2026-08-17",
        description="Initial booking draft",
        user=user,
        linked_entity_type="job",
        linked_entity_id=f"JOB-{uid}"
    )
    assert doc_id is not None
    assert doc_id > 0

    # 2. Retrieve document details
    doc = get_document(doc_id)
    assert doc is not None
    assert doc["document_no"] == f"DOC-BK-{uid}"
    assert doc["document_type"] == "BOOKING_CONFIRMATION"

    # 3. Check version history
    versions = get_document_versions(doc_id)
    assert len(versions) == 1
    assert versions[0]["version_number"] == 1

    # 4. Upload version 2 of the same document
    sample_content_v2 = b"PDF_SMART_FREIGHT_MOCK_CONTENT_VERSION_2"
    doc_id_v2 = upload_document(
        document_type="BOOKING_CONFIRMATION",
        document_category="OPERATIONAL",
        document_no=f"DOC-BK-{uid}",
        file_bytes=sample_content_v2,
        original_filename=f"booking_confirmation_{uid}_v2.pdf",
        mime_type="application/pdf",
        document_date="2026-08-17",
        description="Amended booking with new voyage",
        user=user,
    )
    assert doc_id_v2 == doc_id
    versions_v2 = get_document_versions(doc_id)
    assert len(versions_v2) == 2

    # 5. Check links
    links = get_related_entities(doc_id)
    assert len(links) >= 1
    assert any(l["entity_type"] == "job" and l["entity_id"] == f"JOB-{uid}" for l in links)

    # Link to another entity (e.g. invoice)
    link_document_to_entity(doc_id, "invoice", f"INV-{uid}", user)
    updated_links = get_related_entities(doc_id)
    assert any(l["entity_type"] == "invoice" for l in updated_links)

    # 6. Status update
    update_document_status(doc_id, "ARCHIVED", user)
    doc_archived = get_document(doc_id)
    assert doc_archived["status"] == "ARCHIVED"

    # 7. Multi-tenant isolation: Tenant B should NOT see document
    set_current_tenant_id(tenant_b)
    assert get_document(doc_id) is None
    assert not any(d["id"] == doc_id for d in list_documents())

    # Switch back and delete
    set_current_tenant_id(tenant_a)
    delete_document(doc_id, user)
    assert get_document(doc_id) is None
