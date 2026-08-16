"""Compatibility/self-healing contract for customer, user and finance controls."""
from __future__ import annotations


def ensure_party_finance_schema(conn, sqlite: bool = False) -> None:
    """Add the additive customer/tenant/credit-control contract to Postgres or SQLite."""
    with conn.cursor() as cur:
        if sqlite:
            cur.execute("CREATE TABLE IF NOT EXISTS customers (id INTEGER PRIMARY KEY AUTOINCREMENT, company_name TEXT NOT NULL)")
            for column, ddl in {
                "tenant_id": "TEXT DEFAULT 'default'",
                "customer_code": "TEXT",
                "display_name": "TEXT",
                "billing_name": "TEXT",
                "billing_address": "TEXT",
                "billing_country_code": "TEXT",
                "credit_limit": "REAL DEFAULT 0",
                "credit_currency": "TEXT DEFAULT 'THB'",
                "payment_term_code": "TEXT",
                "credit_status": "TEXT DEFAULT 'NORMAL'",
                "credit_hold": "INTEGER DEFAULT 0",
                "updated_by": "TEXT",
            }.items():
                cur.execute(f"PRAGMA table_info(customers)")
                existing = {str(row[1]) for row in cur.fetchall()}
                if column not in existing:
                    cur.execute(f"ALTER TABLE customers ADD COLUMN {column} {ddl}")
            cur.execute("UPDATE customers SET tenant_id='default' WHERE tenant_id IS NULL OR trim(tenant_id)=''")
            cur.execute("UPDATE customers SET display_name=company_name WHERE display_name IS NULL OR trim(display_name)=''")
            cur.execute("UPDATE customers SET billing_name=company_name WHERE billing_name IS NULL OR trim(billing_name)=''")
            cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS uq_customers_tenant_code ON customers(tenant_id, customer_code)")

            cur.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE NOT NULL)")
            cur.execute("PRAGMA table_info(users)")
            existing_users = {str(row[1]) for row in cur.fetchall()}
            if "tenant_id" not in existing_users:
                cur.execute("ALTER TABLE users ADD COLUMN tenant_id TEXT DEFAULT 'default'")
            cur.execute("UPDATE users SET tenant_id='default' WHERE tenant_id IS NULL OR trim(tenant_id)=''")

            cur.execute("CREATE TABLE IF NOT EXISTS invoices (id INTEGER PRIMARY KEY AUTOINCREMENT, doc_no TEXT UNIQUE NOT NULL)")
            cur.execute("PRAGMA table_info(invoices)")
            existing_invoices = {str(row[1]) for row in cur.fetchall()}
            for column, ddl in {"tenant_id":"TEXT DEFAULT 'default'", "payment_term_code":"TEXT"}.items():
                if column not in existing_invoices:
                    cur.execute(f"ALTER TABLE invoices ADD COLUMN {column} {ddl}")
            cur.execute("UPDATE invoices SET tenant_id='default' WHERE tenant_id IS NULL OR trim(tenant_id)=''")
            conn.commit()
            return

        cur.execute("""CREATE TABLE IF NOT EXISTS customers (
            id SERIAL PRIMARY KEY,
            tenant_id TEXT DEFAULT 'default',
            company_name TEXT NOT NULL,
            display_name TEXT,
            billing_name TEXT,
            billing_address TEXT,
            billing_country_code VARCHAR(2),
            customer_code VARCHAR(5),
            credit_limit NUMERIC(18,2) DEFAULT 0,
            credit_currency VARCHAR(3) DEFAULT 'THB',
            payment_term_code TEXT,
            credit_status TEXT DEFAULT 'NORMAL',
            credit_hold BOOLEAN DEFAULT FALSE,
            updated_by TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""")
        columns = {
            "tenant_id": "TEXT DEFAULT 'default'",
            "customer_code": "VARCHAR(5)",
            "display_name": "TEXT",
            "billing_name": "TEXT",
            "billing_address": "TEXT",
            "billing_country_code": "VARCHAR(2)",
            "credit_limit": "NUMERIC(18,2) DEFAULT 0",
            "credit_currency": "VARCHAR(3) DEFAULT 'THB'",
            "payment_term_code": "TEXT",
            "credit_status": "TEXT DEFAULT 'NORMAL'",
            "credit_hold": "BOOLEAN DEFAULT FALSE",
            "updated_by": "TEXT",
        }
        for column, ddl in columns.items():
            cur.execute(f"ALTER TABLE customers ADD COLUMN IF NOT EXISTS {column} {ddl}")
        cur.execute("UPDATE customers SET tenant_id='default' WHERE tenant_id IS NULL OR btrim(tenant_id)=''")
        cur.execute("UPDATE customers SET display_name=company_name WHERE display_name IS NULL OR btrim(display_name)=''")
        cur.execute("UPDATE customers SET billing_name=company_name WHERE billing_name IS NULL OR btrim(billing_name)=''")
        cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS uq_customers_tenant_code ON customers(tenant_id, customer_code) WHERE customer_code IS NOT NULL AND btrim(customer_code)<>' '")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_customers_tenant_credit ON customers(tenant_id, credit_status, credit_hold)")

        cur.execute("CREATE TABLE IF NOT EXISTS users (id SERIAL PRIMARY KEY, username TEXT UNIQUE NOT NULL, tenant_id TEXT DEFAULT 'default')")
        cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS tenant_id TEXT DEFAULT 'default'")
        cur.execute("UPDATE users SET tenant_id='default' WHERE tenant_id IS NULL OR btrim(tenant_id)=''")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_users_tenant_role ON users(tenant_id, role, is_active)")

        cur.execute("CREATE TABLE IF NOT EXISTS invoices (id SERIAL PRIMARY KEY, doc_no TEXT UNIQUE NOT NULL, tenant_id TEXT DEFAULT 'default')")
        cur.execute("ALTER TABLE invoices ADD COLUMN IF NOT EXISTS tenant_id TEXT DEFAULT 'default'")
        cur.execute("ALTER TABLE invoices ADD COLUMN IF NOT EXISTS payment_term_code TEXT")
        cur.execute("UPDATE invoices SET tenant_id='default' WHERE tenant_id IS NULL OR btrim(tenant_id)=''")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_invoices_tenant_customer_due ON invoices(tenant_id, customer_id, due_date)")
    conn.commit()
