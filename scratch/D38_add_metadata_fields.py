import os
import sys

# Add root directory to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from database.connection import get_connection

def add_metadata_fields():
    with get_connection() as conn:
        with conn.cursor() as cur:
            # Safely add columns using ADD COLUMN IF NOT EXISTS (requires PG 9.6+, SQLite handles it via altering if we use try/except)
            columns = [
                ("effective_date", "DATE"),
                ("issue_date", "DATE"),
                ("expiry_date", "DATE"),
                ("source", "TEXT"),
                ("confidentiality", "TEXT"),
                ("approval_status", "TEXT"),
                ("deleted_at", "TIMESTAMP"),
                ("deleted_by", "TEXT"),
                ("delete_reason", "TEXT")
            ]
            
            for col, dtype in columns:
                try:
                    # SQLite fallback doesn't support IF NOT EXISTS for columns in older versions,
                    # but checking via PRAGMA or just catching the exception works.
                    cur.execute(f"ALTER TABLE documents ADD COLUMN {col} {dtype}")
                    print(f"Added column {col} to documents table")
                except Exception as e:
                    if "duplicate column name" in str(e).lower() or "already exists" in str(e).lower():
                        print(f"Column {col} already exists")
                    else:
                        print(f"Error adding {col}: {e}")
            conn.commit()

if __name__ == "__main__":
    add_metadata_fields()
