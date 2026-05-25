import streamlit as st
import pandas as pd

from managers.auth_manager import (
    list_users,
    create_user,
    update_user_password,
    PERMISSIONS,
)

from database.connection import get_connection


def render():

    user = st.session_state.get("user", {})

    # =====================================================
    # ACCESS CONTROL
    # =====================================================
    if user.get("role") != "admin":
        st.error("⚠️ Admin only access")
        st.stop()

    st.title("👤 User Management")

    tab_list, tab_new = st.tabs([
        "📋 Manage Users",
        "➕ Create New"
    ])

    # =====================================================
    # LOAD USERS SAFELY
    # =====================================================
    try:
        users = list_users()
    except Exception as e:
        st.error("Failed to load users")
        st.exception(e)
        return

    # =====================================================
    # USER LIST
    # =====================================================
    with tab_list:

        if not users:
            st.info("No users found.")
            return

        df = pd.DataFrame(users)

        # SAFE column handling
        safe_cols = [c for c in ["username", "full_name", "role"] if c in df.columns]

        st.dataframe(
            df[safe_cols],
            use_container_width=True
        )

        st.divider()

        usernames = [u.get("username") for u in users if u.get("username")]

        if not usernames:
            st.warning("No valid users")
            return

        search_user = st.selectbox(
            "Select user to manage:",
            usernames
        )

        target = next(
            (u for u in users if u.get("username") == search_user),
            None
        )

        if not target:
            st.error("User not found")
            return

        col1, col2 = st.columns(2)

        # =====================================================
        # RESET PASSWORD
        # =====================================================
        with col1:

            st.subheader("🔐 Reset Password")

            new_pwd = st.text_input(
                "New Password",
                type="password"
            )

            if st.button("Apply New Password"):

                if len(new_pwd) < 6:
                    st.error("Password too short!")

                else:
                    try:
                        update_user_password(
                            target["username"],
                            new_pwd
                        )
                        st.success(f"Password updated for {search_user}")
                        st.rerun()

                    except Exception as e:
                        st.error("Failed to update password")
                        st.exception(e)

        # =====================================================
        # UPDATE ROLE (FIXED SQL)
        # =====================================================
        with col2:

            st.subheader("🎭 Role")

            roles = list(PERMISSIONS.keys())

            current_role = target.get("role")

            try:
                index = roles.index(current_role)
            except ValueError:
                index = 0

            new_role = st.selectbox(
                "Role",
                roles,
                index=index
            )

            if st.button("Save Role"):

                try:
                    with get_connection() as conn:

                        conn.execute(
                            "UPDATE users SET role = ? WHERE id = ?",
                            (new_role, target["id"])
                        )
                        conn.commit()

                    st.success("Role updated!")
                    st.rerun()

                except Exception as e:
                    st.error("Failed to update role")
                    st.exception(e)

    # =====================================================
    # CREATE USER
    # =====================================================
    with tab_new:

        with st.form("create_user_form"):

            col1, col2 = st.columns(2)

            u = col1.text_input("Username *").lower().strip()
            p = col1.text_input("Password *", type="password")

            fn = col2.text_input("Full Name")
            em = col2.text_input("Email")

            rl = st.selectbox("Role", list(PERMISSIONS.keys()))

            submitted = st.form_submit_button("✅ Create User")

            if submitted:

                if not u or not p:
                    st.error("Fill in required fields")
                else:
                    try:
                        create_user(u, p, rl, fn, em)
                        st.success(f"User {u} created!")
                        st.rerun()

                    except Exception as e:
                        st.error("Failed to create user")
                        st.exception(e)