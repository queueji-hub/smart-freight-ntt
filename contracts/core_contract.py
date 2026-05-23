from typing import Dict, Any

# ================================
# CUSTOMER CONTRACT
# ================================

CUSTOMER_SCHEMA = {
    "id": int,
    "name": str,
    "company_name": str,
    "email": str,
    "tel": str,
    "is_active": int,
}

# ================================
# INVOICE CONTRACT
# ================================

INVOICE_SUMMARY_SCHEMA = {
    "billed": float,
    "subtotal": float,
    "vat": float,
    "wht": float,
    "grand_total": float,
    "outstanding": float,
}

# ================================
# SHIPMENT CONTRACT
# ================================

SHIPMENT_SCHEMA = {
    "job_no": str,
    "status": str,
    "customer_name": str,
    "etd": object,
    "eta": object,
}

# ================================
# VALIDATOR (CORE ENGINE)
# ================================

def enforce(schema: Dict[str, Any], data: Dict[str, Any], name: str):
    """
    Force every manager output to match schema
    """
    fixed = {}

    for key, typ in schema.items():
        value = data.get(key, None)

        if value is None:
            value = 0 if typ in [int, float] else ""

        try:
            fixed[key] = typ(value)
        except:
            fixed[key] = typ(0) if typ != str else ""

    return fixed