import sqlite3
import os
from pathlib import Path

db_path = Path('c:/Users/User/Desktop/Got/Smart Freight NTT/data/smart_freight.db')
if not db_path.exists():
    db_path = Path('c:/Users/User/Desktop/Got/Smart Freight NTT,/data/smart_freight.db')

tables_to_migrate = [
    'users',
    'customers',
    'quotations',
    'quotation_items',
    'invoices',
    'invoice_items',
    'invoice_payments',
    'shipments',
    'shipment_milestones',
    'bills_of_lading',
    'containers',
    'bl_containers',
    'job_costs',
    'profit_sheets',
    'booking_revisions',
    'fx_rates',
    'sessions',
    'job_counters',
    'doc_counters'
]

def migrate_tenant():
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    
    try:
        # 1. Add tenant_id column
        for table in tables_to_migrate:
            try:
                cur.execute(f"ALTER TABLE {table} ADD COLUMN tenant_id TEXT DEFAULT 'default'")
                print(f"Added tenant_id to {table}")
            except sqlite3.OperationalError as e:
                if 'duplicate column name' in str(e):
                    print(f"tenant_id already exists in {table}")
                else:
                    raise
                    
        # 2. Backfill existing records
        for table in tables_to_migrate:
            cur.execute(f"UPDATE {table} SET tenant_id = 'default' WHERE tenant_id IS NULL")
            print(f"Backfilled {cur.rowcount} records in {table}")
            
        # 3. Add Indexes for tenant_id
        for table in tables_to_migrate:
            try:
                cur.execute(f"CREATE INDEX idx_{table}_tenant ON {table}(tenant_id)")
                print(f"Created index on {table}(tenant_id)")
            except sqlite3.OperationalError:
                pass # Index already exists
                
        conn.commit()
        print("Tenant migration completed successfully.")
        
    except Exception as e:
        conn.rollback()
        print(f"Migration failed: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    migrate_tenant()
