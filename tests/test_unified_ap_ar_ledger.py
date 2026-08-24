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
    from pdf.payment_voucher_pdf import generate_payment_voucher_pdf
    from pdf.profit_pdf import generate_profit_pdf

    user = {'id': 1, 'username': 'admin', 'tenant_id': 'default'}

    # 1. Create a test Shipment / Job
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
    print(f'1. Created Job {job_no} (Shipment ID: {ship_id})')

    # 2. Add AP Cost lines (Ocean Freight USD, THC THB, Customs Clearance THB with WHT 3%, Port Advance Disbursement)
    ap1_id = add_cost_line({
        'shipment_id': ship_id,
        'cost_type': 'AP',
        'category': 'Ocean Freight Cost (สายเรือ)',
        'description': 'Ocean Freight 40HC',
        'supplier': 'ONE Line',
        'quantity': 2.0,
        'unit': 'CTR',
        'unit_price': 1200.0,
        'currency': 'USD',
        'exchange_rate': 35.0,
        'tax_type': 'Non-VAT',
        'wht_type': 'None',
        'created_by': 'operation'
    })

    ap2_id = add_cost_line({
        'shipment_id': ship_id,
        'cost_type': 'AP',
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
        'created_by': 'operation'
    })

    ap3_id = add_cost_line({
        'shipment_id': ship_id,
        'cost_type': 'AP',
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
        'created_by': 'operation'
    })

    print(f'2. Added AP lines: AP1={ap1_id}, AP2={ap2_id}, AP3={ap3_id}')

    # 3. Test Pulling AP to AR with 15% Markup
    pulled_ar_ids = pull_ap_to_ar(
        ship_id,
        [ap1_id, ap2_id],
        markup_pct=15.0,
        target_customer='Global Trading Logistics Co., Ltd.',
        custom_desc_map={ap1_id: 'Ocean Freight 40HC (Customer Rate)', ap2_id: 'Terminal Handling Charge at Origin'},
        user=user
    )
    print(f'3. Pulled AP to AR with 15% markup -> Created AR lines: {pulled_ar_ids}')
    assert len(pulled_ar_ids) == 2

    # Add standalone pure AR line (Service fee)
    ar3_id = add_cost_line({
        'shipment_id': ship_id,
        'cost_type': 'AR',
        'category': 'Documentation & D/O Fee',
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

    # 4. Verify Unified Job Ledger calculations
    ledger = get_unified_job_ledger(ship_id)
    summary = ledger['summary']
    print(f'4. Ledger Summary: Total AP = {summary["total_ap_amount"]:,.2f} THB, Total AR = {summary["total_ar_amount"]:,.2f} THB')
    print(f'   Gross Profit = {summary["gross_profit"]:,.2f} THB (Margin: {summary["margin_pct"]}%)')
    assert summary['total_ap_amount'] > 0
    assert summary['total_ar_amount'] > 0
    assert summary['gross_profit'] > 0

    # 5. Batch Create AP Payment Voucher for AP2 (THC)
    pv_no = create_batch_payment_voucher(
        ship_id,
        [ap2_id],
        payee_name='LCB Terminal B4',
        voucher_type='PAYMENT_VOUCHER',
        user=user
    )
    print(f'5. Created Batch AP Payment Voucher: {pv_no}')
    ap_lines = get_cost_lines(ship_id, 'AP')
    ap2_rec = next(r for r in ap_lines if r['id'] == ap2_id)
    assert ap2_rec['payout_status'] == 'REQUESTED'
    assert ap2_rec['voucher_no'] == pv_no

    # Batch Create Advance Request for AP3 (Customs Duty)
    adv_no = create_batch_payment_voucher(
        ship_id,
        [ap3_id],
        payee_name='Customs Department',
        voucher_type='ADVANCE_REQUEST',
        user=user
    )
    print(f'   Created Advance Request Voucher: {adv_no}')

    # 6. Batch Create AR Invoice for Pulled AR lines
    inv_no = create_batch_invoice_from_ar(
        ship_id,
        pulled_ar_ids,
        customer_id=1,
        user=user
    )
    print(f'6. Created Batch Customer Invoice: {inv_no}')
    ar_lines = get_cost_lines(ship_id, 'AR')
    ar1_rec = next(r for r in ar_lines if r['id'] == pulled_ar_ids[0])
    assert ar1_rec['billing_status'] == 'INVOICED'
    assert ar1_rec['invoice_no'] == inv_no

    # 7. Test Document Audit & Traceability
    doc_audit = get_job_document_audit(ship_id)
    print(f'7. Document Audit found {len(doc_audit["payment_vouchers"])} Payment Vouchers and {len(doc_audit["invoices"])} Invoices.')
    assert len(doc_audit['payment_vouchers']) >= 2
    assert len(doc_audit['invoices']) >= 1

    # 8. Test PDF Generations
    pv_pdf_path = generate_payment_voucher_pdf(
        doc_audit['payment_vouchers'][0],
        doc_audit['payment_vouchers'][0]['items']
    )
    assert os.path.exists(pv_pdf_path)
    print(f'8. Generated Payment Voucher PDF: {pv_pdf_path}')

    ps_pdf_path = generate_profit_pdf(ship_id)
    assert os.path.exists(ps_pdf_path)
    print(f'   Generated Profit Sheet PDF: {ps_pdf_path}')

    print('\n*** UNIFIED AP/AR LEDGER & DOCUMENT AUDIT TESTS PASSED! ***')

if __name__ == '__main__':
    main()
