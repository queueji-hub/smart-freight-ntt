import sys
import os
import streamlit as st
from unittest.mock import patch, MagicMock

# Add workspace root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.connection import get_connection

def test_successful_connection():
    print("Running test_successful_connection...")
    with get_connection() as conn:
        assert conn is not None
        print("Successfully obtained connection.")

def test_exception_inside_context():
    print("Running test_exception_inside_context...")
    try:
        with get_connection() as conn:
            print("Raising exception inside with block...")
            raise ValueError("Test error inside context")
    except ValueError as e:
        assert str(e) == "Test error inside context"
        print("Exception propagated correctly.")
    else:
        assert False, "Exception was not propagated"

def test_postgres_unreachable_dev_fallback():
    print("Running test_postgres_unreachable_dev_fallback...")
    # Mock psycopg2.connect to fail
    with patch("psycopg2.connect", side_effect=Exception("Connection refused")):
        # st.secrets behaves like a dict or has get
        mock_secrets = MagicMock()
        mock_secrets.get.side_effect = lambda k, default=None: "development" if k == "APP_ENV" else default
        with patch("streamlit.secrets", mock_secrets):
            with get_connection() as conn:
                assert conn.__class__.__name__ == "SQLiteConnAdapter"
                print("Successfully fell back to SQLite in development.")

def test_postgres_unreachable_production_fails():
    print("Running test_postgres_unreachable_production_fails...")
    # Mock psycopg2.connect to fail
    with patch("psycopg2.connect", side_effect=Exception("Connection refused")):
        mock_secrets = MagicMock()
        mock_secrets.get.side_effect = lambda k, default=None: "production" if k == "APP_ENV" else default
        with patch("streamlit.secrets", mock_secrets):
            try:
                with get_connection() as conn:
                    pass
            except RuntimeError as e:
                assert "PostgreSQL connection failed in production mode" in str(e)
                print("Correctly raised RuntimeError in production connection failure.")
            else:
                assert False, "Production connection failure did not raise exception"

if __name__ == "__main__":
    test_successful_connection()
    test_exception_inside_context()
    test_postgres_unreachable_dev_fallback()
    test_postgres_unreachable_production_fails()
    print("All connection contract tests passed successfully!")
