import streamlit as st
import psycopg2.pool
import psycopg2.extras
import logging

# ลบ @st.cache_resource ออก เพื่อบังคับให้ระบบอ่านค่าใหม่เสมอ
def get_db_pool():
    try:
        # ตรวจสอบว่า secrets มีอยู่จริง
        if "connections" not in st.secrets or "postgresql" not in st.secrets["connections"]:
            logging.error("❌ Secrets 'connections.postgresql' missing!")
            return None
            
        db_secrets = st.secrets["connections"]["postgresql"]
        # สร้าง pool
        return psycopg2.pool.SimpleConnectionPool(1, 20, **db_secrets)
    except Exception as e:
        logging.error(f"❌ Connection Pool Error: {e}")
        return None

class PostgresConnectionWrapper:
    def __init__(self, pool):
        self.pool = pool
        self._conn = self.pool.getconn()

    def cursor(self):
        # ใช้ RealDictCursor เพื่อคืนค่าเป็น Dictionary
        return self._conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    def execute(self, query, params=None):
        cur = self.cursor()
        # เปลี่ยน '?' เป็น '%s' เพื่อให้ตรงกับมาตรฐาน PostgreSQL
        processed_query = query.replace('?', '%s') 
        cur.execute(processed_query, params or ())
        return cur

    def commit(self): self._conn.commit()
    def rollback(self): self._conn.rollback()
    def close(self): self.pool.putconn(self._conn)

    def __enter__(self): return self
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type: self.rollback()
        else: self.commit()
        self.close()

def get_connection():
    pool = get_db_pool()
    if not pool: raise Exception("Database pool not initialized")
    return PostgresConnectionWrapper(pool)

# ปรับแก้ให้มีค่าเริ่มต้นเป็น list ว่าง เพื่อแก้ TypeError: missing 1 required positional argument
def init_database(schema_list=None):
    """
    แยก schema ออกเป็น List เพื่อให้รันทีละคำสั่งและจัดการ Error ได้ละเอียดขึ้น
    """
    if schema_list is None:
        schema_list = []
        
    pool = get_db_pool()
    if not pool: return

    conn = pool.getconn()
    try:
        with conn.cursor() as cur:
            for sql in schema_list:
                cur.execute(sql)
        conn.commit()
        logging.info("Database initialized successfully.")
    except Exception as e:
        conn.rollback()
        logging.error(f"Schema Init Failed: {e}")
    finally:
        pool.putconn(conn)