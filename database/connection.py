import streamlit as st
import psycopg2
import psycopg2.extras

# =========================
# DB CONNECTION
# =========================
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
# SAFE QUERY EXECUTOR
# =========================
def execute_query(query, params=None, fetchone=False, fetchall=False, commit=False):
    conn = get_connection()

    try:
        with conn.cursor() as cur:
            cur.execute(query, params)

            result = None

            if fetchone:
                result = cur.fetchone()

            elif fetchall:
                result = cur.fetchall()

            if commit:
                conn.commit()

            return result

    finally:
        conn.close()

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