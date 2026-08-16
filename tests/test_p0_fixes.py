"""Tests for Phase 30 P0 Launch Blocker fixes."""
from database.connection import get_connection, init_database
from config import COMPANY
import managers.db_persistence as db_p


def test_missing_tables_exist_after_init():
    """Verify transport_orders, regulatory_submissions, and commissions tables exist."""
    init_database()
    with get_connection() as conn:
        with conn.cursor() as cur:
            # Check transport_orders
            cur.execute("SELECT COUNT(*) FROM transport_orders")
            assert cur.fetchone() is not None

            # Check regulatory_submissions
            cur.execute("SELECT COUNT(*) FROM regulatory_submissions")
            assert cur.fetchone() is not None

            # Check commissions
            cur.execute("SELECT COUNT(*) FROM commissions")
            assert cur.fetchone() is not None


def test_company_branch_profile_configured():
    """Verify Thai tax compliance branch fields in COMPANY profile."""
    assert "branch_th" in COMPANY
    assert "branch_code" in COMPANY
    assert COMPANY["branch_code"] == "00000"
    assert "0735568004823" in COMPANY["tax_id"] or "073-556-800-4823" in COMPANY["tax_id"]


def test_db_persistence_safe_execution():
    """Verify db_persistence.push_db_to_github handles missing config gracefully."""
    success, msg = db_p.push_db_to_github(force=False)
    assert isinstance(success, bool)
    assert isinstance(msg, str)
