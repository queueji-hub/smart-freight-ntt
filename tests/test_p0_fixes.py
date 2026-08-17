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
    """Verify db_persistence functions handle missing config gracefully and export required APIs."""
    from managers.db_persistence import get_backup_status, force_push, push_db_to_github

    success, msg = push_db_to_github(force=False)
    assert isinstance(success, bool)
    assert isinstance(msg, str)

    status = get_backup_status()
    assert isinstance(status, dict)
    assert "configured" in status
    assert "last_push_str" in status
    assert "db_size_bytes" in status
    assert "is_dirty" in status

    force_ok, force_msg = force_push()
    assert isinstance(force_ok, bool)
    assert isinstance(force_msg, str)

