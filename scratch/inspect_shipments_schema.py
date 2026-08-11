import sys
import os

# Add workspace root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.connection import get_connection

def inspect_shipments_cols():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_name = 'shipments'
            """)
            print("shipments columns:")
            for r in cur.fetchall():
                print(f" - {r['column_name']}: {r['data_type']}")

if __name__ == "__main__":
    inspect_shipments_cols()
