def init_database():
    with get_connection() as conn:
        with conn.cursor() as cur:

            # ===== SHIPMENTS =====
            cur.execute("""
                CREATE TABLE IF NOT EXISTS shipments (
                    id SERIAL PRIMARY KEY,
                    job_no TEXT UNIQUE,
                    status TEXT DEFAULT 'Proceed',
                    job_type TEXT,
                    booking_no TEXT,
                    customer_name TEXT,
                    shipper TEXT,
                    consignee TEXT,
                    cargo_type TEXT,
                    carrier TEXT,
                    pol TEXT,
                    pod TEXT,
                    etd DATE,
                    eta DATE,
                    bl_no TEXT,
                    invoice_no TEXT,
                    customer_paid INTEGER DEFAULT 0,
                    remark TEXT,
                    created_by TEXT,
                    updated_by TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # ===== BOOKINGS =====
            cur.execute("""
                CREATE TABLE IF NOT EXISTS bookings (
                    id SERIAL PRIMARY KEY,
                    booking_no TEXT UNIQUE,
                    job_type TEXT,
                    customer_name TEXT,
                    shipper TEXT,
                    consignee TEXT,
                    pol TEXT,
                    pod TEXT,
                    etd DATE,
                    eta DATE,
                    status TEXT DEFAULT 'Draft',
                    remark TEXT,
                    created_by TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # ===== INVOICES =====
            cur.execute("""
                CREATE TABLE IF NOT EXISTS invoices (
                    id SERIAL PRIMARY KEY,
                    doc_no TEXT UNIQUE,
                    doc_type TEXT,
                    customer_name TEXT,
                    issue_date DATE,
                    due_date DATE,
                    subtotal NUMERIC DEFAULT 0,
                    vat_amount NUMERIC DEFAULT 0,
                    wht_amount NUMERIC DEFAULT 0,
                    total_amount NUMERIC DEFAULT 0,
                    outstanding NUMERIC DEFAULT 0,
                    payment_status TEXT DEFAULT 'Unpaid'
                )
            """)

            conn.commit()