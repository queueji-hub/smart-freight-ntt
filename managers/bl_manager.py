from typing import List, Dict, Any
from database.connection import get_connection


# =========================
# CREATE BL
# =========================

def create_bl(data: Dict[str, Any]) -> str:
    with get_connection() as conn:
        cur = conn.execute("""
            INSERT INTO bills_of_lading (
                bl_no, job_no,
                shipper, consignee, notify_party,
                pol, pod,
                vessel, voyage,
                bl_type, status
            )
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            RETURNING bl_no
        """, (
            data["bl_no"],
            data["job_no"],
            data.get("shipper"),
            data.get("consignee"),
            data.get("notify_party"),
            data.get("pol"),
            data.get("pod"),
            data.get("vessel"),
            data.get("voyage"),
            data.get("bl_type", "Original"),
            "Draft"
        ))

        conn.commit()
        return cur.fetchone()["bl_no"]


# =========================
# LIST BL
# =========================

def list_bl(job_no: str = None):
    with get_connection() as conn:
        if job_no:
            rows = conn.execute(
                "SELECT * FROM bills_of_lading WHERE job_no=%s",
                (job_no,)
            ).fetchall()
        else:
            rows = conn.execute("SELECT * FROM bills_of_lading ORDER BY id DESC").fetchall()

        return [dict(r) for r in rows]


# =========================
# GET BL
# =========================

def get_bl(bl_no: str):
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM bills_of_lading WHERE bl_no=%s",
            (bl_no,)
        ).fetchone()

        return dict(row) if row else None