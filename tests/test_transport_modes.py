import os
import sys

def main():
    from database.local_schema_compat import ensure_phase30_local_schema
    ensure_phase30_local_schema()
    from managers.booking_manager import (
        create_booking, get_booking, update_booking, convert_booking_to_job,
        duplicate_booking, lock_booking, unlock_booking
    )
    from managers.shipment_manager import get_shipment
    from pdf.booking_pdf import generate_booking_pdf
    from managers.customer_master_manager import list_customers

    customers = list_customers()
    cid = customers[0]['id'] if customers else 1
    cname = customers[0].get('display_name') if customers else 'Test Customer'
    user = {'id': 1, 'username': 'admin', 'tenant_id': 'default'}

    # 1. Create Sea FCL Booking & Convert Directly to Job (No Submit/Confirm required)
    b1_data = {
        'job_type': 'SE',
        'mode': 'SEA',
        'cargo_type': 'FCL',
        'service_term': 'CY/CY',
        'customer_id': cid,
        'customer_name': cname,
        'carrier_booking_no': 'ONEY-DIRECT-001',
        'pol': 'Laem Chabang',
        'pod': 'Tokyo',
        'transhipment_port': 'Singapore',
        'liner': 'Ocean Network Express',
        'vessel': 'ONE CONTINUITY',
        'voyage': '023N',
        'mother_vessel': 'ONE OLYMPUS',
        'mother_voyage': '055E',
        'container_summary': "40'HC x 2 | 20'GP x 1",
        'gross_weight': 42000.0,
        'cy_place': 'LCB Terminal B4',
        'cy_date': '2026-08-30',
        'return_place': 'Lat Krabang ICD',
        'customer_return_date': '2026-09-05',
    }
    b1_no = create_booking(b1_data, user)
    print('1. Created Booking:', b1_no)

    # Convert directly to Job
    job_no = convert_booking_to_job(b1_no, user)
    print('2. Converted directly to Job:', job_no)
    ship = get_shipment(job_no)
    assert ship is not None
    print('   Verified Shipment exists with Vessel:', ship.get('vessel'))

    # 3. Test Duplicate Booking
    dup_bk = duplicate_booking(b1_no, user)
    print('3. Duplicated Booking:', dup_bk)
    dup_doc = get_booking(dup_bk)
    assert dup_doc['carrier_booking_no'] == 'ONEY-DIRECT-001'
    assert dup_doc['pol'] == 'Laem Chabang'
    assert dup_doc['job_no'] is None
    print('   Verified Duplicated Booking has cloned data and cleared job_no.')

    # 4. Test Lock and Unlock
    lock_booking(b1_no, user)
    locked_doc = get_booking(b1_no)
    assert bool(locked_doc.get('is_locked')) is True
    print('4. Booking locked successfully.')

    # Attempt to update while locked should raise ValueError
    try:
        update_booking(b1_no, {'vessel': 'SHOULD_FAIL'})
        print('   Error: Update should have failed while locked!')
    except ValueError as exc:
        print('   Verified update blocked while locked:', str(exc))

    # Unlock and update revised schedule
    unlock_booking(b1_no, user)
    unlocked_doc = get_booking(b1_no)
    assert bool(unlocked_doc.get('is_locked')) is False
    print('5. Booking unlocked successfully.')

    # 6. Revise Vessel and dates, and verify automatic sync to linked Job!
    update_booking(b1_no, {
        'vessel': 'ONE REVISED VESSEL',
        'voyage': '099N',
        'cy_place': 'LCB Terminal B3 REVISED'
    }, user.get('tenant_id'))
    print('6. Booking revised while linked to Job.')

    revised_ship = get_shipment(job_no)
    print('   Verified linked Job synchronized vessel:', revised_ship.get('vessel'), 'voyage:', revised_ship.get('voyage'))
    assert revised_ship.get('vessel') == 'ONE REVISED VESSEL'
    assert revised_ship.get('voyage') == '099N'

    print('\n*** ALL TESTS PASSED SUCCESSFULLY! ***')

if __name__ == '__main__':
    main()
