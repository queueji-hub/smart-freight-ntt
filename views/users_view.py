"""User Management view (admin only)."""
import streamlit as st
import pandas as pd
from managers.auth_manager import (
    list_users, create_user, update_user_password,
    PERMISSIONS, ROLE_LABELS, hash_password,
)
from database.connection import get_connection


def render():
    user = st.session_state.get("user", {})
    if user.get("role") != "admin":
        st.error("⚠️ Admin only")
        return
    
    st.title("👤 User Management")
    st.caption("Create accounts · Reset passwords · Manage roles")
    
    tab_list, tab_new = st.tabs(["📋 All Users", "➕ Create User"])
    
    # ===== ALL USERS =====
    with tab_list:
        users = list_users()
        if not users:
            st.info("No users.")
        else:
            df = pd.DataFrame(users)
            cols = ["username", "full_name", "email", "role",
                    "is_active", "created_at"]
            cols = [c for c in cols if c in df.columns]
            st.dataframe(df[cols], use_container_width=True,
                          hide_index=True, height=300,
                column_config={
                    "username": "Username",
                    "full_name": "Full Name",
                    "email": "Email",
                    "role": "Role",
                    "is_active": st.column_config.CheckboxColumn("Active"),
                    "created_at": "Created",
                })
            
            st.markdown("---")
            st.markdown("##### 🔐 Reset Password")
            sel_user = st.selectbox(
                "Select user",
                [u["username"] for u in users],
                key="usr_reset_sel")
            new_pwd = st.text_input("New password",
                type="password", key="usr_new_pwd",
                help="Min 8 chars recommended")
            if st.button("Reset password", type="primary"):
                if not new_pwd:
                    st.error("Enter new password")
                else:
                    target = next(u for u in users if u["username"] == sel_user)
                    update_user_password(target["username"], new_pwd)
                    st.success(f"✅ Password reset for {sel_user}")
            
            st.markdown("---")
            st.markdown("##### 🎭 Change Role / Status")
            sel2 = st.selectbox("User", [u["username"] for u in users],
                                  key="usr_role_sel")
            target2 = next(u for u in users if u["username"] == sel2)
            
            c1, c2, c3 = st.columns(3)
            with c1:
                new_role = st.selectbox("New role",
                    list(PERMISSIONS.keys()),
                    index=list(PERMISSIONS.keys()).index(target2["role"])
                        if target2["role"] in PERMISSIONS else 0,
                    format_func=lambda r: ROLE_LABELS.get(r, r),
                    key="usr_role_new")
            with c2:
                new_active = st.checkbox("Active",
                    value=bool(target2.get("is_active", 1)),
                    key="usr_active_new")
            with c3:
                st.write(""); st.write("")
                if st.button("Update", type="primary",
                              use_container_width=True):
                    with get_connection() as conn:
                        conn.execute(
                            "UPDATE users SET role=?, is_active=? WHERE id=?",
                            (new_role, 1 if new_active else 0, target2["id"])
                        )
                    st.success(f"Updated {sel2}")
                    st.rerun()
    
    # ===== CREATE USER =====
    with tab_new:
        with st.form("new_user"):
            c1, c2 = st.columns(2)
            with c1:
                username = st.text_input("Username *",
                    help="Lowercase, no spaces")
                password = st.text_input("Password *", type="password")
                full_name = st.text_input("Full Name")
            with c2:
                email = st.text_input("Email")
                role = st.selectbox("Role *", list(PERMISSIONS.keys()),
                    format_func=lambda r: ROLE_LABELS.get(r, r))
            
            st.caption(f"Permissions for selected role:")
            perms = PERMISSIONS.get(role, {})
            cols_perm = st.columns(len(perms))
            for col, (mod, perm) in zip(cols_perm, perms.items()):
                with col:
                    icon = "✏️" if "w" in perm else "📖"
                    st.markdown(f"<div style='text-align:center;font-size:0.8rem'>"
                               f"{icon}<br/>{mod}</div>",
                               unsafe_allow_html=True)
            
            submit = st.form_submit_button("➕ Create User",
                type="primary", use_container_width=True)
        
        if submit:
            if not username or not password:
                st.error("Username and password required")
            else:
                try:
                    new_id = create_user(username, password, full_name,
                                          email, role)
                    st.success(f"✅ Created user `{username}` (ID: {new_id})")
                except Exception as ex:
                    st.error(f"Failed: {ex}")
