from database.connection import get_connection

def add_container(job_id, container_no, size, seal_no):

    with get_connection() as conn:
        conn.execute("""
            INSERT INTO containers (
                job_id, container_no, size, seal_no
            )
            VALUES (%s,%s,%s,%s)
        """, (job_id, container_no, size, seal_no))

        conn.commit()