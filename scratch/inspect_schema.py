import sqlite3
import os
from pathlib import Path

db_path = Path('c:/Users/User/Desktop/Got/Smart Freight NTT/data/smart_freight.db')

if not db_path.exists():
    db_path = Path('c:/Users/User/Desktop/Got/Smart Freight NTT,/data/smart_freight.db')

try:
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    
    cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [r[0] for r in cur.fetchall()]
    
    report = []
    
    for table in tables:
        cur.execute(f"PRAGMA table_info({table});")
        columns = {r[1]: r[2] for r in cur.fetchall()}
        
        cur.execute(f"SELECT COUNT(*) FROM {table};")
        count = cur.fetchone()[0]
        
        has_tenant = 'tenant_id' in columns
        report.append(f"Table: {table} | Rows: {count} | Has tenant_id: {has_tenant}")
        
    with open('scratch/tenant_schema_reality.md', 'w') as f:
        f.write("# TENANT SCHEMA REALITY\n\n")
        for r in report:
            f.write(r + "\n")
except Exception as e:
    with open('scratch/tenant_schema_reality.md', 'w') as f:
        f.write(f"Error: {e}")
