from pathlib import Path
import views.rate_master_view as rm_view


def test_rate_master_view_has_render():
    assert hasattr(rm_view, "render")
    assert callable(rm_view.render)


def test_rate_master_view_no_session_state_form_key_collision():
    source = Path("views/rate_master_view.py").read_text(encoding="utf-8")
    # Form key and session state flag must never collide
    assert 'with st.form(f"rate_card_form_' in source
    assert 'st.session_state["rate_master_create_mode"]' in source
    assert 'with st.form(f"rate_master_' not in source


def test_upsert_rate_card_crud():
    import uuid
    from database.connection import init_database
    from database.postgres_compat import ensure_phase30_master_data_schema, ensure_phase30_charge_master_schema
    from database.connection import get_connection
    from managers.rate_master_manager import upsert_rate_card, list_rate_cards
    from managers.charge_master_crud_manager import upsert_charge
    from managers.customer_master_manager import save_customer

    init_database()
    with get_connection() as conn:
        ensure_phase30_master_data_schema(conn)
        ensure_phase30_charge_master_schema(conn)

    suffix = uuid.uuid4().hex[:4].upper()
    rate_code = f"RC-{suffix}"
    charge_code = f"C-{suffix}"
    cust_code = f"C{suffix}"[:5]

    # Test Charge Master CRUD
    charge_id = upsert_charge({
        "charge_code": charge_code,
        "description": "Test Ocean Freight",
        "category": "FREIGHT",
        "default_basis": "CONTAINER",
        "default_unit": "40HC",
        "default_currency": "USD",
        "is_active": True,
    })
    assert charge_id > 0

    # Test Rate Card insertion (triggers fetchone returning id)
    rate_card_id = upsert_rate_card(
        {
            "rate_no": rate_code,
            "mode": "SEA",
            "currency": "USD",
            "status": "ACTIVE",
            "valid_from": "2026-01-01",
            "valid_to": "2026-12-31",
            "service_type": "FCL",
            "equipment_type": "40HC",
        },
        [
            {
                "charge_id": charge_id,
                "basis": "CONTAINER",
                "minimum": 0,
                "rate": 1500.00,
                "currency": "USD",
            }
        ],
        user={"username": "admin", "tenant_id": "default"},
    )
    assert rate_card_id > 0

    # Test listing rate cards
    cards = list_rate_cards(active_only=False, user={"tenant_id": "default"})
    matching = [c for c in cards if c["id"] == rate_card_id]
    assert len(matching) == 1
    assert matching[0]["rate_no"] == rate_code
    assert len(matching[0]["lines"]) == 1
    assert float(matching[0]["lines"][0]["rate"]) == 1500.00

    # Test updating rate card
    updated_id = upsert_rate_card(
        {
            "id": rate_card_id,
            "rate_no": rate_code,
            "mode": "SEA",
            "currency": "USD",
            "status": "ACTIVE",
            "valid_from": "2026-01-01",
            "valid_to": "2026-12-31",
        },
        [
            {
                "charge_id": charge_id,
                "basis": "CONTAINER",
                "minimum": 100,
                "rate": 1600.00,
                "currency": "USD",
            }
        ],
        user={"username": "admin", "tenant_id": "default"},
    )
    assert updated_id == rate_card_id

    # Test customer master insert
    cust_id = save_customer({
        "customer_code": cust_code,
        "company_name": f"Test Customer Co. {suffix}",
        "display_name": "Test Cust",
        "credit_limit": 50000,
        "credit_currency": "THB",
        "is_active": True,
    })
    assert cust_id > 0


