from typing import Dict, Any, List, Optional
from database.connection import get_connection
from managers.tenant_context import get_current_tenant_id
from managers.document_numbering_service import generate_document_number

def create_transport_order(data: Dict[str, Any]) -> str:
    tenant_id = get_current_tenant_id()
    
    order_type = data.get("order_type", "TRUCKING").upper()
    prefix = "TO" if order_type == "TRUCKING" else "MO"
    transport_order_no = generate_document_number(prefix, None)
    
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO transport_orders (
                    tenant_id, transport_order_no, order_type, job_no, 
                    customer_name, vendor_name, pickup_location, delivery_location, 
                    pickup_time, delivery_time, truck_type, vehicle_no, driver_name, 
                    container_no, cargo_details, special_instructions, status
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                tenant_id,
                transport_order_no,
                order_type,
                data.get("job_no"),
                data.get("customer_name"),
                data.get("vendor_name"),
                data.get("pickup_location"),
                data.get("delivery_location"),
                data.get("pickup_time"),
                data.get("delivery_time"),
                data.get("truck_type"),
                data.get("vehicle_no"),
                data.get("driver_name"),
                data.get("container_no"),
                data.get("cargo_details"),
                data.get("special_instructions"),
                data.get("status", "DRAFT")
            ))
            conn.commit()
            return transport_order_no

def get_transport_order(order_no: str) -> Optional[Dict[str, Any]]:
    tenant_id = get_current_tenant_id()
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM transport_orders WHERE transport_order_no=%s AND tenant_id=%s", 
                        (order_no, tenant_id))
            row = cur.fetchone()
            if row:
                return dict(row)
            return None

def update_transport_status(order_no: str, status: str, pod_received: bool = False) -> bool:
    tenant_id = get_current_tenant_id()
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE transport_orders 
                SET status=%s, pod_received=%s
                WHERE transport_order_no=%s AND tenant_id=%s
            """, (status, pod_received, order_no, tenant_id))
            conn.commit()
            return cur.rowcount > 0

def list_transport_orders_by_job(job_no: str) -> List[Dict[str, Any]]:
    tenant_id = get_current_tenant_id()
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM transport_orders WHERE job_no=%s AND tenant_id=%s ORDER BY id DESC", 
                        (job_no, tenant_id))
            rows = cur.fetchall()
            return [dict(r) for r in rows]
