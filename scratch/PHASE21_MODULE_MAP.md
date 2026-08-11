# PHASE 21 — MODULE MAP

This matrix maps each business subsystem, its canonical manager, public interface, underlying database tables, and view consumers.

| MODULE | CANONICAL OWNER | PUBLIC FUNCTIONS | DATABASE TABLES | UI CONSUMERS |
| :--- | :--- | :--- | :--- | :--- |
| **Auth** | `auth_manager.py` | `authenticate_user()`, `can_read()`, `can_write()` | `users` | `login_view.py`, `Dashboard.py` |
| **Customers** | `customer_manager.py` | `list_customers()`, `create_customer()`, `get_customer()` | `customers` | `crm_view.py`, `billing_view.py` |
| **Bookings** | `booking_manager.py` | `create_booking()`, `list_bookings()`, `convert_booking_to_job()` | `bookings` | `booking_view.py` |
| **Shipments** | `shipment_manager.py` | `create_shipment()`, `list_shipments()`, `get_shipment()`, `get_reporting_period()` | `shipments` | `shipment_view.py` |
| **Milestones** | `milestone_manager.py` | `add_milestone()`, `list_milestones()`, `update_milestone()`, `delete_milestone()` | `shipment_milestones` | `shipment_view.py` |
| **Containers** | `container_manager.py` | `add_container()`, `list_containers()`, `delete_container()`, `validate_job_readiness_for_billing()` | `containers` | `shipment_view.py` |
| **B/L** | `bl_manager.py` | `list_bls()`, `create_bl()`, `get_bl()`, `add_bl_container()` | `bills_of_lading` | `bl_view.py` |
| **Finance** | `finance_manager.py` | `get_outstanding_summary()`, `get_ar_aging_report()` | `invoices`, `job_costs` | `finance.py`, `billing_view.py` |
| **Reporting** | `report_manager.py` | `get_sales_performance_report()`, `get_company_monthly_performance()` | `shipments`, `job_costs` | `reports_view.py`, `dashboard_view.py` |
| **Month End** | `month_end_manager.py` | `get_month_end_summary()`, `close_month()` | `shipments` | `dashboard_view.py` |
