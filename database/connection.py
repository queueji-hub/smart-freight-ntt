import os
import psycopg2
from psycopg2.extras import RealDictCursor
import streamlit as st

def _get_env(key, default=None):
    return st.secrets.get(key, os.getenv(key, default))

def get_connection():
    return psycopg2.connect(
        host=_get_env("DB_HOST"),
        database=_get_env("DB_NAME", "postgres"),
        user=_get_env("DB_USER"),
        password=_get_env("DB_PASSWORD"),
        port=_get_env("DB_PORT", 5432),
        cursor_factory=RealDictCursor
    )

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