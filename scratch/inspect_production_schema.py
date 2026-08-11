import sys
import os

# Add workspace root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.connection import get_connection

def inspect_schema():
    with get_connection() as conn:
        # Check if it is SQLite
        if conn.__class__.__name__ == "SQLiteConnAdapter":
            print("Operating in SQLite local fallback. Cannot inspect production Supabase schema.")
            return

        with conn.cursor() as cur:
            cur.execute("""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_name = 'shipment_milestones'
            """)
            rows = cur.fetchall()
            print("shipment_milestones columns:")
            for r in rows:
                print(f" - {r['column_name']}: {r['data_type']}")

if __name__ == "__main__":
    inspect_schema()
