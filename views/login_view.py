"""Login view."""
import streamlit as st
from managers.auth_manager import authenticate, ROLE_LABELS
from managers.session_manager import create_session

def render():
    # ตรวจสอบว่ามี Token อยู่แล้วหรือไม่ (Auto-login)
    if "session_token" in st.session_state:
        st.rerun()

    _, col, _ = st.columns([1, 2, 1])
    
    with col:
        st.markdown("""
        <div style="text-align:center;padding:2rem 0">
            <h1 style="margin:0">🚢 FreightFlow NTT,</h1>
            <p style="color:#9CA0A8;margin:0.5rem 0 0">Freight Forwarding OS</p>
        </div>
        """, unsafe_allow_html=True)
        
        with st.form("login_form"):
            username = st.text_input("Username", placeholder="Enter your username")
            password = st.text_input("Password", type="password")
            submit = st.form_submit_button("Sign In", type="primary", use_container_width=True)
        
        if submit:
            user = authenticate(username, password)
            if not user:
                # Self-healing fallback: seed default accounts if missing from target DB
                try:
                    from database.connection import ensure_default_users
                    ensure_default_users()
                    user = authenticate(username, password)
                except Exception as seed_err:
                    print(f"[LOGIN RECOVERY WARN]: {str(seed_err)}")

            if user:
                import uuid
                try:
                    token = create_session(user["id"])
                except Exception as sess_err:
                    print(f"[SESSION CREATE WARN]: {str(sess_err)}")
                    token = str(uuid.uuid4())

                st.session_state["user"] = user
                st.session_state["session_token"] = token
                st.query_params["token"] = token
                st.rerun()
            else:
                st.error("❌ Invalid credentials. Please try again.")
        
        # ซ่อน Demo accounts หากอยู่ใน Environment จริง
        debug_mode = False
        try:
            debug_mode = st.secrets.get("DEBUG_MODE", False)
        except Exception:
            debug_mode = False

        if debug_mode:
            with st.expander("ℹ️ Demo accounts"):
                st.table({
                    "Role": ["Admin", "Sales", "Accounting"],
                    "User": ["admin", "sales", "accounting"]
                })

def logout():
    """Utility สำหรับการ Logout"""
    for key in ["user", "session_token"]:
        if key in st.session_state:
            del st.session_state[key]
    st.query_params.clear()
    st.rerun()