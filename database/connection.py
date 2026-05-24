import os
import psycopg2
from psycopg2.extras import RealDictCursor
import streamlit as st


# =========================
# SAFE ENV LOADER
# =========================
def _get(key, default=None):
    try:
        return st.secrets.get(key, os.getenv(key, default))
    except Exception:
        return os.getenv(key, default)


# =========================
# CONNECTION
# =========================
def get_connection():

    host = _get("DB_HOST")
    db = _get("DB_NAME", "postgres")
    user = _get("DB_USER")
    password = _get("DB_PASSWORD")
    port = _get("DB_PORT", 5432)

    # 🔥 กันพังก่อน connect
    if not host or not user or not password:
        raise Exception(
            "DB CONFIG MISSING ❌ "
            "Please set DB_HOST, DB_USER, DB_PASSWORD in Streamlit secrets"
        )

    return psycopg2.connect(
        host=host,
        database=db,
        user=user,
        password=password,
        port=port,
        cursor_factory=RealDictCursor
    )


# =========================
# SAFE EXECUTE
# =========================
def execute(query, params=None, fetch=False):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(query, params or ())

            if fetch:
                return cur.fetchall()

            conn.commit()
            return None
    finally:
        conn.close()


# =========================
# INIT DB (SAFE)
# =========================
def init_database():
    conn = get_connection()
    try:
        with conn.cursor() as cur:

            cur.execute("""
                CREATE TABLE IF NOT EXISTS shipments (
                    id SERIAL PRIMARY KEY,
                    job_no TEXT UNIQUE,
                    status TEXT DEFAULT 'Proceed',
                    job_type TEXT,
                    customer_name TEXT,
                    pol TEXT,
                    pod TEXT,
                    etd DATE,
                    eta DATE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS bookings (
                    id SERIAL PRIMARY KEY,
                    booking_no TEXT UNIQUE,
                    job_type TEXT,
                    customer_name TEXT,
                    pol TEXT,
                    pod TEXT,
                    etd DATE,
                    eta DATE,
                    status TEXT DEFAULT 'Draft',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS invoices (
                    id SERIAL PRIMARY KEY,
                    doc_no TEXT UNIQUE,
                    customer_name TEXT,
                    total_amount NUMERIC DEFAULT 0,
                    outstanding NUMERIC DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

        conn.commit()

    finally:
        conn.close()