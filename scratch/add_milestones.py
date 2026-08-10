import os
with open("managers/shipment_manager.py", "a", encoding="utf-8") as f:
    f.write('''

# =========================
# MILESTONES
# =========================

def add_milestone(job_no: str, milestone_code: str, milestone_name: str, planned_date: str = None) -> bool:
    tenant_id = get_current_tenant_id()
    target = get_shipment(job_no)
    if not target:
        return False
        
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO shipment_milestones (tenant_id, shipment_id, milestone_code, milestone_name, planned_date)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (tenant_id, target['id'], milestone_code, milestone_name, planned_date)
            )
            conn.commit()
            return cur.rowcount > 0

def update_milestone(milestone_id: int, actual_date: str, status: str = 'COMPLETED', remarks: str = None) -> bool:
    tenant_id = get_current_tenant_id()
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE shipment_milestones
                SET actual_date = %s, status = %s, remarks = %s, updated_at = CURRENT_TIMESTAMP
                WHERE id = %s AND tenant_id = %s
                """,
                (actual_date, status, remarks, milestone_id, tenant_id)
            )
            conn.commit()
            return cur.rowcount > 0

def get_milestones(job_no: str) -> List[Dict]:
    tenant_id = get_current_tenant_id()
    target = get_shipment(job_no)
    if not target:
        return []
        
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT * FROM shipment_milestones 
                WHERE shipment_id = %s AND tenant_id = %s
                ORDER BY id ASC
                """,
                (target['id'], tenant_id)
            )
            rows = cur.fetchall()
            if not rows:
                return []
            cols = [desc[0] for desc in cur.description]
            return [dict(zip(cols, row)) for row in rows]
''')
