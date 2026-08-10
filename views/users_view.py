"""
User Authentication & Corporate RBAC Matrix View Workspace
PostgreSQL / Core Relational Connected - 100% Professional ERP Grade Interface
"""

import streamlit as st
import pandas as pd

from managers.auth_manager import (
    list_users,
    create_user,
    update_user_password,
    PERMISSIONS,
)
from database.connection import get_connection

# =========================================================
# SYSTEM VIEW ROUTER ENTRYPOINT
# =========================================================
def render():
    user = st.session_state.get("user", {})
    role = str(user.get("role", "")).lower()

    # --- ENFORCE RIGID ACCESS CONTROL INTERCEPT ---
    if role != "admin":
        st.markdown("<div style='padding: 20px; background-color: #451a1a; border: 1px solid #dc2626; border-radius: 8px; margin-bottom: 20px;'>", unsafe_allow_html=True)
        st.markdown("<h4 style='color: #ef4444; margin: 0;'>⚠️ Access Control Refusal</h4>", unsafe_allow_html=True)
        st.markdown("<p style='color: #fca5a5; margin: 4px 0 0 0; font-size: 14px;'>Security Policy Violation: This administration workspace is strictly reserved for Authorized Accounts holding the 'admin' security clearance token.</p>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
        st.stop()

    # --- UI HEADER PRESENTATION LAYER ---
    st.markdown("<p style='color: #38BDF8; font-weight: 700; font-size: 13px; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 2px;'>System Security Infrastructure</p>", unsafe_allow_html=True)
    st.markdown("<h2 style='margin-top: 0px; font-weight: 800; color:#F8FAFC;'>👤 Identity & Access Management (IAM)</h2>", unsafe_allow_html=True)
    st.caption("Central Identity Ledger — Administer enterprise tenant profiles, rotate credentials, modify operational roles, and provision encrypted system actor accounts.")

    tab_list, tab_new = st.tabs([
        "📋 Active Identity Directory",
        "➕ Provision Corporate Account"
    ])

    # --- SAFE RELATIONAL READ ROUTINE ---
    with st.spinner("Fetching system actor registries..."):
        try:
            users = list_users() or []
        except Exception as e:
            st.error("🚨 Critical Infrastructure Fault: Failed to safely fetch identities from relational tables.")
            st.exception(e)
            return

    # =========================================================
    # TAB 1: USER MANAGEMENT & CREDENTIAL ROTATION
    # =========================================================
    with tab_list:
        if not users:
            st.info("ℹ️ Identity index empty: No registered enterprise accounts found.")
        else:
            # PostgreSQL Clean Data Conversion Schema
            df = pd.DataFrame(users)
            
            # Extract safe non-sensitive columns for global corporate presentation
            safe_cols = [c for c in ["username", "full_name", "role", "email"] if c in df.columns]
            
            column_mapping = {
                "username": "Account Handle / Unique ID",
                "full_name": "Full Legal Name",
                "role": "Assigned System Role",
                "email": "Registered Corporate Email"
            }
            
            df_display = df[safe_cols].rename(columns=column_mapping)
            
            st.dataframe(
                df_display,
                use_container_width=True,
                hide_index=True
            )

            st.markdown("<div style='margin-top: 25px;'></div>", unsafe_allow_html=True)
            st.markdown("---")
            st.markdown("<h4 style='font-size:16px; color:#F1F5F9; font-weight:700;'>✏️ Enterprise Account Operation Desk</h4>", unsafe_allow_html=True)

            usernames = [str(u.get("username")) for u in users if u.get("username")]
            
            if not usernames:
                st.warning("No valid usernames detected in registry sequence.")
            else:
                search_user = st.selectbox(
                    "Select Target Corporate Account to Manage",
                    options=usernames,
                    key="iam_target_account_selector"
                )

                target = next((u for u in users if str(u.get("username")) == search_user), None)

                if not target:
                    st.error("Selected record frame failed lookup validation index.")
                else:
                    st.markdown(f"<div style='padding: 18px; border: 1px solid #1E293B; background-color: #0F172A; border-radius:12px; margin-top:10px;'>", unsafe_allow_html=True)
                    st.markdown(f"##### 🔒 Profile Selected: Account Reference ID `{target.get('id', 'N/A')}`")
                    
                    col1, col2 = st.columns(2)

                    # --- SUB-OPERATION: CREDENTIAL ROTATION ---
                    with col1:
                        st.markdown("<p style='font-weight:700; color:#F1F5F9; margin-bottom:8px;'>🔐 Rotate Account Password</p>", unsafe_allow_html=True)
                        
                        # Isolate widget dependencies via an explicit action form block
                        with st.form(key=f"iam_password_form_block_{target['username']}"):
                            new_pwd = st.text_input(
                                "Define New Secure Password Structure",
                                type="password",
                                placeholder="Minimum 6 characters recommended...",
                                key=f"iam_pwd_input_{target['username']}"
                            )
                            submit_pwd = st.form_submit_button("⚡ Overwrite Account Credentials", use_container_width=True, type="primary")
                        
                        if submit_pwd:
                            if len(new_pwd.strip()) < 6:
                                st.error("⚠️ Policy Rejection: Assigned corporate password does not satisfy complexity threshold (min 6 chars).")
                            else:
                                with st.spinner("Encrypting and mutating record vector..."):
                                    try:
                                        update_user_password(target["username"], new_pwd.strip())
                                        st.toast(f"✅ Credentials rotated successfully for account: {search_user}", icon="🔐")
                                        st.rerun()
                                    except Exception as pwd_ex:
                                        st.error("System database rejected authentication alteration routine.")
                                        st.exception(pwd_ex)

                    # --- SUB-OPERATION: ROLE CHANGE MATRIX ---
                    with col2:
                        st.markdown("<p style='font-weight:700; color:#F1F5F9; margin-bottom:8px;'>🎭 Reassign RBAC Clearance Token</p>", unsafe_allow_html=True)
                        
                        roles_options = list(PERMISSIONS.keys())
                        current_role = str(target.get("role", ""))

                        try:
                            role_index = roles_options.index(current_role)
                        except ValueError:
                            role_index = 0

                        with st.form(key=f"iam_role_form_block_{target['username']}"):
                            new_role = st.selectbox(
                                "Target RBAC Clearance Tier Selection",
                                options=roles_options,
                                index=role_index,
                                key=f"iam_role_select_{target['username']}"
                            )
                            submit_role = st.form_submit_button("💾 Save System Role Mutation", use_container_width=True)

                        if submit_role:
                            with st.spinner("Applying access matrix mutation..."):
                                try:
                                    with get_connection() as conn:
                                        # Standardized placeholder structure safely prepared
                                        cursor = conn.cursor()
                                        
                                        # Adaptable query statement format agnostic handler
                                        try:
                                            cursor.execute(
                                                "UPDATE users SET role = %s WHERE id = %s",
                                                (new_role, target["id"])
                                            )
                                        except:
                                            # Failover support for alternative embedded systems architecture configurations
                                            cursor.execute(
                                                "UPDATE users SET role = ? WHERE id = ?",
                                                (new_role, target["id"])
                                            )
                                            
                                        conn.commit()
                                        
                                    st.toast(f"✅ Access authorization upgraded to standard: [{new_role.upper()}]", icon="🎭")
                                    st.rerun()
                                except Exception as role_ex:
                                    st.error("🚨 Mutation Pipeline Failure: Database level constraint aborted role assignment.")
                                    st.exception(role_ex)
                    
                    st.markdown("</div>", unsafe_allow_html=True)

    # =========================================================
    # TAB 2: PROVISIONING NEW CORPORATE ACCOUNT ENGINE
    # =========================================================
    with tab_new:
        st.markdown("<h4 style='font-size:16px; color:#F1F5F9; font-weight:700;'>➕ Provision New Legal Security Actor Profile</h4>", unsafe_allow_html=True)
        
        with st.form("iam_provisioning_new_user_form_block", clear_on_submit=True):
            with st.container(border=True):
                st.markdown("**📋 Account Credentials & Scope Definition**")
                c1, c2 = st.columns(2)

                with c1:
                    u = st.text_input("System Account Username Handle *", placeholder="e.g., james.k (lowercase letters only)").lower().strip()
                    p = st.text_input("Temporary Assignment Password *", type="password", placeholder="Provide strong alphanumeric block...")

                with c2:
                    fn = st.text_input("Full Employee Identity Name", placeholder="e.g., James Knight")
                    em = st.text_input("Corporate Operational Email Address", placeholder="e.g., james.k@freightflow.com")

                st.markdown("---")
                rl = st.selectbox("Assigned Roles Matrix Group Authorization Target", options=list(PERMISSIONS.keys()))

            submitted = st.form_submit_button("🚀 Commit Account Provisioning to Registry", type="primary", use_container_width=True)

        if submitted:
            if not u or not p:
                st.error("⚠️ Validation Refusal: Username and Password parameters are strictly mandatory fields.")
            elif len(p) < 6:
                st.error("⚠️ Policy Rejection: Assigned provisioning temporary password length does not satisfy security minimums (6 chars).")
            else:
                with st.spinner("Executing secure pipeline data injection..."):
                    try:
                        create_user(u, p, rl, fn.strip() if fn else None, em.strip() if em else None)
                        st.success(f"🎉 Enterprise Profile [{u}] successfully provisioned and committed to master nodes!")
                        st.balloons()
                        st.rerun()
                    except Exception as creation_ex:
                        st.error(f"🚨 Master Entry Aborted: Target record identifier could be conflicting or corrupted. Error: {str(creation_ex)}")