import os
import sys

def main():
    from database.local_schema_compat import ensure_phase30_local_schema
    ensure_phase30_local_schema()

    from managers.shipment_manager import create_shipment, get_shipment
    from managers.profit_manager import (
        add_cost_line, get_cost_lines, get_unified_job_ledger,
        pull_ap_to_ar, create_batch_payment_voucher, create_batch_invoice_from_ar,
        get_job_document_audit, compute_line_tax_and_net
    )
    from managers.master_data_crud_manager import upsert_party, list_parties
    from managers.charge_master_manager import list_charges, list_charge_categories, get_charge
    from pdf.payment_voucher_pdf import generate_payment_voucher_pdf
    from pdf.profit_pdf import generate_profit_pdf

    user = {'id': 1, 'username': 'admin', 'tenant_id': 'default'}

    # 1. Verify Master Data Charge Items & Categories
    charges = list_charges(active_only=True)
    cats = list_charge_categories()
    print(f'1. Master Data Charge Items Loaded: {len(charges)} active charges, {len(cats)} categories')
    assert len(charges) >= 5, "Expected at least 5 standard master data charges"
    assert any(c['charge_code'] == 'OF' for c in charges)
    assert any(c['charge_code'] == 'CUS' for c in charges)

    # 2. Create a Business Party (Liner / Vendor)
    party_id = upsert_party(
        data={
            "party_code": "BP001",
            "legal_name": "Ocean Network Express (Thailand) Ltd.",
            "display_name": "ONE Line",
            "tax_id": "0105560123456",
            "country_code": "TH",
            "is_active": True,
        },
        roles=["CARRIER", "LINER", "VENDOR"],
        user=user
    )
    print(f'2. Registered Business Party: ID={party_id} (ONE Line)')

    # 3. Create a test Shipment / Job
    job_payload = {
        'customer_id': 1,
        'customer_name': 'Global Trading Logistics Co., Ltd.',
        'job_type': 'SE',
        'mode': 'SEA',
        'service_type': 'CY/CY',
        'carrier': 'Ocean Network Express',
        'vessel': 'ONE CONTINUITY',
        'voyage': '023N',
        'pol': 'Laem Chabang',
        'pod': 'Tokyo',
        'etd': '2026-08-30',
        'eta': '2026-09-12',
        'gross_weight': 24000.0,
        'cbm': 58.0,
        'package_quantity': 500,
        'status': 'Proceed'
    }
    job_no = create_shipment(job_payload, user)
    ship = get_shipment(job_no)
    ship_id = ship['id']
    print(f'3. Created Job {job_no} (Shipment ID: {ship_id})')

    # 4. Add AP Cost lines with Vendor Invoices and Business Party link
    ap1_id = add_cost_line({
        'shipment_id': ship_id,
        'cost_type': 'AP',
        'party_id': party_id,
        'matched_charge_code': 'OF',
        'category': 'Ocean Freight Cost (สายเรือ)',
        'description': 'Ocean Freight 40HC',
        'supplier': 'Ocean Network Express (Thailand) Ltd.',
        'quantity': 2.0,
        'unit': 'CTR',
        'unit_price': 1200.0,
        'currency': 'USD',
        'exchange_rate': 35.0,
        'tax_type': 'Non-VAT',
        'wht_type': 'None',
        'vendor_invoice_no': 'ONE-INV-8899',
        'vendor_invoice_date': '2026-08-24',
        'created_by': 'operation'
    })

    ap2_id = add_cost_line({
        'shipment_id': ship_id,
        'cost_type': 'AP',
        'matched_charge_code': 'THC-O',
        'category': 'Port Terminal Cost (THC / ท่าเรือ)',
        'description': 'Terminal Handling Charge (THC)',
        'supplier': 'LCB Terminal B4',
        'quantity': 2.0,
        'unit': 'CTR',
        'unit_price': 4200.0,
        'currency': 'THB',
        'exchange_rate': 1.0,
        'tax_type': 'VAT 7%',
        'wht_type': 'WHT 1%',
        'vendor_invoice_no': 'PAT-THC-4421',
        'vendor_invoice_date': '2026-08-24',
        'created_by': 'operation'
    })

    ap3_id = add_cost_line({
        'shipment_id': ship_id,
        'cost_type': 'AP',
        'matched_charge_code': 'ADV-DUTY',
        'category': 'Advance Paid on Behalf (สำรองจ่าย)',
        'description': 'Customs Import Duty (สำรองจ่ายกรมศุลกากร)',
        'supplier': 'Customs Department',
        'quantity': 1.0,
        'unit': 'SHPT',
        'unit_price': 15000.0,
        'currency': 'THB',
        'exchange_rate': 1.0,
        'tax_type': 'Advance',
        'wht_type': 'None',
        'vendor_invoice_no': 'CUST-DUTY-9901',
        'created_by': 'operation'
    })

    print(f'4. Added AP lines: AP1={ap1_id} (Inv: ONE-INV-8899), AP2={ap2_id} (Inv: PAT-THC-4421), AP3={ap3_id}')

    # 5. Test Pulling AP to AR with 15% Markup
    pulled_ar_ids = pull_ap_to_ar(
        ship_id,
        [ap1_id, ap2_id],
        markup_pct=15.0,
        target_customer='Global Trading Logistics Co., Ltd.',
        custom_desc_map={ap1_id: 'Ocean Freight 40HC (Customer Rate)', ap2_id: 'Terminal Handling Charge at Origin'},
        user=user
    )
    print(f'5. Pulled AP to AR with 15% markup -> Created AR lines: {pulled_ar_ids}')
    assert len(pulled_ar_ids) == 2

    # Verify duplicate pull prevention
    try:
        pull_ap_to_ar(ship_id, [ap1_id], markup_pct=10.0, user=user)
        assert False, "Expected ValueError on duplicate pull"
    except ValueError as exc:
        print(f'   [OK] Duplicate pull properly blocked: {exc}')

    # Add standalone pure AR line (Service fee)
    ar3_id = add_cost_line({
        'shipment_id': ship_id,
        'cost_type': 'AR',
        'matched_charge_code': 'DOC',
        'category': 'Documentation / D/O Cost',
        'description': 'Bill of Lading & Forwarder Service Fee',
        'supplier': 'Global Trading Logistics Co., Ltd.',
        'quantity': 1.0,
        'unit': 'BL',
        'unit_price': 2500.0,
        'currency': 'THB',
        'exchange_rate': 1.0,
        'tax_type': 'VAT 7%',
        'wht_type': 'WHT 3%',
        'created_by': 'operation'
    })
    print(f'   Added Standalone AR line: AR3={ar3_id}')

    # 6. Verify Unified Job Ledger calculations
    ledger = get_unified_job_ledger(ship_id)
    summary = ledger['summary']
    print(f'6. Ledger Summary: Total AP = {summary["total_ap_amount"]:,.2f} THB, Total AR = {summary["total_ar_amount"]:,.2f} THB')
    print(f'   Gross Profit = {summary["gross_profit"]:,.2f} THB (Margin: {summary["margin_pct"]}%)')
    assert summary['total_ap_amount'] > 0
    assert summary['total_ar_amount'] > 0
    assert summary['gross_profit'] > 0

    # 7. Batch Create AP Payment Voucher for AP1 & AP2 together
    pv_no = create_batch_payment_voucher(
        ship_id,
        [ap1_id, ap2_id],
        payee_name='Ocean Network Express (Thailand) Ltd.',
        voucher_type='PAYMENT_VOUCHER',
        user=user
    )
    print(f'7. Created Batch AP Payment Voucher: {pv_no}')
    ap_lines = get_cost_lines(ship_id, 'AP')
    ap1_rec = next(r for r in ap_lines if r['id'] == ap1_id)
    assert ap1_rec['payout_status'] == 'REQUESTED'
    assert ap1_rec['voucher_no'] == pv_no

    # Verify duplicate voucher creation prevention
    try:
        create_batch_payment_voucher(ship_id, [ap1_id], payee_name='Test', user=user)
        assert False, "Expected ValueError on duplicate voucher creation"
    except ValueError as exc:
        print(f'   [OK] Duplicate payment voucher properly blocked: {exc}')

    # Batch Create Advance Request for AP3 (Customs Duty)
    adv_no = create_batch_payment_voucher(
        ship_id,
        [ap3_id],
        payee_name='Customs Department',
        voucher_type='ADVANCE_REQUEST',
        user=user
    )
    print(f'   Created Advance Request Voucher: {adv_no}')

    # 8. Test Multi-Currency Invoicing: Issue Customer Invoice in USD with conversion
    all_ar_ids = pulled_ar_ids + [ar3_id]
    inv_no_usd = create_batch_invoice_from_ar(
        shipment_id=ship_id,
        ar_line_ids=all_ar_ids,
        customer_id=1,
        billing_currency='USD',
        exchange_rate=35.0,
        user=user
    )
    print(f'8. Created Multi-Currency Customer Invoice (USD): {inv_no_usd}')
    ar_lines = get_cost_lines(ship_id, 'AR')
    ar1_rec = next(r for r in ar_lines if r['id'] == pulled_ar_ids[0])
    assert ar1_rec['billing_status'] == 'INVOICED'
    assert ar1_rec['invoice_no'] == inv_no_usd

    # Verify duplicate invoicing prevention
    try:
        create_batch_invoice_from_ar(ship_id, [pulled_ar_ids[0]], user=user)
        assert False, "Expected ValueError on duplicate invoicing"
    except ValueError as exc:
        print(f'   [OK] Duplicate invoicing properly blocked: {exc}')

    # 9. Test Document Audit & Traceability
    doc_audit = get_job_document_audit(ship_id)
    print(f'9. Document Audit found {len(doc_audit["payment_vouchers"])} Payment Vouchers and {len(doc_audit["invoices"])} Invoices.')
    assert len(doc_audit['payment_vouchers']) >= 2
    assert len(doc_audit['invoices']) >= 1

    # Check vendor invoice refs on payment voucher
    pv_doc = next(v for v in doc_audit['payment_vouchers'] if v['voucher_no'] == pv_no)
    print(f'   Voucher {pv_no} Ref Invoices: {pv_doc.get("vendor_invoice_refs")}, Tax ID: {pv_doc.get("payee_tax_id")}')
    assert 'ONE-INV-8899' in str(pv_doc.get('vendor_invoice_refs'))
    assert 'PAT-THC-4421' in str(pv_doc.get('vendor_invoice_refs'))

    # 10. Test PDF Generations
    pv_pdf_path = generate_payment_voucher_pdf(
        pv_doc,
        pv_doc['items']
    )
    assert os.path.exists(pv_pdf_path)
    print(f'10. Generated Payment Voucher PDF: {pv_pdf_path}')

    ps_pdf_path = generate_profit_pdf(ship_id)
    assert os.path.exists(ps_pdf_path)
    print(f'    Generated Profit Sheet PDF: {ps_pdf_path}')

    print('\n*** ALL MASTER DATA CHARGES, DUPLICATE LOCKING, AND MULTI-CURRENCY BILLING TESTS PASSED! ***')

if __name__ == '__main__':
    main()
