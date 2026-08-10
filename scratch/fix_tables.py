import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from database.connection import get_connection

def recreate_tables():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("DROP TABLE IF EXISTS shipment_milestones CASCADE;")
            cur.execute("""
                CREATE TABLE shipment_milestones (
                    id SERIAL PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    shipment_id INTEGER REFERENCES shipments(id),
                    milestone_code TEXT,
                    milestone_name TEXT,
                    planned_date TIMESTAMP,
                    actual_date TIMESTAMP,
                    status TEXT DEFAULT 'PENDING',
                    responsible_user TEXT,
                    remarks TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            cur.execute("DROP TABLE IF EXISTS transport_orders CASCADE;")
            cur.execute("""
                CREATE TABLE transport_orders (
                    id SERIAL PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    transport_order_no TEXT UNIQUE NOT NULL,
                    order_type TEXT DEFAULT 'TRUCKING',
                    job_no TEXT,
                    customer_name TEXT,
                    vendor_name TEXT,
                    pickup_location TEXT,
                    delivery_location TEXT,
                    pickup_time TIMESTAMP,
                    delivery_time TIMESTAMP,
                    truck_type TEXT,
                    vehicle_no TEXT,
                    driver_name TEXT,
                    container_no TEXT,
                    cargo_details TEXT,
                    special_instructions TEXT,
                    status TEXT DEFAULT 'DRAFT',
                    pod_received BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            cur.execute("DROP TABLE IF EXISTS physical_documents CASCADE;")
            cur.execute("""
                CREATE TABLE physical_documents (
                    id SERIAL PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    job_no TEXT,
                    document_type TEXT,
                    is_original BOOLEAN DEFAULT TRUE,
                    quantity INTEGER DEFAULT 1,
                    received_from TEXT,
                    received_date TIMESTAMP,
                    storage_location TEXT,
                    released_to TEXT,
                    released_date TIMESTAMP,
                    courier_name TEXT,
                    tracking_no TEXT,
                    returned_date TIMESTAMP,
                    destroyed_date TIMESTAMP,
                    barcode TEXT,
                    remarks TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            cur.execute("DROP TABLE IF EXISTS commissions CASCADE;")
            cur.execute("""
                CREATE TABLE commissions (
                    id SERIAL PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    job_no TEXT,
                    sales_person TEXT,
                    basis TEXT,
                    rate NUMERIC(5,2),
                    commission_amount NUMERIC(15,2),
                    status TEXT DEFAULT 'DRAFT',
                    calculated_at TIMESTAMP,
                    approved_by TEXT,
                    paid_at TIMESTAMP,
                    remarks TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            cur.execute("DROP TABLE IF EXISTS regulatory_submissions CASCADE;")
            cur.execute("""
                CREATE TABLE regulatory_submissions (
                    id SERIAL PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    submission_type TEXT,
                    country TEXT,
                    authority TEXT,
                    job_no TEXT,
                    hbl_no TEXT,
                    mbl_no TEXT,
                    container_no TEXT,
                    submission_reference TEXT,
                    submission_date TIMESTAMP,
                    cut_off_date TIMESTAMP,
                    submitted_by TEXT,
                    status TEXT DEFAULT 'DRAFT',
                    response TEXT,
                    error_msg TEXT,
                    version INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
        conn.commit()

if __name__ == '__main__':
    recreate_tables()
