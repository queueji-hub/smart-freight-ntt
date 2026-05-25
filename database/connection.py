import streamlit as st
import psycopg2
import psycopg2.extras

def get_connection():
    return psycopg2.connect(
        host=st.secrets["connections"]["postgresql"]["host"],
        port=st.secrets["connections"]["postgresql"]["port"],
        database=st.secrets["connections"]["postgresql"]["database"],
        user=st.secrets["connections"]["postgresql"]["user"],
        password=st.secrets["connections"]["postgresql"]["password"],
        cursor_factory=psycopg2.extras.RealDictCursor
    )

# =========================
# INIT DATABASE
# =========================
def init_database():
    conn = get_connection()

    try:
        with conn.cursor() as cur:

            cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT DEFAULT 'user',
                full_name TEXT,
                email TEXT,
                is_active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)

            conn.commit()

    finally:
        conn.close()