import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from database.connection import get_connection

def verify_schema():
    expected_tables = [
        "users", "customers", "vendors", "quotations", "bookings", "shipments", 
        "containers", "bills_of_lading", "invoices", "documents", "document_versions", 
        "document_links", "physical_documents", "doc_counters", "document_counters",
        "job_costs", "ap_vouchers", "invoice_payments", "commissions", 
        "transport_orders", "regulatory_submissions", "audit_logs", "email_log"
    ]
    
    expected_columns = {
        "shipments": ["tenant_id", "job_no", "reporting_date", "reporting_month", "reporting_year", "financial_status", "document_status", "mode", "closed_at", "closed_by"],
        "documents": ["tenant_id", "document_no"],
        "document_versions": ["document_id", "version_number", "storage_key"],
        "job_costs": ["cost_status"],
        "quotations": ["quotation_no"],
        "invoices": ["doc_no"]
    }
    
    actual_tables = []
    columns_info = {}
    
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
            """)
            actual_tables = [row['table_name'] for row in cur.fetchall()]
            
            for table in expected_columns.keys():
                cur.execute("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_schema = 'public' AND table_name = %s
                """, (table,))
                columns_info[table] = [row['column_name'] for row in cur.fetchall()]

    with open("scratch/PHASE20_2_SCHEMA_REALITY_REPORT.md", "w") as f:
        f.write("# PHASE 20.2 - SCHEMA REALITY REPORT\n\n")
        f.write("## Tables\n")
        f.write("| TABLE | EXPECTED | ACTUAL | STATUS |\n")
        f.write("|---|---|---|---|\n")
        for t in expected_tables:
            status = "PASS" if t in actual_tables else "MISSING"
            f.write(f"| {t} | YES | {'YES' if t in actual_tables else 'NO'} | {status} |\n")
            
        f.write("\n## Critical Columns\n")
        f.write("| TABLE | COLUMN | EXPECTED | ACTUAL | STATUS |\n")
        f.write("|---|---|---|---|---|\n")
        for table, cols in expected_columns.items():
            actual_cols = columns_info.get(table, [])
            for c in cols:
                status = "PASS" if c in actual_cols else "MISSING"
                f.write(f"| {table} | {c} | YES | {'YES' if c in actual_cols else 'NO'} | {status} |\n")
                
    print("Schema verification complete. Report written to scratch/PHASE20_2_SCHEMA_REALITY_REPORT.md")

if __name__ == "__main__":
    verify_schema()
