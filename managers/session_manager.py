import uuid
from typing import Optional, Dict, Any
from database.connection import get_connection


# =========================================================
# CREATE SESSION
# =========================================================

def create_session(user_id: int) -> str:

    token = str(uuid.uuid4())

    try:

        with get_connection() as conn:
            with conn.cursor() as cur:

                cur.execute(
                    """
                    INSERT INTO sessions (
                        user_id,
                        token
                    )
                    VALUES (%s, %s)
                    """,
                    (
                        user_id,
                        token
                    )
                )

                conn.commit()

        return token

    except Exception as e:

        print("CREATE SESSION ERROR:", e)
        raise e


# =========================================================
# GET USER BY TOKEN
# =========================================================

def get_user_by_token(
    token: str
) -> Optional[Dict[str, Any]]:

    try:

        with get_connection() as conn:
            with conn.cursor() as cur:

                cur.execute(
                    """
                    SELECT
                        u.id,
                        u.username,
                        u.full_name,
                        u.email,
                        u.role,
                        u.is_active
                    FROM sessions s
                    JOIN users u
                        ON s.user_id = u.id
                    WHERE s.token = %s
                    LIMIT 1
                    """,
                    (token,)
                )

                row = cur.fetchone()

                if not row:
                    return None

                return dict(row)

    except Exception as e:

        print("GET USER BY TOKEN ERROR:", e)
        return None


# =========================================================
# DELETE SESSION
# =========================================================

def delete_session(token: str):

    try:

        with get_connection() as conn:
            with conn.cursor() as cur:

                cur.execute(
                    """
                    DELETE FROM sessions
                    WHERE token = %s
                    """,
                    (token,)
                )

                conn.commit()

    except Exception as e:

        print("DELETE SESSION ERROR:", e)
        raise e