import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from database.connection import init_database, get_connection

def test_connection():
    print("=== Testing Database Connection ===")
    try:
        init_database()
        print("[PASS] init_database() executed without exception.")
    except Exception as e:
        print(f"[FAIL] init_database() threw exception: {type(e).__name__} - {str(e)}")

    print("\n=== Testing get_connection() ===")
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
                row = cur.fetchone()
                print(f"[PASS] get_connection() succeeded. SELECT 1 returned: {row}")
    except Exception as e:
        print(f"[FAIL] get_connection() threw exception: {type(e).__name__} - {str(e)}")

if __name__ == "__main__":
    test_connection()
