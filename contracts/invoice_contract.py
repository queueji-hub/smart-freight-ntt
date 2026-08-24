from typing import Dict, Any

INVOICE_SUMMARY_SCHEMA = {
    "amount_no_vat": float,
    "amount_vat": float,
    "total_before_vat": float,
    "total_vat_7": float,
    "total_advance": float,
    "wht_1_amount": float,
    "wht_3_amount": float,
    "wht_total": float,
    "less_vat_sub": float,
    "plus_wht_diff": float,
    "diff_amount": float,
    "grand_total": float,
    "net_payable": float,
}

def validate_invoice_summary(summary: Dict[str, Any]) -> Dict[str, float]:
    """Force contract consistency"""
    normalized = {}

    for key, typ in INVOICE_SUMMARY_SCHEMA.items():
        value = summary.get(key, 0)

        try:
            normalized[key] = typ(value)
        except Exception:
            normalized[key] = 0.0

    return normalized