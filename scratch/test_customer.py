import sys
import os

# Add workspace root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from managers.customer_manager import list_customers

try:
    print("Attempting to list customers...")
    res = list_customers()
    print(f"Success! Found {len(res)} customers.")
except Exception as e:
    import traceback
    print("Failed to list customers:")
    traceback.print_exc()
