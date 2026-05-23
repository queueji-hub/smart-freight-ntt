import streamlit as st
import pandas as pd
from managers.auth_manager import (
    list_users, create_user, update_user_password,
    PERMISSIONS, ROLE_LABELS,
)
from database.connection import get_connection

def render():
    user = st.session_state.get("user", {})
    if user.get("role") != "admin":
        st.error("⚠️ Admin only access")
        return
    
    st.title("👤 User Management")
    
    tab_list, tab_new = st.tabs(["📋 Manage Users", "➕ Create New"])
    
    with tab_list:

    users = list_users()

    if not users:
        st.info("No users found.")
        return

    df = pd.DataFrame(users)

    st.dataframe(
        df[["username", "full_name", "role"]],
        use_container_width=True
    )

    st.divider()

    # Select User
    search_user = st.selectbox(
        "Select user to manage:",
        [u["username"] for u in users]
    )

    target = next(
        u for u in users
        if u["username"] == search_user
    )

    col1, col2 = st.columns(2)

    with col1:

        st.subheader("🔐 Reset Password")

        new_pwd = st.text_input(
            "New Password",
            type="password",
            key="reset_pwd"
        )

        if st.button("Apply New Password"):

            if len(new_pwd) < 6:
                st.error("Password too short!")

            else:
                update_user_password(
                    target["username"],
                    new_pwd
                )

                st.success(
                    f"Password updated for {search_user}"
                )

    with col2:

        st.subheader("🎭 Role")

        new_role = st.selectbox(
            "Role",
            list(PERMISSIONS.keys()),
            index=list(PERMISSIONS.keys()).index(target["role"])
        )

        if st.button("Save Role"):

            with get_connection() as conn:

                conn.execute(
                    "UPDATE users SET role=%s WHERE id=%s",
                    (new_role, target["id"])
                )

                conn.commit()

            st.success("Updated!")
            st.rerun()

    with tab_new:
        with st.form("create_user_form"):
            col1, col2 = st.columns(2)
            u = col1.text_input("Username *").lower().strip()
            p = col1.text_input("Password *", type="password")
            fn = col2.text_input("Full Name")
            em = col2.text_input("Email")
            rl = st.selectbox("Role", list(PERMISSIONS.keys()))
            
            if st.form_submit_button("✅ Create User"):
                if not u or not p:
                    st.error("Fill in required fields")
                else:
                    try:
                        create_user(u, p, rl, fn, em)
                        st.success(f"User {u} created!")
                    except Exception as e:
                        st.error(f"Error: {e}")