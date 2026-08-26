import pytest
import time
from database.connection import init_database
from database.local_schema_compat import ensure_phase30_local_schema
from managers.auth_manager import (
    authenticate,
    can,
    can_read,
    can_write,
    normalize_user,
    hash_password,
    verify_password,
    create_user,
    get_user_by_username,
    update_user_role,
    set_user_active,
    update_user_password,
    PERMISSIONS,
)


@pytest.fixture(scope="module", autouse=True)
def setup_db():
    init_database()
    ensure_phase30_local_schema()



def test_rbac_permission_matrix():
    # Admin has read/write on core modules
    assert can("admin", "dashboard", "r") is True
    assert can("admin", "dashboard", "w") is True
    assert can("admin", "users", "w") is True

    # Sales has read-only on dashboard and booking, rw on quotation
    assert can("sales", "dashboard", "r") is True
    assert can("sales", "dashboard", "w") is False
    assert can("sales", "quotation", "w") is True
    assert can_write("sales", "quotation") is True

    # Accounting has rw on billing
    assert can("accounting", "billing", "w") is True
    assert can("accounting", "users", "r") is False


def test_user_normalization():
    raw_user = {
        "id": 42,
        "username": "  TEST_USER  ",
        "full_name": None,
        "email": "test@example.com",
        "role": "ADMIN",
        "is_active": 1,
    }
    norm = normalize_user(raw_user)
    assert norm["username"] == "test_user"
    assert norm["role"] == "admin"
    assert norm["full_name"] == "test_user"
    assert norm["is_active"] == 1


def test_password_hashing_and_verification():
    pw = "SuperSecret@2026!"
    hashed = hash_password(pw)
    assert hashed != pw
    assert verify_password(pw, hashed) is True
    assert verify_password("WrongPassword", hashed) is False


def test_user_lifecycle_crud():
    uid = int(time.time() * 1000) % 1000000
    uname = f"autotest_user_{uid}"
    
    # 1. Create user
    create_user(
        username=uname,
        password="TempPassword@123",
        full_name="Automated Test User",
        email=f"{uname}@freightflow.com",
        role="sales"
    )
    
    user = get_user_by_username(uname)
    assert user is not None
    assert user["username"] == uname
    assert user["role"] == "sales"
    assert user["is_active"] == 1

    # 2. Update role
    update_user_role(uname, "operation")
    updated_user = get_user_by_username(uname)
    assert updated_user["role"] == "operation"

    # 3. Update password
    new_pw = "NewSecurePass@2026!"
    update_user_password(uname, new_pw)
    auth_user = authenticate(uname, new_pw)
    assert auth_user is not None
    assert auth_user["username"] == uname

    # 4. Deactivate and reactivate
    set_user_active(uname, False)
    deactivated = get_user_by_username(uname)
    assert deactivated["is_active"] == 0

    set_user_active(uname, True)
    reactivated = get_user_by_username(uname)
    assert reactivated["is_active"] == 1
