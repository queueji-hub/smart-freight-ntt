from typing import List, Dict, Any
from database.connection import get_connection


# =========================
# ADD CONTAINER
# =========================

def add_container(data: Dict[str, Any]):
    with get_connection() as conn:
        conn.execute("""
            INSERT INTO containers (
                bl_no, job_no,
                container_no,
                container_size,
                container_type,
                seal_no,
                gross_weight,
                volume,
                status
            )
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, (
            data["bl_no"],
            data["job_no"],
            data.get("container_no"),
            data.get("container_size"),
            data.get("container_type"),
            data.get("seal_no"),
            data.get("gross_weight", 0),
            data.get("volume", 0),
            "Loaded"
        ))

        conn.commit()


# =========================
# LIST CONTAINERS
# =========================

def list_containers(bl_no: str = None, job_no: str = None):
    sql = "SELECT * FROM containers WHERE 1=1"
    params = []

    if bl_no:
        sql += " AND bl_no=%s"
        params.append(bl_no)

    if job_no:
        sql += " AND job_no=%s"
        params.append(job_no)

    with get_connection() as conn:
        rows = conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]