import bcrypt
from typing import Optional, Dict, Any, List
from database.connection import get_connection


# =========================================================
# ROLE PERMISSIONS
# =========================================================

PERMISSIONS = {
    "admin": {
        "dashboard": "rw",
        "crm": "rw",
        "quotation": "rw",
        "booking": "rw",
        "shipment": "rw",
        "billing": "rw",
        "reports": "rw",
        "users": "rw",
    },
    "sales": {
        "dashboard": "r",
        "crm": "rw",
        "quotation": "rw",
        "booking": "r",
        "shipment": "r",
        "billing": "r",
        "reports": "r",
    },
    "operation": {
        "dashboard": "r",
        "crm": "rw",
        "quotation": "rw",
        "booking": "rw",
        "shipment": "rw",
        "billing": "r",
        "reports": "r",
    },
    "accounting": {
        "dashboard": "r",
        "crm": "r",
        "quotation": "r",
        "booking": "r",
        "shipment": "r",
        "billing": "rw",
        "reports": "rw",
    },
}


ROLE_LABELS = {
    "admin": "Administrator",
    "sales": "Sales",
    "operation": "Operation",
    "accounting": "Accounting",
}


# =========================================================
# PERMISSION HELPERS
# =========================================================

def can(role: str, module: str, action: str = "r") -> bool:

    perms = PERMISSIONS.get(role, {})
    granted = perms.get(module, "")

    if action == "r":
        return "r" in granted or "w" in granted

    if action == "w":
        return "w" in granted

    return False


def can_read(role: str, module: str) -> bool:
    return can(role, module, "r")


def can_write(role: str, module: str) -> bool:
    return can(role, module, "w")


# =========================================================
# PASSWORD HELPERS
# =========================================================

def hash_password(password: str) -> str:

    password = password.strip()

    return bcrypt.hashpw(
        password.encode("utf-8"),
        bcrypt.gensalt()
    ).decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:

    try:

        if not password or not hashed:
            return False

        password = password.strip()

        return bcrypt.checkpw(
            password.encode("utf-8"),
            hashed.encode("utf-8")
        )

    except Exception as e:

        print("VERIFY PASSWORD ERROR:", e)
        return False


# =========================================================
# AUTHENTICATION
# =========================================================

def authenticate(
    username: str,
    password: str
) -> Optional[Dict[str, Any]]:

    try:

        username = username.strip().lower()
        password = password.strip()

        with get_connection() as conn:
            with conn.cursor() as cur:

                cur.execute(
                    """
                    SELECT *
                    FROM users
                    WHERE LOWER(username) = %s
                    LIMIT 1
                    """,
                    (username,)
                )

                row = cur.fetchone()

                # =====================================
                # USER NOT FOUND
                # =====================================
                if not row:

                    print(f"❌ USER NOT FOUND: {username}")
                    return None

                user = dict(row)

                print(f"✅ USER FOUND: {user.get('username')}")

                # =====================================
                # PASSWORD HASH CHECK
                # =====================================
                stored_hash = user.get("password_hash")

                if not stored_hash:

                    print("❌ PASSWORD HASH EMPTY")
                    return None

                # =====================================
                # VERIFY PASSWORD
                # =====================================
                password_ok = verify_password(
                    password,
                    stored_hash
                )

                print("PASSWORD OK:", password_ok)

                if not password_ok:

                    print("❌ INVALID PASSWORD")
                    return None

                # =====================================
                # OPTIONAL ACTIVE CHECK
                # =====================================
                if "is_active" in user:

                    try:

                        if int(user.get("is_active", 1)) != 1:

                            print("❌ USER DISABLED")
                            return None

                    except Exception:
                        pass

                # =====================================
                # REMOVE HASH
                # =====================================
                user.pop("password_hash", None)

                return user

    except Exception as e:

        print("AUTHENTICATE ERROR:", e)
        return None

    return None


# =========================================================
# USER MANAGEMENT
# =========================================================

def list_users() -> List[Dict[str, Any]]:

    try:

        with get_connection() as conn:
            with conn.cursor() as cur:

                cur.execute(
                    """
                    SELECT
                        id,
                        username,
                        full_name,
                        email,
                        role,
                        is_active,
                        created_at
                    FROM users
                    ORDER BY username ASC
                    """
                )

                rows = cur.fetchall()

                return [dict(r) for r in rows]

    except Exception as e:

        print("LIST USERS ERROR:", e)
        return []


def get_user_by_username(
    username: str
) -> Optional[Dict[str, Any]]:

    try:

        username = username.strip().lower()

        with get_connection() as conn:
            with conn.cursor() as cur:

                cur.execute(
                    """
                    SELECT *
                    FROM users
                    WHERE LOWER(username) = %s
                    LIMIT 1
                    """,
                    (username,)
                )

                row = cur.fetchone()

                if not row:
                    return None

                return dict(row)

    except Exception as e:

        print("GET USER ERROR:", e)
        return None


def create_user(
    username: str,
    password: str,
    full_name: str = "",
    email: str = "",
    role: str = "sales"
):

    username = username.strip().lower()

    existing = get_user_by_username(username)

    if existing:
        raise Exception("Username already exists")

    password_hash = hash_password(password)

    try:

        with get_connection() as conn:
            with conn.cursor() as cur:

                cur.execute(
                    """
                    INSERT INTO users (
                        username,
                        password_hash,
                        full_name,
                        email,
                        role,
                        is_active
                    )
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    (
                        username,
                        password_hash,
                        full_name,
                        email,
                        role,
                        1
                    )
                )

                conn.commit()

        print(f"✅ USER CREATED: {username}")

    except Exception as e:

        print("CREATE USER ERROR:", e)
        raise e


def update_user_password(
    username: str,
    new_password: str
):

    password_hash = hash_password(new_password)

    try:

        with get_connection() as conn:
            with conn.cursor() as cur:

                cur.execute(
                    """
                    UPDATE users
                    SET password_hash = %s
                    WHERE LOWER(username) = %s
                    """,
                    (
                        password_hash,
                        username.strip().lower()
                    )
                )

                conn.commit()

                if cur.rowcount == 0:
                    raise Exception("User not found")

        print(f"✅ PASSWORD UPDATED: {username}")

    except Exception as e:

        print("UPDATE PASSWORD ERROR:", e)
        raise e


def update_user_role(
    username: str,
    role: str
):

    try:

        with get_connection() as conn:
            with conn.cursor() as cur:

                cur.execute(
                    """
                    UPDATE users
                    SET role = %s
                    WHERE LOWER(username) = %s
                    """,
                    (
                        role,
                        username.strip().lower()
                    )
                )

                conn.commit()

        print(f"✅ ROLE UPDATED: {username}")

    except Exception as e:

        print("UPDATE ROLE ERROR:", e)
        raise e


def set_user_active(
    username: str,
    active: bool
):

    try:

        with get_connection() as conn:
            with conn.cursor() as cur:

                cur.execute(
                    """
                    UPDATE users
                    SET is_active = %s
                    WHERE LOWER(username) = %s
                    """,
                    (
                        1 if active else 0,
                        username.strip().lower()
                    )
                )

                conn.commit()

        print(f"✅ ACTIVE STATUS UPDATED: {username}")

    except Exception as e:

        print("SET ACTIVE ERROR:", e)
        raise e