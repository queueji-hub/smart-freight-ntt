import psycopg2
from psycopg2.extras import RealDictCursor

DB_CONFIG = {
    "host": "localhost",
    "database": "smart_freight",
    "user": "postgres",
    "password": "postgres",
    "port": 5432,
}

def get_connection():
    conn = psycopg2.connect(**DB_CONFIG)
    conn.autocommit = False
    return conn


def execute(query, params=None):
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query, params)
            if query.strip().lower().startswith("select"):
                return cur.fetchall()
            conn.commit()
            return None