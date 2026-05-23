import streamlit as st
import psycopg2.pool
import psycopg2.extras
import logging

# เพิ่ม Logging เพื่อให้ Debug ได้ง่ายขึ้น
logging.basicConfig(level=logging.INFO)

@st.cache_resource
def get_db_pool():
    try:
        db_secrets = st.secrets["connections"]["postgresql"]
        return psycopg2.pool.SimpleConnectionPool(
            1, 20, # เพิ่ม maxconn ตามความเหมาะสม
            **db_secrets
        )
    except Exception as e:
        st.error(f"❌ Connection Pool Error: {e}")
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
        # หากต้องการรักษาความเข้ากันได้ของ '?' ให้ใช้ regex จะแม่นยำกว่า .replace
        # แต่แนะนำให้เปลี่ยนเป็น %s ตั้งแต่ต้นจะดีที่สุดครับ
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

def init_database(schema_list):
    """
    แยก schema ออกเป็น List เพื่อให้รันทีละคำสั่งและจัดการ Error ได้ละเอียดขึ้น
    """
    conn = get_connection()
    try:
        with conn._conn.cursor() as cur:
            for sql in schema_list:
                cur.execute(sql)
        conn.commit()
    except Exception as e:
        conn.rollback()
        logging.error(f"Schema Init Failed: {e}")
    finally:
        conn.close()