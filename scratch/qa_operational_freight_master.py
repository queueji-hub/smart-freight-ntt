import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Mock tenant context
import managers.tenant_context
managers.tenant_context.get_current_tenant_id = lambda: "TENANT_QA_OPERATIONAL_83"

from managers.shipment_manager import create_shipment, add_milestone
from managers.profit_manager import add_cost_line, get_profit_summary
from managers.transport_manager import create_transport_order
from managers.regulatory_manager import create_regulatory_submission
from managers.physical_document_manager import register_physical_document
from managers.commission_manager import create_commission_draft, get_sales_performance
from managers.month_end_manager import get_month_end_summary

def run_qa():
    print("--- STARTING D83 OPERATIONAL MASTER QA ---")
    
    # 1. EXPORT JOB (ETD rule)
    export_job = create_shipment({
        "job_type": "EXPORT SEA FCL",
        "customer_name": "ABC Global",
        "etd": "2026-09-15",
        "sales_person": "Sales_01"
    })
    print(f"Created EXPORT Job: {export_job}")
    
    # 2. IMPORT JOB (ETA rule)
    import_job = create_shipment({
        "job_type": "IMPORT AIR",
        "customer_name": "XYZ Import",
        "eta": "2026-10-05",
        "sales_person": "Sales_02"
    })
    print(f"Created IMPORT Job: {import_job}")
    
    # 3. Add Milestones
    add_milestone(export_job, "BK_CONF", "Booking Confirmed", "2026-09-01")
    print(f"Added Milestone to {export_job}")
    
    # 4. Job Profitability (Accrued vs Actual)
    add_cost_line({
        "shipment_id": 1, # Mock ID 
        "cost_type": "AR",
        "cost_status": "ACTUAL",
        "amount": 5000,
        "currency": "USD"
    })
    add_cost_line({
        "shipment_id": 1,
        "cost_type": "AP",
        "cost_status": "ACCRUED",
        "amount": 3000,
        "currency": "USD"
    })
    profit = get_profit_summary(1)
    print(f"Profit Summary (ID 1): AR Actual={profit['ar_actual']}, AP Accrued={profit['ap_accrued']}")
    
    # 5. Transport Order
    to = create_transport_order({
        "job_no": export_job,
        "pickup_location": "Factory A",
        "delivery_location": "Port B"
    })
    print(f"Created Transport Order: {to}")
    
    # 6. Regulatory Submission
    reg = create_regulatory_submission({
        "submission_type": "AMS",
        "job_no": export_job,
        "country": "US"
    })
    print(f"Registered Regulatory Submission: {reg}")
    
    # 7. Physical Document Control
    phys = register_physical_document({
        "job_no": import_job,
        "document_type": "Original BL",
        "is_original": True
    })
    print(f"Registered Physical Document Custody: {phys}")
    
    # 8. Commission & Month-End (Export should be under 2026-09, Import under 2026-10)
    comm_id = create_commission_draft(export_job, "Sales_01", basis="Gross Profit", rate=10)
    print(f"Generated Commission Draft ID: {comm_id}")
    
    sales_9 = get_sales_performance("2026-09")
    sales_10 = get_sales_performance("2026-10")
    print(f"2026-09 Sales Performance (Should contain export): {sales_9}")
    print(f"2026-10 Sales Performance (Should contain import): {sales_10}")
    
    month_end = get_month_end_summary("2026-09")
    print(f"Month-End Summary for 2026-09: {month_end['job_stats']}")
    
    print("--- D83 OPERATIONAL MASTER QA COMPLETED SUCCESSFULLY ---")

if __name__ == '__main__':
    run_qa()
