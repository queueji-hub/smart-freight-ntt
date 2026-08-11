import sys
import os

# Add workspace root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.connection import get_connection

def list_all_tables():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
            """)
            print("Tables in public schema:")
            for r in cur.fetchall():
                print(f" - {r['table_name']}")

if __name__ == "__main__":
    list_all_tables()
