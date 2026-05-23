"""Login view."""
import streamlit as st
from managers.auth_manager import authenticate, ROLE_LABELS
from managers.session_manager import create_session


def render():
    """Show login form. Sets st.session_state.user + URL token on success."""
    _, col, _ = st.columns([1, 2, 1])
    
    with col:
        st.markdown("""
        <div style="text-align:center;padding:2rem 0">
            <h1 style="margin:0">🚢 Smart Freight NTT</h1>
            <p style="color:#9CA0A8;margin:0.5rem 0 0">Freight Forwarding Operating System</p>
        </div>
        """, unsafe_allow_html=True)
        
        with st.form("login_form", clear_on_submit=False):
            st.subheader("🔐 Sign In")
            username = st.text_input("Username",
                placeholder="admin / sales / cs / operation / accounting")
            password = st.text_input("Password", type="password")
            submit = st.form_submit_button("Login", type="primary",
                                            use_container_width=True)
        
        if submit:
            user = authenticate(username, password)
            if user:
                # Create persistent session token
                token = create_session(user["id"])
                st.session_state["user"] = user
                st.session_state["session_token"] = token
                # Store token in URL so it survives full reloads
                try:
                    st.query_params["token"] = token
                except Exception:
                    try:
                        st.experimental_set_query_params(token=token)
                    except Exception:
                        pass
                st.success(f"Welcome, {user['full_name']} ({ROLE_LABELS[user['role']]})!")
                st.rerun()
            else:
                st.error("❌ Invalid username or password")
        
        with st.expander("ℹ️ Demo accounts"):
            st.markdown("""
            | Role | Username | Password |
            |------|----------|----------|
            | 👑 Admin | `admin` | `Admin@2026!` |
            | 💼 Sales | `sales` | `Sales@2026!` |
            | 📞 Customer Service | `cs` | `Cs@2026!` |
            | 🚢 Operation | `operation` | `Ops@2026!` |
            | 💰 Accounting | `accounting` | `Acc@2026!` |
            """)
