from database.connection import get_connection

def log(user_id, tenant_id, entity, entity_id, action):

    with get_connection() as conn:
        conn.execute("""
            INSERT INTO audit_logs
            (user_id, tenant_id, entity, entity_id, action)
            VALUES (%s,%s,%s,%s,%s)
        """, (user_id, tenant_id, entity, entity_id, action))

        conn.commit()