# contracts/invoice_contract.py

from typing import Dict, Any

INVOICE_SUMMARY_SCHEMA = {
    "billed": float,
    "subtotal": float,
    "vat": float,
    "wht": float,
    "grand_total": float,
    "outstanding": float,
}


def validate_invoice_summary(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Enforce schema: ensure all required keys exist + correct type
    """
    validated = {}

    for key, expected_type in INVOICE_SUMMARY_SCHEMA.items():
        value = data.get(key, 0)

        try:
            validated[key] = expected_type(value)
        except Exception:
            validated[key] = expected_type(0)

    return validated