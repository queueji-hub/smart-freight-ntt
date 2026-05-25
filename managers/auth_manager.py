import bcrypt
from typing import Optional, Dict, Any, List
from database.connection import get_connection

# =========================================================
# CONFIGURATION
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
    "cs": {
        "dashboard": "r",
        "crm": "rw",
        "quotation": "rw",
        "booking": "rw",
        "shipment": "rw",
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
        "reports": "r",
    },
}

ROLE_LABELS = {
    "admin": "Administrator",
    "sales": "Sales Executive",
    "cs": "Customer Service",
    "operation": "Operations",
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
# PASSWORD FUNCTIONS
# =========================================================

def hash_password(password: str) -> str:
    return bcrypt.hashpw(
        password.encode("utf-8"),
        bcrypt.gensalt()
    ).decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    try:
        if not hashed:
            return False

        return bcrypt.checkpw(
            password.encode("utf-8"),
            hashed.encode("utf-8")
        )

    except Exception as e:
        print(f"❌ verify_password error: {e}")
        return False


# =========================================================
# AUTHENTICATION
# =========================================================

def authenticate(username: str, password: str) -> Optional[Dict[str, Any]]:
    """
    Login authentication
    """

    username = username.strip().lower()

    with get_connection() as conn:
        with conn.cursor() as cur:

            cur.execute(
                """
                SELECT
                    id,
                    username,
                    password_hash,
                    full_name,
                    email,
                    role,
                    is_active
                FROM users
                WHERE username = %s
                LIMIT 1
                """,
                (username,)
            )

            user = cur.fetchone()

            if not user:
                print("❌ User not found")
                return None

            user = dict(user)

            if int(user.get("is_active", 1)) != 1:
                print("❌ User inactive")
                return None

            password_ok = verify_password(
                password,
                user["password_hash"]
            )

            if not password_ok:
                print("❌ Invalid password")
                return None

            # remove password hash before return
            del user["password_hash"]

            return user


# =========================================================
# USER MANAGEMENT
# =========================================================

def list_users() -> List[Dict[str, Any]]:
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


def get_user_by_id(user_id: int) -> Optional[Dict[str, Any]]:
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
                    is_active
                FROM users
                WHERE id = %s
                """,
                (user_id,)
            )

            row = cur.fetchone()

            return dict(row) if row else None


def create_user(
    username: str,
    password: str,
    full_name: str = "",
    email: str = "",
    role: str = "sales",
):
    username = username.strip().lower()

    pwd_hash = hash_password(password)

    with get_connection() as conn:
        with conn.cursor() as cur:

            # check duplicate
            cur.execute(
                """
                SELECT id
                FROM users
                WHERE username = %s
                """,
                (username,)
            )

            existing = cur.fetchone()

            if existing:
                raise Exception("Username already exists")

            cur.execute(
                """
                INSERT INTO users (
                    username,
                    password_hash,
                    role,
                    full_name,
                    email,
                    is_active
                )
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (
                    username,
                    pwd_hash,
                    role,
                    full_name,
                    email,
                    1,
                )
            )

            conn.commit()


def update_user_password(username: str, new_password: str):
    username = username.strip().lower()

    pwd_hash = hash_password(new_password)

    with get_connection() as conn:
        with conn.cursor() as cur:

            cur.execute(
                """
                UPDATE users
                SET password_hash = %s
                WHERE username = %s
                """,
                (
                    pwd_hash,
                    username,
                )
            )

            conn.commit()


def update_user_role(username: str, role: str):
    username = username.strip().lower()

    with get_connection() as conn:
        with conn.cursor() as cur:

            cur.execute(
                """
                UPDATE users
                SET role = %s
                WHERE username = %s
                """,
                (
                    role,
                    username,
                )
            )

            conn.commit()


def set_user_active(username: str, active: bool):
    username = username.strip().lower()

    with get_connection() as conn:
        with conn.cursor() as cur:

            cur.execute(
                """
                UPDATE users
                SET is_active = %s
                WHERE username = %s
                """,
                (
                    1 if active else 0,
                    username,
                )
            )

            conn.commit()


def delete_user(username: str):
    username = username.strip().lower()

    with get_connection() as conn:
        with conn.cursor() as cur:

            cur.execute(
                """
                DELETE FROM users
                WHERE username = %s
                """,
                (username,)
            )

            conn.commit()