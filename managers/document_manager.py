import os
import hashlib
from typing import List, Dict, Any, Optional
from datetime import datetime
from database.connection import get_connection
from managers.tenant_context import get_current_tenant_id
from managers.document_numbering_service import normalize_doc_no
from core.audit import log_action
import re

from managers.storage_service import get_storage_provider

# Basic config
ALLOWED_EXTENSIONS = {
    'pdf', 'docx', 'xlsx', 'csv', 'jpg', 'jpeg', 'png', 'zip', 'doc', 'xls'
}
FORBIDDEN_EXTENSIONS = {
    'exe', 'bat', 'cmd', 'ps1', 'vbs', 'js', 'sh', 'py'
}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB

def secure_filename(filename: str) -> str:
    filename = re.sub(r'[^a-zA-Z0-9_.-]', '_', filename)
    filename = filename.strip('_')
    return filename

def _allowed_file(filename: str) -> bool:
    if '.' not in filename:
        return False
    ext = filename.rsplit('.', 1)[1].lower()
    if ext in FORBIDDEN_EXTENSIONS:
        return False
    if ext not in ALLOWED_EXTENSIONS:
        return False
    return True

def upload_document(
    document_type: str,
    document_category: str,
    document_no: str,
    file_bytes: bytes,
    original_filename: str,
    mime_type: str,
    document_date: str = None,
    description: str = None,
    user: Dict[str, Any] = None,
    linked_entity_type: str = None,
    linked_entity_id: str = None
) -> int:
    tenant_id = get_current_tenant_id()
    
    if not _allowed_file(original_filename):
        raise ValueError("File type not allowed or executable")
    
    file_size = len(file_bytes)
    if file_size > MAX_FILE_SIZE:
        raise ValueError("File size exceeds 50MB limit")
        
    file_hash = hashlib.sha256(file_bytes).hexdigest()
    
    with get_connection() as conn:
        try:
            with conn.cursor() as cur:
                # Check if document already exists by number and type
                cur.execute("""
                    SELECT id FROM documents 
                    WHERE tenant_id=%s AND document_no=%s AND document_type=%s AND is_deleted=FALSE
                """, (tenant_id, document_no, document_type))
                existing_doc = cur.fetchone()
                
                if existing_doc:
                    document_id = existing_doc["id"]
                    # Get max version
                    cur.execute("""
                        SELECT COALESCE(MAX(version_number), 0) as max_v 
                        FROM document_versions 
                        WHERE document_id=%s
                    """, (document_id,))
                    version_number = int(cur.fetchone()["max_v"]) + 1
                else:
                    # Create new document
                    cur.execute("""
                        INSERT INTO documents (
                            tenant_id, document_no, document_type, document_category, 
                            document_date, description, created_by
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id
                    """, (tenant_id, document_no, document_type, document_category, 
                          document_date, description, user["id"] if user else 'system'))
                    document_id = cur.fetchone()["id"]
                    version_number = 1
                    
                    provider = get_storage_provider()
                    # Storage provider handles path security safely
                    storage_key = provider.upload(
                        str(tenant_id), 
                        str(document_id), 
                        str(version_number), 
                        secure_filename(original_filename),
                        file_bytes
                    )
                    
                    cur.execute("""
                        INSERT INTO document_versions (
                            document_id, version_number, original_file_name,
                            mime_type, file_size, storage_key, storage_provider,
                            file_hash, uploaded_by
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, (document_id, version_number, original_filename, 
                          mime_type, file_size, storage_key, provider.__class__.__name__, file_hash,
                          user["id"] if user else 'system'))
                    
                # Insert link if provided
                if linked_entity_type and linked_entity_id:
                    # Check if link exists
                    cur.execute("""
                        SELECT id FROM document_links 
                        WHERE document_id=%s AND entity_type=%s AND entity_id=%s
                    """, (document_id, linked_entity_type, linked_entity_id))
                    
                    if not cur.fetchone():
                        cur.execute("""
                            INSERT INTO document_links (document_id, entity_type, entity_id, created_by)
                            VALUES (%s, %s, %s, %s)
                        """, (document_id, linked_entity_type, linked_entity_id, user["id"] if user else 'system'))
                
            conn.commit()
            
            if user:
                log_action(user["id"], tenant_id, "document", str(document_id), "UPLOAD_VERSION")
                
            return document_id
            
        except Exception as e:
            conn.rollback()
            raise RuntimeError(f"Document upload failed: {str(e)}")

def list_documents(entity_type: str = None, entity_id: str = None) -> List[Dict[str, Any]]:
    tenant_id = get_current_tenant_id()
    
    query = """
        SELECT d.id, d.document_no, d.document_type, d.document_category, d.document_date, 
               d.description, d.status, d.created_at,
               dv.version_number, dv.original_file_name, dv.file_size, dv.uploaded_by, dv.uploaded_at
        FROM documents d
        JOIN (
            SELECT document_id, MAX(version_number) as max_v
            FROM document_versions GROUP BY document_id
        ) latest_v ON d.id = latest_v.document_id
        JOIN document_versions dv ON dv.document_id = d.id AND dv.version_number = latest_v.max_v
    """
    
    params = [tenant_id]
    where_clauses = ["d.tenant_id = %s", "d.is_deleted = FALSE"]
    
    if entity_type and entity_id:
        query += " JOIN document_links dl ON dl.document_id = d.id"
        where_clauses.append("dl.entity_type = %s AND dl.entity_id = %s")
        params.extend([entity_type, str(entity_id)])
        
    query += " WHERE " + " AND ".join(where_clauses)
    query += " ORDER BY d.created_at DESC"
    
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, params)
            rows = cur.fetchall()
            return [dict(r) for r in rows] if rows else []

def get_document_versions(document_id: int) -> List[Dict[str, Any]]:
    tenant_id = get_current_tenant_id()
    with get_connection() as conn:
        with conn.cursor() as cur:
            # Check ownership
            cur.execute("SELECT id FROM documents WHERE id=%s AND tenant_id=%s AND is_deleted=FALSE", 
                             (document_id, tenant_id))
            d = cur.fetchone()
            if not d:
                return []
                
            cur.execute("""
                SELECT * FROM document_versions 
                WHERE document_id=%s ORDER BY version_number DESC
            """, (document_id,))
            rows = cur.fetchall()
            return [dict(r) for r in rows] if rows else []

def download_document_version(document_id: int, version: int = None) -> Optional[Dict[str, Any]]:
    tenant_id = get_current_tenant_id()
    
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT d.document_no, dv.* FROM documents d JOIN document_versions dv ON d.id = dv.document_id WHERE d.id=%s AND d.tenant_id=%s AND d.is_deleted=FALSE", 
                             (document_id, tenant_id))
                             
            if version is None:
                cur.execute("""
                    SELECT d.document_no, dv.* 
                    FROM documents d 
                    JOIN document_versions dv ON d.id = dv.document_id 
                    WHERE d.id=%s AND d.tenant_id=%s 
                    ORDER BY dv.version_number DESC LIMIT 1
                """, (document_id, tenant_id))
            else:
                cur.execute("""
                    SELECT d.document_no, dv.* 
                    FROM documents d 
                    JOIN document_versions dv ON d.id = dv.document_id 
                    WHERE d.id=%s AND d.tenant_id=%s AND dv.version_number=%s
                """, (document_id, tenant_id, version))
                
            doc = cur.fetchone()
            if not doc:
                raise ValueError("Document version not found or access denied")
                
            provider = get_storage_provider()
            storage_key = doc["storage_key"]
            
            # Fetch bytes from provider
            file_bytes = provider.download(storage_key)
            
            return {
                "original_file_name": doc["original_file_name"],
                "mime_type": doc["mime_type"],
                "file_bytes": file_bytes,
                "version_number": doc["version_number"],
                "document_no": doc["document_no"]
            }

def search_documents(query_str: str) -> List[Dict[str, Any]]:
    tenant_id = get_current_tenant_id()
    normalized = normalize_doc_no(query_str)
    
    query = """
        SELECT DISTINCT d.id, d.document_no, d.document_type, d.document_category, d.document_date, 
               d.description, d.status, d.created_at,
               dv.version_number, dv.original_file_name, dv.file_size, dv.uploaded_by, dv.uploaded_at
        FROM documents d
        JOIN (
            SELECT document_id, MAX(version_number) as max_v
            FROM document_versions GROUP BY document_id
        ) latest_v ON d.id = latest_v.document_id
        JOIN document_versions dv ON dv.document_id = d.id AND dv.version_number = latest_v.max_v
        LEFT JOIN document_links dl ON dl.document_id = d.id
        WHERE d.tenant_id = %s AND d.is_deleted = FALSE
        AND (
            REPLACE(REPLACE(UPPER(d.document_no), '-', ''), ' ', '') LIKE %s
            OR REPLACE(REPLACE(UPPER(dl.entity_id), '-', ''), ' ', '') LIKE %s
            OR d.document_type ILIKE %s
            OR dv.original_file_name ILIKE %s
            OR d.description ILIKE %s
        )
        ORDER BY d.created_at DESC
        LIMIT 50
    """
    
    like_norm = f"%{normalized}%"
    like_raw = f"%{query_str}%"
    
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, [tenant_id, like_norm, like_norm, like_raw, like_raw, like_raw])
            rows = cur.fetchall()
            return [dict(r) for r in rows] if rows else []

def link_document(document_id: int, entity_type: str, entity_id: str, user: Dict[str, Any] = None):
    tenant_id = get_current_tenant_id()
    with get_connection() as conn:
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT id FROM documents WHERE id=%s AND tenant_id=%s AND is_deleted=FALSE", 
                                 (document_id, tenant_id))
                d = cur.fetchone()
                if not d:
                    raise ValueError("Document not found or unauthorized")
                    
                cur.execute("""
                    SELECT id FROM document_links 
                    WHERE document_id=%s AND entity_type=%s AND entity_id=%s
                """, (document_id, entity_type, entity_id))
                
                if not cur.fetchone():
                    cur.execute("""
                        INSERT INTO document_links (document_id, entity_type, entity_id, created_by)
                        VALUES (%s, %s, %s, %s)
                    """, (document_id, entity_type, entity_id, user["id"] if user else 'system'))
            conn.commit()
            if user:
                log_action(user["id"], tenant_id, "document", str(document_id), f"LINKED_TO_{entity_type}_{entity_id}")
        except Exception as e:
            conn.rollback()
            raise

def get_related_entities(document_id: int) -> List[Dict[str, Any]]:
    tenant_id = get_current_tenant_id()
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM documents WHERE id=%s AND tenant_id=%s AND is_deleted=FALSE", 
                             (document_id, tenant_id))
            if not cur.fetchone():
                return []
            
            cur.execute("""
                SELECT id, entity_type, entity_id, created_at, created_by 
                FROM document_links 
                WHERE document_id=%s
            """, (document_id,))
            rows = cur.fetchall()
            return [dict(r) for r in rows] if rows else []

def update_document_status(document_id: int, status: str, user: Dict[str, Any]):
    tenant_id = get_current_tenant_id()
    with get_connection() as conn:
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT id FROM documents WHERE id=%s AND tenant_id=%s AND is_deleted=FALSE", 
                                 (document_id, tenant_id))
                d = cur.fetchone()
                if not d:
                    raise ValueError("Document not found or unauthorized")
                    
                cur.execute("""
                    UPDATE documents SET status=%s, updated_at=CURRENT_TIMESTAMP
                    WHERE id=%s
                """, (status, document_id))
            conn.commit()
            log_action(user["id"], tenant_id, "document", str(document_id), f"STATUS_{status}")
        except Exception as e:
            conn.rollback()
            raise

def delete_document(document_id: int, user: Dict[str, Any]):
    tenant_id = get_current_tenant_id()
    with get_connection() as conn:
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT id FROM documents WHERE id=%s AND tenant_id=%s", 
                                 (document_id, tenant_id))
                d = cur.fetchone()
                if not d:
                    raise ValueError("Document not found or unauthorized")
                    
                cur.execute("""
                    UPDATE documents SET 
                        is_deleted=TRUE, 
                        deleted_at=CURRENT_TIMESTAMP,
                        deleted_by=%s,
                        delete_reason='User requested deletion',
                        updated_at=CURRENT_TIMESTAMP
                    WHERE id=%s
                """, (user["id"] if user else 'system', document_id))
            conn.commit()
            log_action(user["id"], tenant_id, "document", str(document_id), "DELETED")
        except Exception:
            conn.rollback()
            raise
