"""
QA: Finance Manager — Cross-Tenant Isolation + Decimal Precision
Tests that TENANT_B cannot access TENANT_A's financial data.
Tests that all monetary calculations use Decimal precision.
"""
import os, sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from database.connection import init_database, get_connection
from managers.finance_manager import (
    create_invoice, list_invoices, record_payment,
    get_outstanding_summary, get_invoice, calculate_summary
)
from unittest.mock import patch
from decimal import Decimal


def test_decimal_precision():
    print("=" * 60)
    print("TEST 1: Decimal Precision in calculate_summary")
    print("=" * 60)
    
    items = [
        {"amount": "333.33", "tax_type": "VAT 7%", "wht_type": "NONE"},
        {"amount": "333.33", "tax_type": "VAT 7%", "wht_type": "NONE"},
        {"amount": "333.33", "tax_type": "VAT 7%", "wht_type": "NONE"},
    ]
    
    summary = calculate_summary(items)
    
    # 333.33 * 3 = 999.99
    assert abs(summary["total_before_vat"] - 999.99) < 0.01, f"Subtotal wrong: {summary['total_before_vat']}"
    
    # VAT: 333.33 * 0.07 = 23.33 (rounded) * 3 = 69.99
    expected_vat = 23.33 * 3  # 69.99
    assert abs(summary["total_vat_7"] - expected_vat) < 0.02, f"VAT wrong: {summary['total_vat_7']}"
    
    print(f"  Subtotal: {summary['total_before_vat']}")
    print(f"  VAT: {summary['total_vat_7']}")
    print(f"  WHT: {summary['wht_total']}")
    print(f"  Grand Total: {summary['grand_total']}")
    print("PASS: Decimal precision verified.\n")


def test_tenant_isolation():
    print("=" * 60)
    print("TEST 2: Cross-Tenant Financial Isolation")
    print("=" * 60)
    
    user_a = {"id": 1, "username": "test_user_a"}
    user_b = {"id": 2, "username": "test_user_b"}
    
    # TENANT_A creates an invoice
    with patch('managers.finance_manager.get_current_tenant_id', return_value='FIN_TENANT_A'):
        with patch('managers.document_numbering_service.get_current_tenant_id', return_value='FIN_TENANT_A'):
            doc_no = create_invoice(
                tenant_id="FIN_TENANT_A",
                data={
                    "customer_name": "Alpha Corp",
                    "issue_date": "2026-08-10",
                    "due_date": "2026-09-10"
                },
                items=[
                    {"description": "Ocean Freight", "amount": "5000.00", "quantity": 1, "unit_price": 5000}
                ],
                user=user_a
            )
            print(f"  TENANT_A created invoice: {doc_no}")
            
            # TENANT_A can list it
            invoices_a = list_invoices()
            found = [i for i in invoices_a if i["doc_no"] == doc_no]
            assert len(found) == 1, "TENANT_A should see its own invoice"
            invoice_id = found[0]["id"]
            print(f"  TENANT_A can list own invoice: OK (id={invoice_id})")
            
            # TENANT_A can get it
            detail = get_invoice(invoice_id)
            assert detail is not None
            assert detail["doc_no"] == doc_no
            print(f"  TENANT_A can get own invoice detail: OK")
            
            # TENANT_A summary
            summary_a = get_outstanding_summary()
            assert summary_a["outstanding"] > 0
            print(f"  TENANT_A outstanding: {summary_a['outstanding']}")
    
    # Switch to TENANT_B
    with patch('managers.finance_manager.get_current_tenant_id', return_value='FIN_TENANT_B'):
        with patch('managers.document_numbering_service.get_current_tenant_id', return_value='FIN_TENANT_B'):
            # TENANT_B must NOT see TENANT_A's invoices
            invoices_b = list_invoices()
            leaked = [i for i in invoices_b if i.get("doc_no") == doc_no]
            assert len(leaked) == 0, "TENANT_B should NOT see TENANT_A's invoice!"
            print(f"  TENANT_B list_invoices: [] (correct)")
            
            # TENANT_B must NOT get TENANT_A's invoice by ID
            detail_b = get_invoice(invoice_id)
            assert detail_b is None, "TENANT_B should NOT get TENANT_A's invoice by ID!"
            print(f"  TENANT_B get_invoice({invoice_id}): None (correct)")
            
            # TENANT_B must NOT record payment against TENANT_A's invoice
            try:
                record_payment(
                    invoice_id=invoice_id,
                    amount=1000.0,
                    user=user_b
                )
                assert False, "TENANT_B should NOT be able to pay TENANT_A's invoice!"
            except (ValueError, RuntimeError) as e:
                print(f"  TENANT_B record_payment blocked: {e}")
            
            # TENANT_B summary must not include TENANT_A's data
            summary_b = get_outstanding_summary()
            # Since TENANT_B has no invoices, outstanding should be 0
            assert summary_b["outstanding"] == 0.0, f"TENANT_B outstanding should be 0, got {summary_b['outstanding']}"
            print(f"  TENANT_B outstanding: {summary_b['outstanding']} (correct)")
    
    print("PASS: Cross-tenant financial isolation verified.\n")


def test_payment_decimal():
    print("=" * 60)
    print("TEST 3: Payment with Decimal Precision")
    print("=" * 60)
    
    user = {"id": 1, "username": "test_pay"}
    
    with patch('managers.finance_manager.get_current_tenant_id', return_value='FIN_PAY_TENANT'):
        with patch('managers.document_numbering_service.get_current_tenant_id', return_value='FIN_PAY_TENANT'):
            # Create invoice for 1000.00
            doc_no = create_invoice(
                tenant_id="FIN_PAY_TENANT",
                data={
                    "customer_name": "Pay Test Corp",
                    "issue_date": "2026-08-10",
                    "due_date": "2026-09-10"
                },
                items=[
                    {"description": "Freight", "amount": "1000.00", "quantity": 1, "unit_price": 1000, "tax_type": "NON_VAT"}
                ],
                user=user
            )
            print(f"  Created: {doc_no}")
            
            invoices = list_invoices()
            inv = [i for i in invoices if i["doc_no"] == doc_no][0]
            inv_id = inv["id"]
            
            # Pay 333.33
            record_payment(invoice_id=inv_id, amount=333.33, user=user)
            inv_after = get_invoice(inv_id)
            remaining = float(inv_after["outstanding"])
            print(f"  After payment of 333.33: outstanding = {remaining}")
            assert abs(remaining - 666.67) < 0.01, f"Expected ~666.67, got {remaining}"
            
            # Pay another 333.33
            record_payment(invoice_id=inv_id, amount=333.33, user=user)
            inv_after2 = get_invoice(inv_id)
            remaining2 = float(inv_after2["outstanding"])
            print(f"  After payment of 333.33: outstanding = {remaining2}")
            assert abs(remaining2 - 333.34) < 0.01, f"Expected ~333.34, got {remaining2}"
            
            # Final payment
            record_payment(invoice_id=inv_id, amount=333.34, user=user)
            inv_final = get_invoice(inv_id)
            remaining_final = float(inv_final["outstanding"])
            print(f"  After final payment of 333.34: outstanding = {remaining_final}")
            assert remaining_final == 0.0, f"Expected 0.0, got {remaining_final}"
            assert inv_final["status"] == "PAID"
            print(f"  Status: {inv_final['status']}")
    
    print("PASS: Payment Decimal precision verified.\n")


if __name__ == "__main__":
    init_database()
    test_decimal_precision()
    test_tenant_isolation()
    test_payment_decimal()
    
    print("=" * 60)
    print("ALL FINANCE ISOLATION + PRECISION TESTS PASSED")
    print("=" * 60)
