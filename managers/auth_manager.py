def authenticate(username: str, password: str):
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
                print("USER NOT FOUND")
                return None

            user = dict(user)

            print("DB HASH:", user["password_hash"])

            password_ok = verify_password(
                password,
                user["password_hash"]
            )

            print("VERIFY RESULT:", password_ok)

            if not password_ok:
                return None

            del user["password_hash"]

            return user