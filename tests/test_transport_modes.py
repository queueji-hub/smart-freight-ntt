import os
import sys

def main():
    from database.local_schema_compat import ensure_phase30_local_schema
    ensure_phase30_local_schema()
    from managers.booking_manager import create_booking, get_booking, update_booking, convert_booking_to_job
    from pdf.booking_pdf import generate_booking_pdf
    from managers.customer_master_manager import list_customers

    customers = list_customers()
    cid = customers[0]['id'] if customers else 1
    cname = customers[0].get('display_name') if customers else 'Test Customer'
    user = {'id': 1, 'username': 'admin', 'tenant_id': 'default'}

    # 1. Test Sea FCL
    b1_data = {
        'job_type': 'SE',
        'mode': 'SEA',
        'cargo_type': 'FCL',
        'service_term': 'CY/CY',
        'customer_id': cid,
        'customer_name': cname,
        'carrier_booking_no': 'ONEY-BKK-00123',
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
    print('Created Sea FCL Booking:', b1_no)
    update_booking(b1_no, {'status': 'SUBMITTED'}, user.get('tenant_id'))
    update_booking(b1_no, {'status': 'CONFIRMED'}, user.get('tenant_id'))
    p1 = generate_booking_pdf(b1_no)
    print('Generated Sea FCL PDF:', p1)
    j1 = convert_booking_to_job(b1_no, user)
    print('Converted Sea FCL to Job:', j1)

    # 2. Test Sea LCL
    b2_data = {
        'job_type': 'SE',
        'mode': 'SEA',
        'cargo_type': 'LCL',
        'service_term': 'CFS/CFS',
        'customer_id': cid,
        'customer_name': cname,
        'carrier_booking_no': 'VG-BKK-9988',
        'pol': 'Bangkok CFS',
        'pod': 'Singapore',
        'transhipment_port': None,
        'liner': 'Vanguard Logistics',
        'vessel': 'SITC BANGKOK',
        'voyage': '2411S',
        'package_qty': 45,
        'package_unit': 'Cartons',
        'gross_weight': 1500.0,
        'measurement_cbm': 4.85,
        'cfs_place': 'PAT CFS Warehouse No. 3',
        'cfs_date': '2026-08-28',
    }
    b2_no = create_booking(b2_data, user)
    print('Created Sea LCL Booking:', b2_no)
    update_booking(b2_no, {'status': 'SUBMITTED'}, user.get('tenant_id'))
    update_booking(b2_no, {'status': 'CONFIRMED'}, user.get('tenant_id'))
    p2 = generate_booking_pdf(b2_no)
    print('Generated Sea LCL PDF:', p2)
    j2 = convert_booking_to_job(b2_no, user)
    print('Converted Sea LCL to Job:', j2)

    # 3. Test Air Freight
    b3_data = {
        'job_type': 'AE',
        'mode': 'AIR',
        'cargo_type': 'AIR',
        'service_term': 'AIR',
        'customer_id': cid,
        'customer_name': cname,
        'carrier_booking_no': 'TG-RES-45678',
        'mawb_no': '217-12345678',
        'hawb_no': 'HAWB-889900',
        'pol': 'BKK - Suvarnabhumi Airport',
        'pod': 'NRT - Tokyo Narita Airport',
        'transhipment_port': 'SIN',
        'carrier': 'Thai Airways',
        'flight_no': 'TG910',
        'flight_date': '2026-08-29',
        'package_qty': 12,
        'package_unit': 'Boxes',
        'gross_weight': 250.0,
        'measurement_cbm': 1.80,
        'chargeable_weight': 300.6,
        'cfs_place': 'TG Cargo Terminal BKK',
        'cfs_date': '2026-08-28',
    }
    b3_no = create_booking(b3_data, user)
    print('Created Air Booking:', b3_no)
    update_booking(b3_no, {'status': 'SUBMITTED'}, user.get('tenant_id'))
    update_booking(b3_no, {'status': 'CONFIRMED'}, user.get('tenant_id'))
    p3 = generate_booking_pdf(b3_no)
    print('Generated Air PDF:', p3)
    j3 = convert_booking_to_job(b3_no, user)
    print('Converted Air to Job:', j3)

    # 4. Test Truck / Cross-Border
    b4_data = {
        'job_type': 'TE',
        'mode': 'TRUCK',
        'cargo_type': 'TRUCK',
        'service_term': 'DOOR-TO-DOOR',
        'customer_id': cid,
        'customer_name': cname,
        'carrier_booking_no': 'TRK-NTT-7766',
        'pol': 'Factory Bangna KM.23',
        'pod': 'Vientiane Logistics Park, Laos',
        'transhipment_port': 'ด่านสะพานมิตรภาพไทย-ลาว (หนองคาย)',
        'carrier': 'NTT Cross-Border Transport',
        'truck_type': "Trailer 40'",
        'truck_plate': '70-9988 กทม / 71-1122',
        'driver_name': 'นายสมศักดิ์ ขนส่ง',
        'driver_phone': '089-999-8888',
        'loading_date': '2026-08-27',
        'delivery_date': '2026-08-29',
        'package_qty': 20,
        'package_unit': 'Pallets',
        'gross_weight': 18000.0,
    }
    b4_no = create_booking(b4_data, user)
    print('Created Truck Booking:', b4_no)
    update_booking(b4_no, {'status': 'SUBMITTED'}, user.get('tenant_id'))
    update_booking(b4_no, {'status': 'CONFIRMED'}, user.get('tenant_id'))
    p4 = generate_booking_pdf(b4_no)
    print('Generated Truck PDF:', p4)
    j4 = convert_booking_to_job(b4_no, user)
    print('Converted Truck to Job:', j4)

if __name__ == '__main__':
    main()
