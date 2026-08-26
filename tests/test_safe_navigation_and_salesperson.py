"""
Tests for Safe Navigation Redirection & Job Salesperson Completeness.
Verifies that:
1. Navigation helper manages session state redirects safely without StreamlitAPIException.
2. Salesperson retrieval (list_salespersons, list_sales_users) works seamlessly across database dialects.
3. Salesperson matching helper (_idx_sales) matches exact, partial, and formatted names reliably.
4. Job creation & ops editing persist salespersons accurately without data truncation.
"""

import pytest
import streamlit as st
from views.navigation_helper import get_active_tab, redirect_to_tab
from managers.salesperson_manager import list_salespersons, save_salesperson
from managers.master_data_manager import list_sales_users
from views.shipment_view import _idx_sales
from managers.shipment_manager import create_shipment, get_shipment, update_shipment


def test_safe_navigation_redirection_lifecycle():
    """Test get_active_tab and redirect_to_tab without widget exception."""
    nav_key = "test_fin_active_tab"
    tab_opts = ["📑 Browse / Register", "➕ Create New", "🛡️ Audit"]

    # Initial load: should default to first option
    st.session_state.pop(nav_key, None)
    st.session_state.pop(f"_nav_redirect_{nav_key}", None)
    
    current = get_active_tab(nav_key, tab_opts)
    assert current == "📑 Browse / Register"
    assert st.session_state[nav_key] == "📑 Browse / Register"

    # User navigates to tab 1
    st.session_state[nav_key] = "➕ Create New"

    # In child form, user submits -> queues redirect to Browse
    redirect_to_tab(nav_key, "📑 Browse / Register")
    assert st.session_state[f"_nav_redirect_{nav_key}"] == "📑 Browse / Register"

    # On next rerun, before widget instantiation, get_active_tab consumes redirect:
    current_after_rerun = get_active_tab(nav_key, tab_opts)
    assert current_after_rerun == "📑 Browse / Register"
    assert st.session_state[nav_key] == "📑 Browse / Register"
    assert f"_nav_redirect_{nav_key}" not in st.session_state


def test_salesperson_list_and_user_sync():
    """Test that list_salespersons and list_sales_users return valid non-empty lists."""
    sales_list = list_salespersons(active_only=False)
    assert isinstance(sales_list, list)
    assert len(sales_list) > 0, "Expected at least default or synced salespersons"

    sales_users = list_sales_users()
    assert isinstance(sales_users, list)
    assert len(sales_users) > 0, "Expected sales users list to contain entries"
    for su in sales_users:
        assert "id" in su
        assert "full_name" in su or "username" in su


def test_salesperson_idx_matching():
    """Test _idx_sales matching exact, code-prefixed, and partial names."""
    opts = [
        "SP001 — Spicy (Managing Director / Sales)",
        "SP002 — John Doe",
        "SP003 — Jane Smith",
        "Unassigned"
    ]

    # Exact match
    assert _idx_sales(opts, "SP002 — John Doe") == 1

    # Match just the name
    assert _idx_sales(opts, "Spicy") == 0
    assert _idx_sales(opts, "John Doe") == 1
    assert _idx_sales(opts, "Jane Smith") == 2

    # Match just the code
    assert _idx_sales(opts, "SP001") == 0
    assert _idx_sales(opts, "SP003") == 2

    # Match lowercase / stripped
    assert _idx_sales(opts, "jane smith") == 2
    assert _idx_sales(opts, "sp002") == 1

    # Unknown defaults to 0 without error
    assert _idx_sales(opts, "Unknown Person") == 0


def test_shipment_salesperson_persistence():
    """Test creating and updating a job with salesperson info."""
    user = {"id": 1, "username": "admin", "tenant_id": "default"}
    import time
    uid = int(time.time() * 1000) % 1000000

    job_no = create_shipment({
        "customer_id": 1,
        "customer_name": f"Sales Test Cust {uid}",
        "sales_id": 1,
        "sales_person": "SP001 — Spicy",
        "job_type": "SE",
        "mode": "SEA",
        "status": "Proceed"
    }, user)

    job = get_shipment(job_no)
    assert job is not None
    assert job.get("sales_person") == "SP001 — Spicy"

    # Update salesperson
    success = update_shipment(job_no, {
        "sales_person": "SP002 — Jane Doe",
    })
    assert success is True

    updated_job = get_shipment(job_no)
    assert updated_job is not None
    assert updated_job.get("sales_person") == "SP002 — Jane Doe"
