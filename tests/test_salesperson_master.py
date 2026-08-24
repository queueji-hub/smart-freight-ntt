from managers.salesperson_manager import list_salespersons, save_salesperson, get_salesperson, delete_salesperson


def test_salesperson_crud():
    user = {"username": "admin", "role": "admin", "tenant_id": "default"}
    
    # Create salesperson
    sid = save_salesperson({
        "sales_code": "SPTEST01",
        "name": "Jane Sales Rep",
        "email": "jane@smartfreight.com",
        "phone": "+66 81 234 5678",
        "commission_rate": 2.5,
        "remarks": "Overseas Account Specialist",
        "is_active": True
    }, user)
    assert sid is not None

    # Fetch
    rec = get_salesperson(sid, user)
    assert rec is not None
    assert rec["sales_code"] == "SPTEST01"
    assert rec["name"] == "Jane Sales Rep"

    # List
    all_sp = list_salespersons(active_only=False, user=user)
    assert any(s["sales_code"] == "SPTEST01" for s in all_sp)

    # Update
    save_salesperson({
        "id": sid,
        "sales_code": "SPTEST01",
        "name": "Jane Doe",
        "email": "janedoe@smartfreight.com",
        "phone": "+66 81 234 5678",
        "commission_rate": 3.0,
        "remarks": "Senior Specialist",
        "is_active": True
    }, user)
    rec2 = get_salesperson(sid, user)
    assert rec2["name"] == "Jane Doe"
    assert float(rec2["commission_rate"]) == 3.0

    # Delete
    assert delete_salesperson(sid, user) is True
