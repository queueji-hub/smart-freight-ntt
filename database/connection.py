import streamlit as st
import psycopg2.pool
import psycopg2.extras
import logging

@st.cache_resource
def get_db_pool():
    try:
        # เช็คทุกขั้นตอนและ Print ออก Log โดยตรง
        if "connections" not in st.secrets:
            print("❌ DEBUG: ไม่พบหัวข้อ 'connections' ใน Secrets")
            return None
        if "postgresql" not in st.secrets["connections"]:
            print("❌ DEBUG: ไม่พบหัวข้อ 'postgresql' ภายใต้ 'connections'")
            return None
            
        db_secrets = st.secrets["connections"]["postgresql"]
        print(f"DEBUG: กำลังเชื่อมต่อด้วย user={db_secrets.get('user')}, host={db_secrets.get('host')}")
        
        return psycopg2.pool.SimpleConnectionPool(1, 20, **db_secrets)
    except Exception as e:
        print(f"❌ DEBUG: เกิดข้อผิดพลาดร้ายแรง: {e}")
        return None

class PostgresConnectionWrapper:
    def __init__(self, pool):
        self.pool = pool
        self._conn = self.pool.getconn()

    def cursor(self):
        # ใช้ RealDictCursor เพื่อคืนค่าเป็น Dictionary
        return self._conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    def execute(self, query, params=None):
    cur = self.conn.cursor()

    if params is None or params == ():
        cur.execute(query)
    else:
        cur.execute(query, params)

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