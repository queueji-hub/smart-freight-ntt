import os
import sys
import hashlib

# Add root directory to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from database.connection import get_connection
from managers.storage_service import SupabaseStorageProvider, LocalStorageProvider

def migrate_documents(dry_run: bool = True):
    print(f"=== Document Migration to Object Storage ===")
    print(f"Mode: {'DRY RUN' if dry_run else 'EXECUTE'}")
    
    local_provider = LocalStorageProvider()
    
    try:
        remote_provider = SupabaseStorageProvider()
    except Exception as e:
        print(f"Failed to initialize remote provider: {e}")
        return

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT d.tenant_id, dv.id, dv.document_id, dv.version_number, dv.original_file_name, dv.storage_key, dv.file_hash, dv.storage_provider
                FROM document_versions dv
                JOIN documents d ON d.id = dv.document_id
                WHERE dv.storage_provider = 'LOCAL' OR dv.storage_provider IS NULL
            """)
            
            versions = cur.fetchall()
            print(f"Found {len(versions)} local document versions to migrate.")
            
            success_count = 0
            failed_count = 0
            
            for v in versions:
                storage_key = v["storage_key"]
                tenant_id = v["tenant_id"]
                document_id = v["document_id"]
                version_number = v["version_number"]
                filename = v["original_file_name"]
                old_hash = v["file_hash"]
                
                try:
                    # 1. Download from local
                    file_bytes = local_provider.download(storage_key)
                    
                    # 2. Verify checksum
                    new_hash = hashlib.sha256(file_bytes).hexdigest()
                    if old_hash and old_hash != new_hash:
                        print(f"[FAIL] Checksum mismatch for document_id={document_id} version={version_number}")
                        failed_count += 1
                        continue
                        
                    if not dry_run:
                        # 3. Upload to remote
                        new_storage_key = remote_provider.upload(
                            str(tenant_id),
                            str(document_id),
                            str(version_number),
                            filename,
                            file_bytes
                        )
                        
                        # 4. Update database
                        cur.execute("""
                            UPDATE document_versions 
                            SET storage_key = %s, storage_provider = 'SupabaseStorageProvider'
                            WHERE id = %s
                        """, (new_storage_key, v["id"]))
                        conn.commit()
                        
                        print(f"[OK] Migrated document_id={document_id} version={version_number}")
                        success_count += 1
                    else:
                        print(f"[DRY RUN] Would migrate document_id={document_id} version={version_number}")
                        
                except Exception as e:
                    print(f"[ERROR] Failed to migrate document_id={document_id}: {e}")
                    failed_count += 1
                    conn.rollback()
                    
            print(f"\nMigration Complete. Success: {success_count}, Failed: {failed_count}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Migrate local documents to object storage.")
    parser.add_argument("--execute", action="store_true", help="Perform the actual migration")
    args = parser.parse_args()
    
    migrate_documents(dry_run=not args.execute)
