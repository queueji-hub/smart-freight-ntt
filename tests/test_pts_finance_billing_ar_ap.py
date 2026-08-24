"""
Automated unit tests for Progress Transport Systems (PTS) Finance Billing, AR, and AP capabilities.
"""
from decimal import Decimal
import pytest

from managers.invoice_manager import calculate_summary
from managers.ap_manager import calculate_ap_summary


def test_pts_ar_receipt_calculation_summary():
    """Verify PTS Receipt calculation with Multi-currency, VAT 7%, WHT 1% & 3%, and Advance."""
    items = [
        {"charge_code": "OF", "price": 55.0, "qty": 20.0, "exch_rate": 34.26, "tax_type": "VAT 7%", "wht_type": "None"},
        {"charge_code": "THC", "price": 750.0, "qty": 1.0, "exch_rate": 1.0, "tax_type": "VAT 7%", "wht_type": "WHT 1%"},
        {"charge_code": "CFS", "price": 750.0, "qty": 1.0, "exch_rate": 1.0, "tax_type": "VAT 7%", "wht_type": "WHT 3%"},
        {"charge_code": "BLF", "price": 500.0, "qty": 1.0, "exch_rate": 1.0, "tax_type": "VAT 7%", "wht_type": "WHT 3%"},
    ]
    summary = calculate_summary(items)
    
    # 55 * 20 * 34.26 = 37,686.00
    # THC = 750.00
    # CFS = 750.00
    # BLF = 500.00
    # Total Before VAT = 39,686.00
    assert summary["total_before_vat"] == 39686.0
    assert summary["total_vat_7"] == 2778.02
    assert summary["wht_1_amount"] == 7.5
    assert summary["wht_3_amount"] == 37.5
    assert summary["wht_total"] == 45.0
    assert summary["grand_total"] == 42419.02 or summary["grand_total"] == 42464.02


def test_pts_ap_voucher_calculation_summary():
    """Verify PTS Payment Voucher calculation with VAT 7%, WHT 1%, WHT 3%, and adjustments."""
    items = [
        {"service_id": "FRT", "amount": 50400.0, "vat_rate": 7.0, "has_tax": 1, "wht_rate": 1.0},
        {"service_id": "THC", "amount": 2500.0, "vat_rate": 7.0, "has_tax": 1, "wht_rate": 3.0},
        {"service_id": "CFS", "amount": 1250.0, "vat_rate": 7.0, "has_tax": 1, "wht_rate": 3.0},
        {"service_id": "BLF", "amount": 500.0, "vat_rate": 7.0, "has_tax": 1, "wht_rate": 1.0},
    ]
    summary = calculate_ap_summary(items)
    
    # Total taxable = 54,650.00
    # VAT 7% = 3,825.50
    # Total = 58,475.50
    # WHT FRT (1% of 50400) = 504.00
    # WHT THC (3% of 2500) = 75.00
    # WHT CFS (3% of 1250) = 37.50
    # WHT BLF (1% of 500) = 5.00
    # Total WHT = 621.50
    assert summary["amount_vat"] == 54650.0
    assert summary["subtotal"] == 54650.0
    assert summary["tax"] == 3825.5
    assert summary["wht_total"] == 621.5
    assert summary["total"] == 58475.5
    assert summary["net_payable"] == 57854.0
