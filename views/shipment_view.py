import logging
from typing import List, Dict, Any, Optional
import psycopg2
from psycopg2.extras import RealDictCursor

# โมดูลภายในระบบของคุณ (ยังคงไว้ตามเดิม)
from database.connection import get_connection
from managers.job_number import generate_job_number

# =========================
# CONFIGURATION
# =========================

logger = logging.getLogger(__name__)

SHIPMENT_FIELDS = [
    "status", "job_type", "booking_no", "customer_name",
    "shipper", "consignee", "cargo_type", "carrier",
    "pol", "pod", "etd", "eta",
    "bl_no", "invoice_no",
    "customer_paid",
    "remark",
    "created_by", "updated_by"
]

STATUS_FLOW = ["Proceed", "In Transit", "Arrived", "Finished", "Closed", "Canceled"]


# =========================
# DATABASE INITIALIZATION
# =========================

def init_shipments_table() -> None:
    """
    สร้างตาราง `shipments` และ Index ที่เกี่ยวข้องบน PostgreSQL 
    หากยังไม่มีตารางนี้อยู่ในระบบ
    """
    create_table_sql = """
        CREATE TABLE IF NOT EXISTS shipments (
            id SERIAL PRIMARY KEY,
            job_no TEXT UNIQUE NOT NULL,
            status TEXT DEFAULT 'Proceed',
            job_type TEXT,
            booking_no TEXT,
            customer_name TEXT,
            shipper TEXT,
            consignee TEXT,
            cargo_type TEXT,
            carrier TEXT,
            pol TEXT,
            pod TEXT,
            etd DATE,
            eta DATE,
            bl_no TEXT,
            invoice_no TEXT,
            customer_paid INTEGER DEFAULT 0,
            remark TEXT,
            created_by TEXT,
            updated_by TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """
    create_index_sql = """
        CREATE INDEX IF NOT EXISTS idx_shipments_job_no ON shipments(job_no);
    """
    
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(create_table_sql)
                cur.execute(create_index_sql)
            conn.commit()
            logger.info("Shipments table and indexes initialized successfully.")
    except psycopg2.Error as e:
        logger.error(f"Failed to initialize shipments table: {e}")
        raise


# =========================
# CREATE SHIPMENT
# =========================

def create_shipment(data: Dict[str, Any], company_prefix: Optional[str] = None) -> str:
    """
    สร้างรายการ Shipment ใหม่ในฐานข้อมูล
    
    Args:
        data (Dict[str, Any]): ข้อมูล Shipment ที่ต้องการบันทึก
        company_prefix (Optional[str]): ตัวอักษรย่อบริษัทสำหรับสร้าง Job Number
        
    Returns:
        str: หมายเลข Job Number ที่สร้างขึ้นใหม่
    """
    job_no = generate_job_number(
        data.get("job_type", "SE"),
        data.get("etd"),
        company_prefix
    )

    # กรองเฉพาะฟิลด์ที่อนุญาต
    filtered_data = {k: v for k, v in data.items() if k in SHIPMENT_FIELDS}

    cols = ["job_no"] + list(filtered_data.keys())
    values = [job_no] + list(filtered_data.values())

    columns = ", ".join(cols)
    placeholders = ", ".join(["%s"] * len(cols))

    sql = f"""